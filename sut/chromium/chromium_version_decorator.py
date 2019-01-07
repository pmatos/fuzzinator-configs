# Copyright (c) 2020 Renata Hodovan, Akos Kiss.
#
# Licensed under the BSD 3-Clause License
# <LICENSE.rst or https://opensource.org/licenses/BSD-3-Clause>.
# This file may not be copied, modified, or distributed except
# according to those terms.

import json
import logging
import os
import platform
import re
import subprocess

from fuzzinator.call import CallableDecorator

logger = logging.getLogger(__name__)


class ChromiumVersionDecorator(CallableDecorator):
    """
    Decorator for Chromium-based SUTs: it supports SUTs built from
    source and SUTs updated/downloaded with the chromium-update-nightly
    script. In both cases, the decorator compiles version information
    in the form provided by the chrome://version page.

    **Mandatory parameter of the decorator:**

      - ``root_dir``: root directory of Chromium's GIT repository.

    **Example configuration snippet:**

        .. code-block:: ini

            [sut.foo]
            call=fuzzinator.call.SubprocessCall
            call.decorate(0)=chromium_version_decorator.ChromiumVersionDecorator

            [sut.foo.call]
            # assuming that foo takes one file as input specified on command line
            command=/home/alice/chromium/out/Fuzzer/binary {test}

            [sut.foo.decorate(0)]
            root=dir=/home/alice/chromium/src/
    """

    def decorator(self, root_dir, **kwargs):

        def _run_cmd(cmd):
            proc = subprocess.Popen(cmd,
                                    cwd=root_dir,
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE,
                                    universal_newlines=True)
            stdout, stderr = proc.communicate()
            if proc.returncode != 0:
                logger.debug('ChromiumVersionDecorator exited with nonzero exit code: %s', stderr)
                return None
            return stdout.strip()

        cr_version = None

        if os.path.exists(os.path.join(root_dir, 'fuzz_version_data.json')):
            with open(os.path.join(root_dir, 'fuzz_version_data.json'), 'r') as f:
                version_data = json.load(f)
                cr_version = 'Google Chrome: {name} downloaded from http://commondatastorage.googleapis.com\n' \
                             'Revision: {hash}-{cr_pos} ({platform})'.format(
                                name=version_data['name'],
                                platform=platform.machine(),
                                hash=version_data['metadata']['cr-git-commit'],
                                cr_pos=version_data['metadata']['cr-commit-position-number'])
        else:
            tag = _run_cmd(['git', 'describe', '--tags'])
            if tag:
                hash = _run_cmd(['git', 'rev-parse', tag + '~1'])
                commit = _run_cmd(['git', 'log', tag, '-n1'])
                if commit:
                    m = re.search(r'Cr-Commit-Position: (?P<cr_pos>.+)$', commit)
                    if m:
                        cr_version = 'Google Chrome: {tag} dev ({platform})\n' \
                                     'Revision: {hash}-{cr_pos}'.format(
                                        tag=tag,
                                        platform=platform.machine(),
                                        hash=hash,
                                        cr_pos=m.group('cr_pos'))

        def wrapper(fn):
            def filter(*args, **kwargs):
                issue = fn(*args, **kwargs)
                if not issue:
                    return issue

                if cr_version:
                    issue['version'] = cr_version

                return issue
            return filter
        return wrapper

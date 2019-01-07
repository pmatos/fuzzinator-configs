#!/usr/bin/env python3

# Copyright (c) 2019-2020 Renata Hodovan, Akos Kiss.
#
# Licensed under the BSD 3-Clause License
# <LICENSE-BSD-3-Clause.rst or https://opensource.org/licenses/BSD-3-Clause>.
# This file may not be copied, modified, or distributed except according to
# those terms.

import json
import platform
import shutil
import stat

from argparse import ArgumentParser
from os import chmod, getcwd, remove, rename
from os.path import exists, join
from urllib.request import Request, urlopen
from zipfile import ZipFile


def update_nightly(system, build, outdir, name=None):

    def _get_latest_decriptor():
        latest = dict()
        next_page_token = ''
        req_url = 'https://www.googleapis.com/storage/v1/b/chromium-browser-asan/o?delimiter=/' \
                  '&prefix=%s-%s/&fields=items(kind,mediaLink,metadata,name,size,updated),kind,prefixes,nextPageToken' \
                  % (system, build)
        while True:
            json_obj = json.loads(_download_resource(req_url + '&pageToken=' + (next_page_token or '')).decode('utf-8', errors='ignore'))
            for item in json_obj['items']:
                if 'metadata' not in item or 'cr-commit-position-number' not in item['metadata']:
                    continue
                if int(item['metadata']['cr-commit-position-number']) > int(latest.get('metadata', {}).get('cr-commit-position-number', 0)):
                    latest = item

            if 'nextPageToken' in json_obj:
                next_page_token = json_obj['nextPageToken']
            else:
                break
        return latest

    def _download_resource(src):
        for i in range(5):
            try:
                return urlopen(Request(src), None, 35).read()
            except Exception as e:
                print('%s while downloading "%s"' % (e, src))

    def _make_executable(path):
        chmod(path, stat.S_IRWXU | stat.S_IRGRP | stat.S_IWGRP | stat.S_IROTH | stat.S_IWOTH)

    zip_path = None
    try:
        print('Extract latest Chromium descriptor ...')
        latest_desc = _get_latest_decriptor()
        orig_zip_name = latest_desc['name'].split('/')[-1]
        zip_path = join(outdir, orig_zip_name)
        if not exists(zip_path):
            print('Download %s ...' % orig_zip_name)
            with open(zip_path, 'wb') as f:
                f.write(_download_resource(latest_desc['mediaLink']))
            print('Extract zip ...')
            ZipFile(zip_path).extractall(outdir)
            print('Delete zip ...')
            remove(zip_path)

        chromium_dir = join(outdir, orig_zip_name.replace('.zip', ''))
        print('Set executable flags ...')
        _make_executable(join(chromium_dir, 'content_shell'))
        _make_executable(join(chromium_dir, 'chrome'))

        with open(join(chromium_dir, 'fuzz_version_data.json'), 'w') as f:
            json.dump(latest_desc, f)

        if name:
            target_dir = join(outdir, name)
            if exists(target_dir):
                shutil.rmtree(target_dir)
            print('Rename %s to %s ...' % (chromium_dir, target_dir))
            rename(chromium_dir, target_dir)

    except KeyboardInterrupt:
        if zip_path and exists(zip_path):
            print('KeyboardInterrupt. Remove %s.' % zip_path)
            remove(zip_path)


if __name__ == '__main__':
    parser = ArgumentParser(description='Download the latest Chromium binary from googleapis.')
    parser.add_argument('--system', metavar='STRING', choices=['linux', 'mac'], default='linux' if platform.system() == 'Linux' else 'mac' if platform.system() == 'Darwin' else None,
                        help='Name of the system to download Chromium for (choices: %(choices)s, default: %(default)s)')
    parser.add_argument('--build', metavar='STRING', choices=['debug', 'release'], default='debug',
                        help='Chromium build version to download (choices: %(choices)s, default: %(default)s)')
    parser.add_argument('--outdir', metavar='DIR', default=getcwd(),
                        help='Path to the directory to save the latest chromium.')
    parser.add_argument('--name', metavar='STRING',
                        help='Name of the target directory containing chromium sources.')
    args = parser.parse_args()

    if args.system not in ['linux', 'mac']:
        parser.error('Unsupported system %s.' % args.system)

    update_nightly(args.system, args.build, args.outdir, args.name)

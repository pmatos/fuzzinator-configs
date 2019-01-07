#!/bin/bash

# Copyright (c) 2019-2021 Renata Hodovan, Akos Kiss.
#
# Licensed under the BSD 3-Clause License
# <LICENSE-BSD-3-Clause.rst or https://opensource.org/licenses/BSD-3-Clause>.
# This file may not be copied, modified, or distributed except according to
# those terms.

# Updates and builds a GIT-based Chromium repository to the choosen or to the
# latest tagged version.
# Requirement: >= Git 2.23

ARGS=$1
TARGETS=$2

git fetch
RELEASE=${3-$(git describe --tags --abbrev=0)}
git switch -C "dev_$RELEASE" $RELEASE
gclient sync --with_branch_heads --with_tags -D --force
gn gen out/Fuzzer --args="$ARGS"
ninja -C out/Fuzzer chrome $TARGET

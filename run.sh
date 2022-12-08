#!/usr/bin/env bash

set -euo pipefail

pushd $(dirname $(readlink -f $0))

if [ ! -d build/llvm-mingw ]; then
    mkdir -p build/llvm-mingw
    pushd build/llvm-mingw
    wget -q https://github.com/mstorsjo/llvm-mingw/releases/download/20220906/llvm-mingw-20220906-ucrt-ubuntu-18.04-x86_64.tar.xz
    tar xvf *
    mv */* .
    popd
fi

export PATH=$(pwd)/build/llvm-mingw/bin:$PATH
aarch64-w64-mingw32-gcc --version
python3 setup.py install --prefix build/run > /dev/null
crossroad=$(pwd)/build/run/bin/crossroad

popd

# crossroad win-arm64 project
# ... open shell
# crossroad cmake .

$crossroad "$@"

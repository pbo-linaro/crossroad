#!/bin/sh
#
# This file is part of crossroad.
# Copyright (C) 2013 Jehan <jehan at girinstud.io>
#
# crossroad is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# crossroad is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with crossroad.  If not, see <http://www.gnu.org/licenses/>.

# Some value for user usage.
export CROSSROAD_BUILD=`@DATADIR@/share/crossroad/scripts/config.guess`
export CROSSROAD_CMAKE_TOOLCHAIN_FILE="@DATADIR@/share/crossroad/scripts/cmake/toolchain-${CROSSROAD_PLATFORM}.cmake"

# ld is a mandatory file to enter this environment.
# Also it is normally not touched by ccache, which makes it a better
# prefix-searching tool than gcc.
host_ld="`which $CROSSROAD_HOST-ld`"
host_ld_dir="`dirname $host_ld`"
host_ld_bin="`basename $host_ld_dir`"

if [ $host_ld_bin = "bin" ]; then
    host_ld_prefix="`dirname $host_ld_dir`"
    # No need to add the guessed prefix if it is a common one that we add anyway.
    if [ "$host_ld_prefix" != "/usr" ]; then
        if [ "$host_ld_prefix" != "/usr/local" ]; then
            if [ -d "$host_ld_prefix/$CROSSROAD_HOST" ]; then
                export CROSSROAD_GUESSED_MINGW_PREFIX="$host_ld_prefix/$CROSSROAD_HOST"
            fi
        fi
    fi
    unset host_ld_prefix
fi
unset host_ld_bin
unset host_ld_dir
unset host_ld

export LD_LIBRARY_PATH=$CROSSROAD_PREFIX/lib
if [ x"CROSSROAD_PLATFORM" == x"w32" ] && [ -d "$CROSSROAD_CUSTOM_MINGW_W32_PREFIX" ]; then
    export LD_LIBRARY_PATH="${LD_LIBRARY_PATH}:$CROSSROAD_CUSTOM_MINGW_W32_PREFIX/lib32/:$CROSSROAD_CUSTOM_MINGW_W32_PREFIX/lib/"
fi
if [ x"CROSSROAD_PLATFORM" == x"w64" ] && [ -d "$CROSSROAD_CUSTOM_MINGW_W64_PREFIX" ]; then
    export LD_LIBRARY_PATH="${LD_LIBRARY_PATH}:$CROSSROAD_CUSTOM_MINGW_W64_PREFIX/lib64/:$CROSSROAD_CUSTOM_MINGW_W64_PREFIX/lib/"
fi
if [ -d "$CROSSROAD_GUESSED_MINGW_PREFIX" ]; then
    export LD_LIBRARY_PATH="${LD_LIBRARY_PATH}:$CROSSROAD_GUESSED_MINGW_PREFIX/lib32/:$CROSSROAD_GUESSED_MINGW_PREFIX/lib/"
fi
# Adding some typical distribution paths.
# Note: I could also try to guess the user path from `which ${CROSSROAD_HOST}-gcc`.
# But it may not always work. For instance if the user uses ccache.
export LD_LIBRARY_PATH="${LD_LIBRARY_PATH}:/usr/local/$CROSSROAD_HOST/lib${CROSSROAD_WORD_SIZE}/:/usr/local/$CROSSROAD_HOST/lib"
export LD_LIBRARY_PATH="${LD_LIBRARY_PATH}:/usr/$CROSSROAD_HOST/lib${CROSSROAD_WORD_SIZE}/:/usr/$CROSSROAD_HOST/lib/"

mkdir -p $CROSSROAD_PREFIX/bin
export PATH="@DATADIR@/share/crossroad/bin:$CROSSROAD_PREFIX/bin:$PATH"

# no such file or directory error on non-existing aclocal.
mkdir -p $CROSSROAD_PREFIX/share/aclocal
export ACLOCAL_FLAGS="-I $CROSSROAD_PREFIX/share/aclocal"
# no such file or directory warning on non-existing include.
mkdir -p $CROSSROAD_PREFIX/include
mkdir -p $CROSSROAD_PREFIX/lib

# So that the system-wide python can still find any locale lib.
for dir in $(find $CROSSROAD_PREFIX/lib/ -name 'python*');
do
    export PYTHONPATH=:${dir}:$PYTHONPATH
done;

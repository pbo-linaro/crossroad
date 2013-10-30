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

# Here is our root.
export CROSSROAD_PREFIX="`crossroad -p $CROSSROAD_PLATFORM`"

# Internal usage.
export CROSSROAD_ROAD="${CROSSROAD_PLATFORM}"

# Reset pkg-config to search *ONLY* libraries compiled for the cross-compiled platform target.
export PKG_CONFIG_LIBDIR=
export PKG_CONFIG_PATH=$CROSSROAD_PREFIX/lib64/pkgconfig:$CROSSROAD_PREFIX/share/pkgconfig:$CROSSROAD_PREFIX/lib/pkgconfig
if [ -d "$CROSSROAD_CUSTOM_MINGW_W64_PREFIX" ]; then
    export PKG_CONFIG_PATH="$PKG_CONFIG_PATH:$CROSSROAD_CUSTOM_MINGW_W64_PREFIX/lib64/pkconfig:$CROSSROAD_CUSTOM_MINGW_W64_PREFIX/lib/pkconfig"
fi
if [ -d "$CROSSROAD_GUESSED_MINGW_PREFIX" ]; then
    export PKG_CONFIG_PATH="$PKG_CONFIG_PATH:$CROSSROAD_GUESSED_MINGW_PREFIX/lib64/pkconfig:$CROSSROAD_GUESSED_MINGW_PREFIX/lib/pkconfig"
fi
export PKG_CONFIG_PATH="$PKG_CONFIG_PATH:/usr/local/$CROSSROAD_HOST/lib64/pkconfig"
export PKG_CONFIG_PATH="$PKG_CONFIG_PATH:/usr/$CROSSROAD_HOST/lib64/pkconfig"
export PKG_CONFIG_PATH="$PKG_CONFIG_PATH:/usr/local/$CROSSROAD_HOST/lib/pkconfig"
export PKG_CONFIG_PATH="$PKG_CONFIG_PATH:/usr/$CROSSROAD_HOST/lib/pkconfig"

export LD_LIBRARY_PATH=$CROSSROAD_PREFIX/lib
if [ -d "$CROSSROAD_CUSTOM_MINGW_W64_PREFIX" ]; then
    export LD_LIBRARY_PATH="${LD_LIBRARY_PATH}:$CROSSROAD_CUSTOM_MINGW_W64_PREFIX/lib64/:$CROSSROAD_CUSTOM_MINGW_W64_PREFIX/lib/"
fi
if [ -d "$CROSSROAD_GUESSED_MINGW_PREFIX" ]; then
    export LD_LIBRARY_PATH="${LD_LIBRARY_PATH}:$CROSSROAD_GUESSED_MINGW_PREFIX/lib64/:$CROSSROAD_GUESSED_MINGW_PREFIX/lib/"
fi
# Adding some typical distribution paths.
# Note: I could also try to guess the user path from `which ${CROSSROAD_HOST}-gcc`.
# But it may not always work. For instance if the user uses ccache.
export LD_LIBRARY_PATH="${LD_LIBRARY_PATH}:/usr/local/$CROSSROAD_HOST/lib64/:/usr/local/$CROSSROAD_HOST/lib/"
export LD_LIBRARY_PATH="${LD_LIBRARY_PATH}:/usr/$CROSSROAD_HOST/lib64/:/usr/$CROSSROAD_HOST/lib/"

mkdir -p $CROSSROAD_PREFIX/bin
export PATH="$CROSSROAD_PREFIX/bin:$PATH"

# no such file or directory error on non-existing aclocal.
mkdir -p $CROSSROAD_PREFIX/share/aclocal
export ACLOCAL_FLAGS="-I $CROSSROAD_PREFIX/share/aclocal"
# no such file or directory warning on non-existing include.
mkdir -p $CROSSROAD_PREFIX/include
export CFLAGS="-I$CROSSROAD_PREFIX/include"
mkdir -p $CROSSROAD_PREFIX/lib
export LDFLAGS="-L$CROSSROAD_PREFIX/lib"

# Very important! The default -I list of directories when none is specified!
export CPATH="$CROSSROAD_PREFIX/include"

if [ -d "$CROSSROAD_CUSTOM_MINGW_W64_PREFIX" ]; then
    if [ -d "$CROSSROAD_CUSTOM_MINGW_W64_PREFIX/include" ]; then
        export CFLAGS="$CFLAGS -I$CROSSROAD_CUSTOM_MINGW_W64_PREFIX/include/"
        export CPATH="$CPATH:$CROSSROAD_CUSTOM_MINGW_W64_PREFIX/include/"
    fi
    if [ -d "$CROSSROAD_CUSTOM_MINGW_W64_PREFIX/lib64" ]; then
        export LDFLAGS="$LDFLAGS -L$CROSSROAD_CUSTOM_MINGW_W64_PREFIX/lib64"
    fi
    if [ -d "$CROSSROAD_CUSTOM_MINGW_W64_PREFIX/lib" ]; then
        export LDFLAGS="$LDFLAGS -L$CROSSROAD_CUSTOM_MINGW_W64_PREFIX/lib"
    fi
fi
if [ -d "$CROSSROAD_GUESSED_MINGW_PREFIX" ]; then
    if [ -d "$CROSSROAD_GUESSED_MINGW_PREFIX/include" ]; then
        export CFLAGS="$CFLAGS -I$CROSSROAD_GUESSED_MINGW_PREFIX/include/"
        export CPATH="$CPATH:$CROSSROAD_GUESSED_MINGW_PREFIX/include/"
    fi
    if [ -d "$CROSSROAD_GUESSED_MINGW_PREFIX/lib64" ]; then
        export LDFLAGS="$LDFLAGS -L$CROSSROAD_GUESSED_MINGW_PREFIX/lib64"
    fi
    if [ -d "$CROSSROAD_GUESSED_MINGW_PREFIX/lib" ]; then
        export LDFLAGS="$LDFLAGS -L$CROSSROAD_GUESSED_MINGW_PREFIX/lib"
    fi
fi
# Adding some user-installed or distribution common installation path.
if [ -d "/usr/local/$CROSSROAD_HOST/include" ]; then
    export CFLAGS="$CFLAGS -I/usr/local/$CROSSROAD_HOST/include/"
    export CPATH="$CPATH:/usr/local/$CROSSROAD_HOST/include/"
fi
if [ -d "/usr/$CROSSROAD_HOST/include" ]; then
    export CFLAGS="$CFLAGS -I/usr/$CROSSROAD_HOST/include/"
    export CPATH="$CPATH:/usr/$CROSSROAD_HOST/include/"
fi
if [ -d "/usr/local/$CROSSROAD_HOST/lib64" ]; then
    export LDFLAGS="$LDFLAGS -L/usr/local/$CROSSROAD_HOST/lib64"
fi
if [ -d "/usr/$CROSSROAD_HOST/lib64" ]; then
    export LDFLAGS="$LDFLAGS -L/usr/$CROSSROAD_HOST/lib64"
fi
if [ -d "/usr/local/$CROSSROAD_HOST/lib" ]; then
    export LDFLAGS="$LDFLAGS -L/usr/local/$CROSSROAD_HOST/lib"
fi
if [ -d "/usr/$CROSSROAD_HOST/lib" ]; then
    export LDFLAGS="$LDFLAGS -L/usr/$CROSSROAD_HOST/lib"
fi

# So that the system-wide python can still find any locale lib.
for dir in $(find $CROSSROAD_PREFIX/lib/ -name 'python*');
do
    export PYTHONPATH=:${dir}:$PYTHONPATH
done;

# CHANGE the prompt to show you are in cross-comp env.
RED=$'\e[0;31m'
NORMAL=$'\e[0m'
if [ x"$(locale charmap)"x = "xUTF-8x" ]; then
    SYMBOL="✘"
else
    SYMBOL="*"
fi;

# Leave the user override the default crossroads PS1.
if [ "x${CROSSROADS_PS1}x" = "xx" ]; then
    export PS1="${RED}${CROSSROAD_PLATFORM}${SYMBOL}${NORMAL} ${PS1}"
else
    export PS1="${CROSSROADS_PS1}"
fi

echo "Your environment has been set to cross-compile for the '$CROSSROAD_PLATFORM_NICENAME' ($CROSSROAD_PLATFORM) environment."
echo 'Use `crossroad help` to list available commands and `man crossroad` to get a full documentation of crossroad capabilities.'
echo "To exit this cross-compilation environment, simply \`exit\` the current shell session."
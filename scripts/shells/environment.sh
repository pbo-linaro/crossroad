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
export CROSSROAD_MESON_TOOLCHAIN_FILE="@DATADIR@/share/crossroad/scripts/meson/toolchain-${CROSSROAD_PLATFORM}.meson"

# Compute the platform word-size for the "native" platform.
if [ x"$CROSSROAD_PLATFORM" == x"native" ]; then
  LONG_BIT=`getconf LONG_BIT`
  if [ x"$LONG_BIT" == x"32" ] || \
     [ x"$LONG_BIT" == x"64" ]; then
    export CROSSROAD_WORD_SIZE=$LONG_BIT
  fi
fi

export PATH="$CROSSROAD_PREFIX/bin:$PATH"

if [ x"$CROSSROAD_PLATFORM" == x"native" ]; then
  export LD_LIBRARY_PATH=$CROSSROAD_PREFIX/lib:$LD_LIBRARY_PATH
  export GI_TYPELIB_PATH=$CROSSROAD_PREFIX/lib/girepository-1.0/:$GI_TYPELIB_PATH

  GCC="gcc"
else
  export LD_LIBRARY_PATH=$CROSSROAD_PREFIX/lib
  export GI_TYPELIB_PATH=$CROSSROAD_PREFIX/lib/girepository-1.0/

  GCC="${CROSSROAD_HOST}-gcc"
fi

if [ "x$CROSSROAD_WORD_SIZE" != "x" ]; then
  export LD_LIBRARY_PATH=$CROSSROAD_PREFIX/lib${CROSSROAD_WORD_SIZE}:$LD_LIBRARY_PATH
  export GI_TYPELIB_PATH=$CROSSROAD_PREFIX/lib${CROSSROAD_WORD_SIZE}/girepository-1.0/:$GI_TYPELIB_PATH
fi

# This relies on GCC. Clang/LLVM probably has an equivalent to find
# specific multi-arch paths but I don't know about it.
# This is needed because I realized that on some distributions, for
# instance Debian, libraries were installed in lib/x86_64-linux-gnu/.
# And it would seem that some build systems (like meson) would detect
# the distribution standard paths and install the same in custom
# prefixes. So we need to add these paths as well.
if [ "x`$GCC -print-multiarch`" != "x" ]; then
  export LD_LIBRARY_PATH=$CROSSROAD_PREFIX/lib/`$GCC -print-multiarch`:$LD_LIBRARY_PATH
  export GI_TYPELIB_PATH=$CROSSROAD_PREFIX/lib/`$GCC -print-multiarch`/girepository-1.0/:$GI_TYPELIB_PATH
fi

if [ x"$CROSSROAD_PLATFORM" == x"w32" ] || \
   [ x"$CROSSROAD_PLATFORM" == x"w64" ]; then
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

  if [ x"$CROSSROAD_PLATFORM" == x"w32" ] && [ -d "$CROSSROAD_CUSTOM_MINGW_W32_PREFIX" ]; then
      export LD_LIBRARY_PATH="${LD_LIBRARY_PATH}:$CROSSROAD_CUSTOM_MINGW_W32_PREFIX/lib32/:$CROSSROAD_CUSTOM_MINGW_W32_PREFIX/lib/"
  fi
  if [ x"$CROSSROAD_PLATFORM" == x"w64" ] && [ -d "$CROSSROAD_CUSTOM_MINGW_W64_PREFIX" ]; then
      export LD_LIBRARY_PATH="${LD_LIBRARY_PATH}:$CROSSROAD_CUSTOM_MINGW_W64_PREFIX/lib64/:$CROSSROAD_CUSTOM_MINGW_W64_PREFIX/lib/"
  fi
  if [ -d "$CROSSROAD_GUESSED_MINGW_PREFIX" ]; then
      export LD_LIBRARY_PATH="${LD_LIBRARY_PATH}:$CROSSROAD_GUESSED_MINGW_PREFIX/lib32/:$CROSSROAD_GUESSED_MINGW_PREFIX/lib/"
  fi
fi

if [ x"$CROSSROAD_PLATFORM" == x"native" ]; then
  # Native environment does not need much tweaking nor any additional
  # tools. We only need to add pkg-config path.
  export PKG_CONFIG_PATH=$CROSSROAD_PREFIX/lib/pkgconfig:$CROSSROAD_PREFIX/share/pkgconfig:$PKG_CONFIG_PATH
  if [ "x$CROSSROAD_WORD_SIZE" != "x" ]; then
    export PKG_CONFIG_PATH=$CROSSROAD_PREFIX/lib${CROSSROAD_WORD_SIZE}/pkgconfig:$PKG_CONFIG_PATH
  fi
  if [ "x`$GCC -print-multiarch`" != "x" ]; then
    export PKG_CONFIG_PATH=$CROSSROAD_PREFIX/lib/`$GCC -print-multiarch`/pkgconfig/:$PKG_CONFIG_PATH
  fi

  export CROSSROAD_HOST="$CROSSROAD_BUILD"
else
  # Adding some typical distribution paths.
  # Note: I could also try to guess the user path from `which ${CROSSROAD_HOST}-gcc`.
  # But it may not always work. For instance if the user uses ccache.
  export LD_LIBRARY_PATH="${LD_LIBRARY_PATH}:/usr/local/$CROSSROAD_HOST/lib${CROSSROAD_WORD_SIZE}/:/usr/local/$CROSSROAD_HOST/lib"
  export LD_LIBRARY_PATH="${LD_LIBRARY_PATH}:/usr/$CROSSROAD_HOST/lib${CROSSROAD_WORD_SIZE}/:/usr/$CROSSROAD_HOST/lib/"

  export PATH="@DATADIR@/share/crossroad/bin:$PATH"
fi

mkdir -p $CROSSROAD_PREFIX/bin
# no such file or directory error on non-existing aclocal.
mkdir -p $CROSSROAD_PREFIX/share/aclocal
export ACLOCAL_FLAGS="-I$CROSSROAD_PREFIX/share/aclocal"
# no such file or directory warning on non-existing include.
mkdir -p $CROSSROAD_PREFIX/include
mkdir -p $CROSSROAD_PREFIX/lib

# So that the system-wide python can still find any locale lib.
for dir in $(find $CROSSROAD_PREFIX/lib/ $CROSSROAD_PREFIX/lib${CROSSROAD_WORD_SIZE}/ -maxdepth 1 -name 'python3.*' 2>/dev/null);
do
  export PYTHONPATH=${dir}/site-packages:$PYTHONPATH
done;
# For gdbus-codegen.
export PYTHONPATH=$CROSSROAD_PREFIX/share/glib-2.0/:$PYTHONPATH

# g-ir-scanner looks in XDG_DATA_DIRS/gir-1.0
export XDG_DATA_DIRS="$CROSSROAD_PREFIX/share:$XDG_DATA_DIRS"

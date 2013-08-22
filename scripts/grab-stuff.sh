#!/bin/bash

PKGS="gtk2 libpoppler libwebkitgtk libmng librsvg libwmf gtk2-devel libpoppler-devel \
      libwebkitgtk-devel libmng-devel librsvg-devel libwmf-devel xpm-nox xpm-nox-devel \
      libexif libexif-devel libexif-lang libwebkitgtk-lang libcurl libcurl-devel \
      libjasper libjasper-devel libtiff libtiff-devel libpoppler-glib libpoppler-glib-devel \
      bzip2 libbz2 libbz2-devel liblcms liblcms-devel iso-codes iso-codes-devel \
      win_iconv-devel win_iconv ghostscript libgs libgs-devel libffi-devel dbus-1-devel pthreads pthreads-devel"
REPO="openSUSE_12.1"

# TODO: make option --src instead + an option to specify a directory else create under pwd/cross-compile if not existent.
if [ "$1" = "src" ]
then

	python3 download-mingw-rpm.py -r "$REPO" --deps --src $PKGS

else

	rm -rf /home/jehan/cross-compile/deps/usr

	python3 download-mingw-rpm.py -r "$REPO" --deps $PKGS
	python3 download-mingw-rpm.py --no-clean -r "$REPO" -p windows:mingw:win64 --deps $PKGS

#	rm -rvf usr/i686-w64-mingw32/sys-root/mingw/lib/libmingw*
#	rm -rvf usr/x86_64-w64-mingw32/sys-root/mingw/lib/libmingw*

	sed -e 's:^prefix=.*:prefix=/home/jehan/cross-compile/deps/usr/i686-w64-mingw32/sys-root/mingw:g' -i /home/jehan/cross-compile/deps/usr/i686-w64-mingw32/sys-root/mingw/lib/pkgconfig/*.pc
	sed -e 's:^prefix=.*:prefix=/home/jehan/cross-compile/deps/usr/x86_64-w64-mingw32/sys-root/mingw:g' -i /home/jehan/cross-compile/deps/usr/x86_64-w64-mingw32/sys-root/mingw/lib/pkgconfig/*.pc
	sed -e 's:/usr/x86_64-w64-mingw32/sys-root/mingw:/home/jehan/cross-compile/deps/usr/x86_64-w64-mingw32/sys-root/mingw:g' -i /home/jehan/cross-compile/deps/usr/x86_64-w64-mingw32/sys-root/mingw/bin/*-config
	sed -e 's:/usr/i686-w64-mingw32/sys-root/mingw:/home/jehan/cross-compile/deps/usr/i686-w64-mingw32/sys-root/mingw:g' -i /home/jehan/cross-compile/deps/usr/i686-w64-mingw32/sys-root/mingw/bin/*-config
	ln -s noX usr/i686-w64-mingw32/sys-root/mingw/include/X11
	ln -s noX usr/x86_64-w64-mingw32/sys-root/mingw/include/X11

	#remove stuff provided by installed mingw
	for f in /usr/i686-w64-mingw32/lib/*
	do
		l="${f/*\/}"
		if [ -f "usr/i686-w64-mingw32/sys-root/mingw/lib/$l" ]
		then
			rm -f "usr/i686-w64-mingw32/sys-root/mingw/lib/$l"
		fi
	done
	for f in /usr/x86_64-w64-mingw32/lib/*
	do
		l="${f/*\/}"
		if [ -f "usr/x86_64-w64-mingw32/sys-root/mingw/lib/$l" ]
		then
			rm -f "usr/x86_64-w64-mingw32/sys-root/mingw/lib/$l"
		fi
	done

	ln -s x86_64-w64-mingw32 usr/amd64-w64-mingw32

	chmod +x usr/i686-w64-mingw32/sys-root/mingw/bin/*-config
	chmod +x usr/x86_64-w64-mingw32/sys-root/mingw/bin/*-config
fi

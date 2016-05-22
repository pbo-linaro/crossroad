=========
crossroad
=========

--------------------------------------
Cross-Compilation Environment Toolkit.
--------------------------------------

:Date: 2013-10-14
:Version: @VERSION@
:Manual section: 1
:Author: jehan@girinstud.io

SYNOPSIS
========

In a normal environment:
~~~~~~~~~~~~~~~~~~~~~~~~
**crossroad** [--help] [--version] [--list-targets] [--compress=<ARCHIVE.zip> <TARGET> <PROJECT> [...]] [--reset <TARGET> <PROJECT> [...]] [--symlink <TARGET> <PROJECT> [<LINK_NAME>]] [[--run=<script> [--no-exit-after-run]] <TARGET> <PROJECT>]

In a crossroad environment:
~~~~~~~~~~~~~~~~~~~~~~~~~~~
**crossroad** [--help] [--version] <command> [<args>]

DESCRIPTION
===========

**Crossroad** is a developer tool to prepare your shell environment for cross-compilation.

OPTIONS
=======

--version                               Show program's version number and exit
-h, --help                              Show the help message and exit. If a *TARGET* is provided, show information about this platform.
-l, --list-targets                      List all known targets
-L, --list-projects                     List all projects for a given target.
-c, --compress                          Compress an archive (zip support only), with the given name, of the named platform/projects.
-s, --symlink                           Create a symbolic link of the named platform.
--reset                                 Effectively delete TARGET's tree. Don't do this if you have important data saved in there.
-r, --run                               Run the given shell script inside the cross-build environment.
-n, --no-exit-after-run                 Do not exit the cross-build environment after running the script. Otherwise exit immediately and return the script's return value.

USAGE AND EXAMPLES
==================

Setting Up
~~~~~~~~~~

`Crossroad` does not need any particular cross-compilation tool to run,
but it will tell you what you are missing, and you won't be able to enter
a cross-compilation environment until this is installed.

List available and unavailable targets with::

    $ crossroad --list-targets
    crossroad, version 0.4.4
    Available targets:
    w64                  Windows 64-bit

    Uninstalled targets:
    w32                  Windows 32-bit

In the above example, I can compile for Windows 64-bit, not 32-bit.

To get details about a target's missing dependencies, for instance
Windows 32-bit::

    $ crossroad -h w32
    w32: Setups a cross-compilation environment for Microsoft Windows operating systems (32-bit).

    Not available. Some requirements are missing:
    - i686-w64-mingw32-gcc [package "gcc-mingw-w64-i686"] (missing)
    - i686-w64-mingw32-ld [package "binutils-mingw-w64-i686"]

It will return a list of required binaries that `crossroad` cannot find.
If you actually installed them, the most likely reason is that you should
update your `$PATH` with the right location. In the above example,
`crossroad` could find your minGW linker, but not the compiler. It also
informs you of a possible package name (based on a Linux Mint
distribution. Your distribution may use a different name, but it would
still give a useful hint to search in your package manager).

Install the missing requirements and run crossroad again::

    $ crossroad --list-targets
    crossroad, version 0.4.4
    Available targets:
    w32                  Windows 32-bit
    w64                  Windows 64-bit
    $ crossroad -h w32
    w32: Setups a cross-compilation environment for Microsoft Windows operating systems (32-bit).

    Installed language list:
    - C
    Uninstalled language list:
    - Ada                 Common package name providing the feature: gnat-mingw-w64-i686
    - C++                 Common package name providing the feature: g++-mingw-w64-i686
    - OCaml               Common package name providing the feature: mingw-ocaml
    - Objective C         Common package name providing the feature: gobjc++-mingw-w64-i686
    - fortran             Common package name providing the feature: gfortran-mingw-w64-i686

You will notice that now **w32** is available in your list of target, but
also the help is more complete and will also tell you a list of possible
programming languages that MinGW could handle if you installed additional
packages.

*Note: crossroad has actually been tested only with C and C++ projects.
But I welcome any usage report or patch for other languages.*

Optional Step: cleaning any previous cross-compilation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

`Crossroad` saves your work state from one use to another, which
allows you to pause a compilation work and continue later. It also means
that your cross-compiled tree will get filled with time. If you want to
restart your project from scratch with a clean prefix, reset
your project before you enter it with this optional step:

::

    $ crossroad --reset w64 myproject

This is an optional step, and you should not run it if you are actually
expecting to continue where you left `crossroad` the previous time.

**Warning: do not run this --reset if you have important data in your
prefix! Actually you should never have any important data there! It
should only contain your cross-compiled binaries and dependencies.**

Entering a Cross-Compilation Environment
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

::

    $ crossroad w64 myproject

This will set up a Windows 64-bit cross-compilation environment for a
project called `myproject`, and you will be greeted by a message telling
you basics information. "myproject" is obviously to be replaced by
any name which fits your specific job, for instance the name of the
program you wish to crossbuild.

In order for you not to mistake several opened shells, a `crossroad`
prompt will be a modified version of your usual prompt.
A small red ``w64✘myproject`` at the start (only adding information.
Whatever prompt hack you may have made — for instance displaying
information of a code repository — will be untouched) to show you are
in your working cross-compilation environment.
For instance if your prompt is usually `user@host ~/some/path $`, your
`crossroad` prompt will be `w64✘myproject user@host ~/some/path $`.

*Note: only `bash` and `zsh` are supported right now.*

All necessary environment variables for successful builds, like PATH,
LD_LIBRARY_PATH, etc., are set for you.
Moreover `crossroad` behavior is modified once in a cross-compilation
environment. You can `crossroad -h` or `crossroad help` to see the new
list of commands.

You are now ready to configure and compile any project for your target
platform.

In a crossroad environment
~~~~~~~~~~~~~~~~~~~~~~~~~~

Get available actions
.....................

Once in a crossroad environment, crossroad will behave differently and
have a list of commands.

Display the list of commands with::

    $ crossroad help
    Usage: crossroad [--help] [--version] <command> [<args>]

    Any crossroad environment provides the following commands:
    configure            Run `./configure` in the following directory for your cross-compilation environment.
    cmake                Run cmake for your cross-compilation environment.
    ccmake               Run ccmake for your cross-compilation environment.

    Crossroad's w64 environment proposes the following commands:
    info                 Display package details.
    install              Install the list of packages and all their dependencies.
    list_files           List files provided by packages.
    uninstall            Uninstall packages.

    See `crossroad help <command>` for more information on a specific command.

Each target share some base commands (configure, cmake and ccmake) and
may have its own custom list of commands.

Windows only: Pre-Built Dependency Manager
..........................................

The targets `w32` and `w64`, respectively for Windows 32 and 64-bit,
allow to install various dependency packages.
Let's say your app requires gtk2 and zlib.

First you can see if the pre-built gtk2 version is sufficient::

    $ crossroad info gtk2
    Package "mingw64-gtk2":
            Summary: Library for Creation of Graphical User Interfaces (version 2)
            Project URL: http://www.gtk.org/
            Version: 2.24.18 (release: 2.2 - epoch: 0)
            Description: GTK+ is a highly usable, feature rich toolkit for creating graphical user interfaces which boasts cross platform
                         compatibility and an easy to use API.
                         
                         GTK+ was initially developed for and used by the GIMP, the GNU Image Manipulation Program. It is called the "The GIMP
                         ToolKit" so that the origins of the project are remembered. Today it is more commonly known as GTK+ for short and is
                         used by a large number of applications including the GNU project's GNOME desktop.

You can do the same for zlib and if it suits you, install them::

    $ crossroad install gtk2-devel zlib-devel

All dependencies of these packages will be installed as well.

In case of mistake, you can also uninstall a package with::

    $ crossroad uninstall zlib-devel

If ever `crossroad` dependency manager does not have your required
package, or with inadequate version, you will have to compile it
(see `Build a Project`_ section).

*Note: even though `crossroad` already has a nice built-in dependency
manager, many features are still missing. In particular there is no
dependency support on uninstall (so be aware you may end up with a
broken prefix when you uninstall carelessly), and there is no track
of what you already installed (so you can endlessly reinstall the
same packages).*

Also the package manager will overwrite any file in the crossroad tree.
This is by-design, and you should never consider the crossroad tree as a
safe working place, but rather as a temporary cache of foreign-platform
binaries, which can be erased or moved over to the foreign platform at
any time. In particular keep your code and any working material at your
usual development location.

Currently `crossroad` uses pre-compiled package repositories from the
`openSUSE cross-platform builds`_.
I would welcome any patch to use any other pre-compiled repositories
alongside, provided they are safe.

Build a Project
...............

GNU-style project (autotools)
*****************************

Let's imagine you want to compile any software with a typical GNU
compilation system, for Windows 64-bit.

(1) Enter your source code::

        $ cd /some/path/to/your/source/

(2) Configure your build.

    In a typical GNU code, you should have access to a `./configure`
    script, or with ways to build one, for instance by running an
    `./autogen.sh` first. You should not run `./configure` directly,
    but run it through this command instead::

        $ crossroad configure

    There is no need to add a --prefix, a --host, or a --build. These
    are automatically and appropriately set up for you.

    Of course you should still add any other option as you would
    normally do to your `configure` step.
    For instance if your project had a libjpeg dependency that you want to
    deactivate::

        $ crossroad configure --without-libjpeg

    See the `./configure --help` for listing of available options.

    Note that crossroad also supports VPATH builds. If you wish to build
    a project whose source is in ../myproject/ for instance, you could
    run::

        $ crossroad ../myproject/configure --without-libjpeg

(3) If your configure fails because you miss any dependency, you can try
    and install it with the `Windows only: Pre-Built Dependency Manager`_
    or by compiling it too.

    Do this step as many times as necessary, until the configure step (2)
    succeeds. Then go to the next step.

(4) Build::

        $ make
        $ make install

(5) All done! Just exit your cross-compilation environment with *ctrl-d*
    or `exit` when you are finished compiling all your programs.

INFO: this has been tested with success on many GNU projects,
cross-compiled for Windows: cairo, babl, GEGL, glib, GTK+, libpng,
pango, freetype2, gdk-pixbuf and GIMP.

CMake Project
*************

Cmake uses toolchain files. Crossroad prepared one for you, so you don't
have to worry about it.
Simply replace the step (2) of the `GNU-style project (autotools)`_
example with this command::

    $ crossroad cmake .

A common cmake usage is to create a build/ directory and build there.
You can do so with crossroad, of course::

    $ mkdir build; cd build
    $ crossroad cmake ..

Alternatively crossroad allows also to use the curses interface of
`cmake`::

    $ crossroad ccmake .

The rest will be the same as a normal CMake build, and you can add
any options to your build the usual way.

INFO: This has been tested with success on allegro 5 and Exiv2,
cross-compiled for Windows.

Other Build System
******************

It has not been tested with any other compilation system up to now. So
it all depends what they require for a cross-compilation.
But since a `crossroad` environment prepares a bunch of environment
variables for you, and helps you download dependencies, no doubt it will
already make your life easier.

The `configure`, `cmake` and `ccmake` command are simple wrappers around
any normal `./configure` script, and the `cmake` and `ccmake` commands,
adding some default options (which crossroad prepared) for successful
cross-compilation.

For instance `crossroad configure` is the equivalent of running::

    $ ./configure --prefix=$CROSSROAD_PREFIX --host=$CROSSROAD_HOST --build=$CROSSROAD_BUILD

And `crossroad cmake /some/path` is nothing more than::

    $ cmake /some/path -DCMAKE_INSTALL_PREFIX:PATH=$CROSSROAD_PREFIX -DCMAKE_TOOLCHAIN_FILE=$CROSSROAD_CMAKE_TOOLCHAIN_FILE

Here is the list of useful, easy-to-remember and ready-to-use,
environment variables, prepared by crossroad:

- $CROSSROAD_PREFIX;

- $CROSSROAD_HOST;

- $CROSSROAD_BUILD;

- $CROSSROAD_CMAKE_TOOLCHAIN_FILE.

- $CROSSROAD_PLATFORM

- $CROSSROAD_PLATFORM_NICENAME

- $CROSSROAD_PROJECT

- $CROSSROAD_WORD_SIZE

What it means is that you can use these for other compilation systems.
You can also use your `crossroad` prefix, even for systems which do not
require any compilation. Let's say for instance you wish to include a
pure python project in your build. No per-platform compilation is needed,
but you still want to carry all the files in the same prefix for easily
move all together later on.
So just run::

    $ ./setup.py --prefix=$CROSSROAD_PREFIX

and so on.

INFO: as you may have guessed, `$CROSSROAD_PREFIX` encapsulates your new
cross-build and all its dependencies.
Though in most cases, you should not need to manually go there do
anything, you still can (for instance to change software settings, etc.)
`cd $CROSSROAD_PREFIX`.

WARNING: as said previously in the `Windows only: Pre-Built Dependency Manager`_ section, do
not perform there or leave any unique work that has not been saved
somewhere else as well.

WARNING: these environment variables are set up by `crossroad` and it is
unadvisable to modify them. You are likely to break your cross-build
environment if you do so. The only CROSSROAD\_\* variable that you can
safely change are the ones listed in **CONFIGURATION**.

Import your Project to your Target Platform
............................................

To test your binaries on an actual Windows machine, `crossroad` provides
2 tools.

(1) Make a zip of your whole cross-compiled tree::

        $ crossroad -c mysoftware.zip w64 myproject w64 otherproject

    This will create a zip file `mysoftware.zip` that you can just move over
    to your test Windows OS. Then uncompress it, and set or update your PATH
    environment variable with the `bin/` directory of this uncompressed
    prefix.

    *Note: only zip format supported for the moment, since it is the most
    common for Windows.*

(2) If you are running Windows in a VM for instance, or are sharing
    partitions, you can just add a symbolic link in a shared directory.
    Just cd to the shared directory and run::

        $ crossroad -s w64 myproject

    This will create a symlink directory named "crossroad-w64-myproject" linking to
    the "myproject" project's prefix for w64. Since the directory is
    shared, it should be visible in Windows as a normal directory.


**Finally run your app, and enjoy!**

Bonus: testing your win32 binaries on the build platform with Wine
==================================================================

A `crossroad` environment is actually set-up with a few environment
variables so that `Wine` can find the DLLs and win32 tools that you
installed through a `make install`.
Of course you will also need to ensure that Wine is registred in
`binfmt_misc` to execute win32 binaries automatically, otherwise it
won't work.

This means that you may attempt to test your software, or even run some
`make check` tests, and it may work. A lot of "*may*", since obviously
there is no certaincy when it comes to `Wine`. Sometimes it may work great,
sometimes not. Newer versions of Wine even often have regressions: things
which used to work suddenly won't.
So do not consider this feature as perfect as testing on a native win32
platform. Nevertheless this is still a big conveniency.
For the records, I have been able to run successfull `make check` on
projects as complex as **GIMP**.

Bonus 2: install win32 software with Wine
=========================================

Some software have proved extremely hard to cross-compile, mostly because
of weird custom build systems or strange designs. I had this case for
Python, which even went as far as forbidding cross-builds for hosts they
didn't approve with specific configure tests.
I have been therefore unable to crossbuild it. One solution could be to
fix the build system (which I started to do for Python until I discovered
bug reports with patches for specifically this, and opened for eons), or
to install in Windows, and import the data (but then you lose the
flexibility or building all on the same machine).

My other workaround has been to install with Wine. In my Python example, I
have indeed been able to run the 32-bit installer (not the 64-bit one).
When doing so in a crossroad environment, the data will be automatically
installed under `$CROSSROAD_PREFIX/wine/`.
Then you just have to update any necessary environment variable in order
for your builds to discover any library/header if necessary (I don't see
how to do so automatically with a Windows tree being so "random").

Configuration
=============

`Crossroad` relies on XDG standards.
Right now it does not need any configuration file, but it may someday.
And these will be in $XDG_CONFIG_HOME/crossroad/
(defaults to $HOME/.config/crossroad/).

Cache is saved in $XDG_CACHE_HOME/crossroad/ and cross-compiled data in
$XDG_DATA_HOME/crossroad/.

One of the only configuration right now is that in case you use a
self-installed MinGW-w64 prefix of Windows libraries, if they are not in
the same prefix as the MinGW-64 executables you run, you can set
`$CROSSROAD_CUSTOM_MINGW_W32_PREFIX` and
`$CROSSROAD_CUSTOM_MINGW_W64_PREFIX` respectively for your 32-bit and
64-bit installation of MinGW-w64.  Normally you will not need these. In
most usual installation of MinGW-w64, `crossroad` should be able to
find your Windows libraries prefix.

Note that cross-built dependency search through pkg-config won't use
`$PKG_CONFIG_PATH` (this variable is only used for native builds).
If it does, there is a problem in your `configure` file.
If you wish to add a PATH for pkg-config in cross-compilation mode,
please use `$CROSSROAD_PKG_CONFIG_PATH` instead.

Also if the environment variable `$CROSSROAD_PS1` is set, it will be
used as your crossroad prompt, instead of constructing a new prompt from
the currently set one.

Finally a bash-completion script is available in::

    @DATADIR@/share/crossroad/scripts/shells/bash/bash_completion.d/crossroad

If you wish bash completion on the `crossroad` command, which can be very
useful, you should copy or link this file either in the system or your user
`completions` directory.
The system directory can be found with the command "`pkg-config
--variable=completionsdir bash-completion`" (often `/usr/share/bash-completion/completions`).
The user directory is `${XDG_DATA_HOME}/bash-completion/completions`.
Finally refresh your shell by running the `bash_completion` script (often in
`/etc/` or in `/usr/share/bash-completion/`)::

    $ mkdir -p ${BASH_COMPLETION_USER_DIR:-${XDG_DATA_HOME:-$HOME/.local/share}/bash-completion}/completions
    $ cd !$
    $ ln -s @DATADIR@/share/crossroad/scripts/shells/bash/bash_completion.d/crossroad
    $ . /etc/bash_completion

The last command may not be necessary nor available on some platforms (for
instance Fedora). Starting a new shell would be enough to apply the new bash
completion rules.

Contributing
============

You can view the git branch on the web at
http://git.tuxfamily.org/crossroad/crossroad And clone it with::

    $ git clone git://git.tuxfamily.org/gitroot/crossroad/crossroad.git

Then send your `git-format`-ed patches by email to crossroad <at> girinstud.io.

About the name
==============

The name is a hommage to "*cross road blues*" by **Robert Johnson**,
which itself spawned dozens, if not hundreds, of other versions by so
many artists.
I myself always play this song (or rather a version with modified lyrics
adapted to my life) in concerts.
The colored texts when you enter and exits a crossroad are excerpts of
my modified lyrics.

See Also
========

* Author's website: http://girinstud.io

* MinGW-w64 project: http://mingw-w64.sourceforge.net/

* Fedora MinGW project: https://fedoraproject.org/wiki/MinGW

* openSUSE cross-platform builds: https://en.opensuse.org/openSUSE:Build_Service_Concept_Windows_Support

.. _openSUSE cross-platform builds: https://en.opensuse.org/openSUSE:Build_Service_Concept_Windows_Support

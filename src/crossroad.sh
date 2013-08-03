#!/bin/sh

CROSSROADS_VERSION=0.1
CROSSROADS_AUTHORS="Jehan (Studio Girin) [jehan at girinstud.io]"

usage ()
{
    printf "Usage: crossroads [TARGET] [--help] [--env]\n\n"
    echo "Set a cross-compilation environment for the target platform TARGET"
    echo "Possible platforms:"
    printf "\tw64: Windows 64 bits\n"
    printf "\tw32: Windows 32 bits\n"
    printf "NOTE: this tools is designed towards developers who wish to be able to cross-compile and test their software on their UNIX platform. "
    printf "It may not be suited for other cross-compilation usage, like packaging for the target platform.\n"
    printf "Nevertheless any patch most welcome to ${CROSSROADS_AUTHORS}.\n"
    #NOTE: about this, what are the best installers?
    # http://www.jrsoftware.org/isinfo.php is not FLOSS, but seems ok.
}

if [ "$#" != 1 ]; then
    printf "Error: please provide a target platform.\n\n"
    usage
    exit 1
fi;

# propose a basic dependency list for various big packages.
# Ex: GIMP: ...
# --bundle? --bootstrap?

# TODO: allows multi-options by looping!
if [[ "$1" == "--help" || "$1" == "-h" ]]; then
    usage
    exit 0
elif [[ "$1" == "--version" || "$1" == "-v" ]]; then
    printf "crossroads $CROSSROADS_VERSION by "
    printf "${CROSSROADS_AUTHORS}.\n"
    exit 0
elif [ "$1" == "--env" ]; then
    echo "List of available environment variable, set by crossroads:"
    printf "\tPREFIX: the recommended prefix where to compile your cross-compiled projects.\n"
    printf "\tDEP_PREFIX: a prefix where various pre-cross-compiled libraries that are used by many projects are installed.\n"
    printf "\tPKG_CONFIG_LIBDIR: unset by crossroads to ensure no library compiled for your current platform is used by mistake.\n"
    printf "\tPKG_CONFIG_PATH: the paths to find all cross-compiled libraries for the current platform.\n"
    printf "\tHOST: the mingw64 name for your target platform.\n"
    printf "\tPLATFORM: a short name for your target platform.\n"
    printf "\tPLATFORM_NICENAME: the longer name for your target platform\n"
    printf "\tLD_LIBRARY_PATH: path to cross-compiled libraries for the linker.\n"
    printf "\tACLOCAL_FLAGS: \n"
    printf "\tCFLAGS: include path for compilation.\n"
    printf "\tLDFLAGS: libraries path for compilation\n"
    exit 0
elif [ "$1" == "w64" ]; then
    export HOST=x86_64-w64-mingw32
    export PLATFORM=w64
    export PLATFORM_NICENAME="Windows 64 bits"
elif [ "$1" == "w32" ]; then
    export HOST=i686-w64-mingw32
    export PLATFORM=w32
    export PLATFORM_NICENAME="Windows 32 bits"
else
    printf "ERROR: '$1' is not a supported platform value.\n\n"
    usage
    exit 1
fi;

# Go into said environment.
CROSSROADS_PREFIX=$HOME/.local #TODO
export PREFIX="${HOME}/cross-compile/${PLATFORM}"
if [ -d "$PREFIX" ]; then
    if [ ! -f "$PREFIX/.crossroads" ]; then
        echo "The directory '$PREFIX' exists but does not seem to be a crossroads cross-environment."
        # TODO: make possible to force it with -f?
        exit 1
    fi
else # Create the environment,
    mkdir -p $PREFIX
    if [ "$?" != 0 ]; then
        echo "Cross compilation environment could not be created at $PREFIX."
        exit 1
    fi
    touch "$PREFIX/.crossroads"
    # tar -xjf $CROSSROADS_PREFIX/share/crossroads/mingw-w32-bin_x86_64-linux_20121031.tar.bz2 --directory="$PREFIX"
    # TODO: if never installed before, install various default libs + keep db of what has been installed for this cross-comp enviro.
    # Make de-install possible?
fi

cd $PREFIX
# TODO: should use the same shell as $SHELL. PS1 should be changed as well depending on $SHELL.
bash --rcfile "$CROSSROADS_PREFIX/share/crossroads/post_bashrc"

PRINT_PURPLE='\e[1;35m'
PRINT_RESET='\e[0m'
printf "${PRINT_PURPLE}You can run, you can run.\nTell your friend boy Greg T. that you were standing at the crossroads.\n"
printf "I believe you were sinking down.${PRINT_RESET}\n"

# TODO: Create some tools which would exist only in the path in the cross-comp environment? Like installation, etc.
# redefine crossroads inside the crossroads env?!? There is no reason there to enter a new env. But you may want to do other things.
# For install the install bundle feature...

# Instead of a chroot, a warning run when typical commands (like ./configure) are run? Maybe with an alias? (will aliases work with non
# $PATH commands?).

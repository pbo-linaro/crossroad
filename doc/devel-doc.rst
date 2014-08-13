Supporting a New Target Platform
================================

1/ Add a python 3 script in platforms/ with the following data:

- The `name` global variable is the short name listed in a `crossroad --list-all`.
- The `short_description` is the natural language description to the right of the short name.
- is_available() is a function which returns a boolean, True if the cross-compilation environment
is available, False otherwise.
It is up to you to decide how you want to implement this. You can have a look at existing
implemented platforms where we basically search for a list of command that we will require,
for instance a specific cross-compiler, cross-linker, etc.
- requires() returns a string, where you can give human-readable information for the user to
know what to install in order to make the environment available. Do not hesitate to
pretty-format this string, since this is for human consumption.
- language_list() returns a couple of ([installed], {uninstalled}) language.
`installed` is a list of strings. Ex: ["C", "C++", "Ada"].
`uninstalled` is a dictionnary, whose key is a language name and the value is a list
of common package names which would provide the necessary features.
Ex: {"Ada": ["gnat-mingw-w64-x86-64"], "Ocaml": ["mingw-ocaml"]}
- prepare() takes a path as argument, which will be the prefix where everything
will be installed. This is where you will prepare a new environment, in case
anything particular has to be done for this particular platform. Note that prepare()
will be run only once, at the new prefix creation, then never again. prepare()
returns True on success, False if an error occured.

2/ By default an environment only provides the basic features `configure`, `cmake`,
`ccmake` and `prefix`.
You may create any other additional feature of your choice by creating a function
starting with "crossroad_". The right part will be used as the name of the function.
The first line of the doc string will be used as the short description shown in a `crossroad help`.
The whole doc string will be the long description as shown in `crossroad help function`.
Parameters name will also be used as sub-option names, and therefore must be well chosen.
- positional arguments will be mandatory non-named positional argument for the shell command too.
- varargs will allow to accept an indefinite list of non-named arguments after the positional ones.
- keyword arguments will become --arg-name option. Only boolean arguments are valid right now,
and you need a default value.
Note: there may be support of keyword argument of other type in the future to allows --arg-name=value options.

For instance, let's say your environment has a dependency installation feature, and you
implemented a search function. It's signature can be something like::

    def crossroad_search(*keywords, src:bool = False, search_files:bool = False):
        '''
        Search keywords in package names.
        If --search-files is also set, also search in files.
        '''
        DO SOMETHING

Then the `crossroad help search` output will be automatically generated this way::

    crossroad install <packages...> [--src]

        Install the list of packages and all their dependencies.
        If --src is provided, it installs the source packages, and not the main packages.

3/ You may create any other internal variables and functions. As long as they don't start
as "crossroad_", they will be hidden from the outside world.

4/ If needed to support any of your additional platform-specific features,
you can add more complex scripts under scripts/.
To use them in your platform code, know that they will be available under:
`@DATADIR@/share/crossroad/scripts`. `@DATADIR@` will be automatically changed
into the actual datadir at install time, depending on your chosen prefix.

5/ Add scripts/bash/bashrc.${short_name} and scripts/zsh/zshrc.${short_name} for bash and zsh respectively.
These will be run each time you enter your environment, thus must set up basic information about it. These includes:
- CROSSROAD_PLATFORM_NICENAME: as the name applies, some natural language name of the platform.
- CROSSROAD_PLATFORM: the small name, usually same as ${short_name}.
- CROSSROAD_HOST: the host name. Very important, it must be the real host name which prefixes all cross-tools.
- CROSSROAD_WORD_SIZE: usually 32 or 64 (bit implied).
Add and do anything else which is specific to the shell.

6/ Add a scripts/cmake/toolchain-${short_name}.cmake file, which will be the cmake toolchain
for this environment. Check current platforms as example.
There is nothing to add for autotools. Support is automatic.

7/ Normally that's it. You should not have to update setup.py. You should still check that everyone works fine from there.


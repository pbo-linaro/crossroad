#!/usr/bin/python3
# -*- coding: utf-8 -*-
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

import importlib.machinery
import optparse
import os
import sys
import subprocess
import time
import shutil
import zipfile
import mimetypes
import errno

### Current Crossroad Environment ###

crossroad_platform = None
try:
    crossroad_platform = os.environ['CROSSROAD_PLATFORM']
except KeyError:
    pass

# Redirect to the in-crossroad binary.
if crossroad_platform is not None:
    in_crossroad = os.path.join('@DATADIR@', 'share/crossroad/scripts/in-crossroad.py')
    sys.exit(subprocess.call([in_crossroad] + sys.argv[1:], shell=False))

### Check all available platforms. ###

# This string will be replaced by setup.py at installation time,
# depending on where you installed default data.
install_datadir = os.path.join(os.path.abspath('@DATADIR@'), 'share/')

xdg_data_home = None
try:
    xdg_data_home = os.environ['XDG_DATA_HOME']
except KeyError:
    # os.path.expanduser will first check the $HOME env variable, then the current user home.
    # It is cleverer than checking the environment variable only.
    home_dir = os.path.expanduser('~')
    if home_dir != '~':
        xdg_data_home = os.path.join(home_dir, '.local/share')

def get_datadirs():
    '''
    {datadir} is evaluated using XDG rules.
    '''
    # User personal script have priority.
    if xdg_data_home is not None:
        datadirs = [xdg_data_home]
    else:
        datadirs = []

    # Then installation-time files.
    datadirs += [install_datadir]

    # Finally platform global files.
    try:
        other_datadirs = os.environ['XDG_DATA_HOME']
        if other_datadirs.strip() == '':
            datadirs += ['/usr/local/share/', '/usr/share/']
        else:
            datadirs += other_datadirs.split(':')
    except KeyError:
        datadirs += ['/usr/local/share/', '/usr/share/']
    return datadirs

def load_platforms():
    '''
    All platforms are available in {datadir}/crossroads/platforms/.
    '''
    available_platforms = {}
    other_platforms = {}
    datadirs = get_datadirs() + ['../..'] # TODO: remove! For dev only.
    platform_files = []
    for dir in datadirs:
        dir = os.path.abspath(os.path.join (dir, 'crossroad/platforms'))
        try:
            platform_files += [os.path.join(dir, f) for f in os.listdir(dir)]
        except OSError:
            # No such directory maybe.
            continue
    for platform_file in platform_files:
        # They are supposed to be python script. Let's try and import them.
        (dir, file) = os.path.split(platform_file)
        (module, ext) = os.path.splitext(file)
        if ext.lower() != ".py":
            continue
        loader = importlib.machinery.SourceFileLoader(module, platform_file)
        try:
            platform = loader.load_module(module)
        except ImportError:
            continue
        except FileNotFoundError:
            sys.stderr.write ("Module not found: %s\n", platform_file)
            continue
        except SyntaxError as err:
            sys.stderr.write ("Syntax error in module %s:%s\n", platform_file, err.text)
            continue
        try:
            # XXX I don't test other mandatory attributes because if missing,
            # that's an obvious bug that we want fixed asap.
            if platform.name in available_platforms or platform.name in other_platforms:
                # A platform with the same name has already been processed.
                # It may happen if for instance the user overrod a spec with
                # one's own script.
                continue

            if platform.is_available():
                available_platforms[platform.name] = platform
            else:
                other_platforms[platform.name] = platform
        except AttributeError:
            # not a valid platform.
            continue

    return (available_platforms, other_platforms)

def get_projects(target):
    '''
    All projects are available in $XDG_DATA_HOME/crossroad/roads/{target}/.
    '''
    target_path = os.path.join(xdg_data_home, 'crossroad/roads', target)
    if os.path.isdir(target_path):
        available_projects = os.listdir(target_path)
    else:
        available_projects = []
    return available_projects

(available_platforms, other_platforms) = load_platforms()

### Start the Program ###

version = '@VERSION@'
maintainer = '<jehan at girinstud.io>'

usage  = 'Usage: crossroad [--help] [--version] [<TARGET> <PROJECT> [--copy=<PROJECT>] [--run=<script> [--no-exit-after-run]]\n'
usage += '                 [--reset <TARGET> <PROJECT>] [...]] [--list-targets] [--list-projects=<TARGET>]\n'
usage += '                 [--symlink <TARGET> <PROJECT> [<link-name>]] [--compress=<archive.zip> <TARGET> <PROJECT> [...]]\n'

platform_list = "Available targets:\n"
for name in available_platforms:
    platform = available_platforms[name]
    platform_list += "- {:<20} {}\n".format(platform.name, platform.short_description.strip())

unavailable_platform_list = '\nUninstalled targets:\n'
for name in other_platforms:
    platform = other_platforms[name]
    unavailable_platform_list += "{:<20} {}\n".format(platform.name, platform.short_description.strip())

cmdline = optparse.OptionParser(usage,
        version="%prog, version " + version,
        description = "Set a cross-compilation environment for the target platform TARGET",
        conflict_handler="resolve")
cmdline.add_option('-r', '--run',
    help = 'Run the given shell script inside the cross-build environment.',
    action = 'store', type="string", dest = 'script', default = None)
cmdline.add_option('-n', '--no-exit-after-run',
    help = "Do not exit the cross-build environment after running the script. Otherwise exit immediately and return the script's return value.",
    action = 'store_true', dest = 'no_exit', default = False)
cmdline.add_option('--copy',
    help = 'A new project is made as a copy of an existing project for the same target.',
    action = 'store', dest = 'copy', default = None)
cmdline.add_option('-l', '--list-targets',
    help = 'list all known targets.',
    action = 'store_true', dest = 'list_targets', default = False)
cmdline.add_option('-L', '--list-projects',
    help = 'list all existing projects for a given target.',
    action = 'store', type="string", dest = 'list_projects', default = None)
cmdline.add_option('-h', '--help',
    help = 'show this help message and exit. If a TARGET is provided, show information about this platform.',
    action = 'store_true', dest = 'help', default = False)
cmdline.add_option('-c', '--compress',
    help = 'compress an archive (zip only) of projects.',
    action = 'store', type="string", dest = 'archive', default = None)
cmdline.add_option('-s', '--symlink',
    help = 'create a symbolic link of the named platform.',
    action = 'store_true', dest = 'symlink', default = False)
cmdline.add_option('--reset',
    help = "effectively delete TARGET's tree. Don't do this if you have important data saved in there.",
    action = 'store_true', dest = 'reset', default = False)

(options, args) = cmdline.parse_args()

def copy_file(from_file, to_file, from_prefix, to_prefix):
    if os.path.isdir(from_file) and not os.path.islink(from_file):
        try:
            os.makedirs(to_file, exist_ok=True)
        except FileExistsError:
            # This exception would not happen if `to_file` exists and is a directory.
            # But I had the strange case where it existed as a file, and the error still occurred.
            # Not sure this is the right solution, but I will just output a warning and delete it.
            logging.warning ("{} exists as a file, but we want a directory. Deleting.")
            os.unlink (to_file)
            os.makedirs(to_file, exist_ok=True)
        for f in os.listdir(from_file):
            copy_file(os.path.join(from_file, f), os.path.join(to_file, f), from_prefix, to_prefix)
    elif os.path.islink(from_file):
        link_path = os.readlink(from_file)
        if not os.path.isabs(link_path):
            # Make the path absolute.
            link_path = os.path.join(os.path.dirname(from_file), link_path)
        link_path = link_path.replace(from_prefix, to_prefix)
        # Make the path relative in the end.
        link_path = os.path.relpath(link_path, start=os.path.dirname(to_file))
        os.symlink(link_path, to_file)
    else:
        # You can't plan all cases, but I try to plan common ones which I may need during
        # compilation.
        if to_file[-3:] == '.pc' or \
           to_file[-7:] == '-config' or \
           (mimetypes.guess_type(from_file)[0] is not None and
            (mimetypes.guess_type(from_file)[0][:5] == 'text/' or
            (mimetypes.guess_type(from_file)[0] == 'application/x-shared-library-la'))) or \
           (shutil.which('mimetype') is not None and \
           # The `mimetype` command is more efficient than the mimetype lib of Python.
            (subprocess.check_output(['mimetype', '-b', from_file],
                                     universal_newlines=True)[:5] == 'text/' or
             subprocess.check_output(['mimetype', '-b', from_file],
                                     universal_newlines=True) == 'application/x-shared-library-la')):
            try:
                fd = open(from_file, 'r')
                contents = fd.read()
                fd.close()

                contents = contents.replace(from_prefix, to_prefix)

                fd = open(to_file, 'w')
                fd.write(contents)
                fd.close()
            except (IOError, UnicodeDecodeError):
                # For some reason, some files may show a text mimetype (for instance
                # because they start with ascii) though they are definitely binary.
                # In such a case, a UnicodeDecodeError may happen.

                # When something happens in the special replace code, we just
                # let the basic copy code take the relay
                pass
            else:
                # If the replace code worked, we get out of the function.
                return
        try:
            shutil.copy(from_file, to_file, follow_symlinks=False)
        except OSError as err:
            if err.errno == errno.ENXIO:
                # I had this error with some pipes or similar files.
                # As a special exception, I pass the copy of such files.
                pass
            else:
                sys.stderr.write('File {} cannot be copied to {}.'.format(from_file, to_file))
                sys.exit(os.EX_CANTCREAT)

if __name__ == "__main__":
    if options.help:
        # I redefine help because I want to be able to show different
        # information when a platform is set.
        platform = None
        if len(args) == 1:
            if args[0] in available_platforms:
                platform = available_platforms[args[0]]
            elif args[0] in other_platforms:
                platform = other_platforms[args[0]]
        if platform is None:
            cmdline.print_help()
        else:
            if platform.__doc__ is not None:
                print("{}: {}\n".format(platform.name, platform.__doc__.strip()))
            if not platform.is_available():
                sys.stderr.write('Not available. Some requirements are missing:\n{0}'.format(platform.requires()))
            else:
                (installed, uninstalled) = platform.language_list()
                if installed != []:
                    installed.sort()
                    print("Installed language list:\n- {}".format("\n- ".join(installed)))
                if uninstalled != []:
                    uninstalled = [ "{:<20}Common package name providing the feature: {}".format(name, ", ".join(uninstalled[name])) for name in uninstalled]
                    uninstalled.sort()
                    print("Uninstalled language list:\n- {}".format("\n- ".join(uninstalled)))
                projects = get_projects(platform.name)
                if projects != []:
                    print("Current projects on this target:\n- {}".format("\n- ".join(projects)))
        sys.exit(os.EX_OK)

    if options.list_targets:
        cmdline.print_version()
        sys.stdout.write(platform_list)
        if len(other_platforms) > 0:
            sys.stdout.write(unavailable_platform_list)
        sys.stdout.write('\nSee details about any target with `crossroad --help <TARGET>`.\n')
        sys.exit(os.EX_OK)

    if options.list_projects is not None:
        if options.list_projects not in available_platforms:
            sys.stderr.write('Not a valid platform: {}\n'.format(options.list_projects))
            sys.exit(os.EX_USAGE)
        projects = get_projects(options.list_projects)
        # That's not pretty. This is not the way to localize!
        # But hey right now, crossroad is not localized at all. That's an English only tool.
        final_point = ':'
        if len(projects) == 0:
            final_point = 's.'
        elif len(projects) > 1:
            final_point = 's:'
        sys.stdout.write('Target {} has {} current project{}\n'.format(options.list_projects,
                                                                       len(projects) if len(projects) > 0 else 'no',
                                                                       final_point))
        for project in projects:
            sys.stdout.write ('- {}\n'.format(project))
        sys.exit(os.EX_OK)

    if options.reset:
        if len(args) == 0 or len(args) % 2 != 0:
            sys.stderr.write('You must specify a list of "platform project" for --reset.\n')
            sys.exit(os.EX_USAGE)

        platform = None
        project = None
        for platform_project in args:
            if platform is None:
                platform = platform_project
                continue
            project  = platform_project

            project_path = os.path.join(xdg_data_home, 'crossroad/roads/', platform, project)
            if platform not in available_platforms or not os.access(project_path, os.R_OK):
                sys.stderr.write('Project {} for {} is not built, or unreadable.\n'.format(project, platform))
                sys.exit(os.EX_NOPERM)
                sys.stderr.write('Not a valid platform: {}\n'.format(platform))
                platform = None
                project = None
                continue
            platform_path = os.path.join(xdg_data_home, 'crossroad/roads', platform, project)
            # XXX Or a --force option?
            try:
                sys.stdout.write('Project "{}" for target {} ({}) is going to be deleted in'.format(project, platform, platform_path))
                for i in range(5, 0, -1):
                    sys.stdout.write(' {}'.format(i))
                    sys.stdout.flush()
                    time.sleep(1)
            except KeyboardInterrupt:
                sys.stdout.write('\nAborting project deletion.\n')
                platform = None
                project = None
                continue
            sys.stdout.write('...\nDeleting {}...\n'.format(platform_path))
            try:
                shutil.rmtree(platform_path)
            except:
                sys.stderr.write('Warning: deletion of {} failed with {}\n'.format(platform_path, sys.exc_info()[0]))
            platform = None
            project = None
        sys.exit(os.EX_OK)

    if options.archive is not None:
        if options.archive[-4:].lower() != '.zip':
            # XXX may support other format in the future, so I could use a generic naming.
            # But in same time, zip seems the most prominent on Windows platform, so for transfer,
            # I support only this for now.
            sys.stderr.write('Error: sorry, only zip format archives are supported for the time being.\n')
            sys.exit(os.EX_UNAVAILABLE)
        if len(args) == 0 or len(args) % 2 != 0:
            sys.stderr.write('You must specify a list of "platform project" to include in your archive.\n')
            sys.exit(os.EX_USAGE)

        # XXX the last slash / is important because we will want to remove it from file archive name.
        archive_root = os.path.join(xdg_data_home, 'crossroad/roads/')
        project_paths = []

        platform = None
        project = None
        for platform_project in args:
            if platform is None:
                platform = platform_project
                continue
            project  = platform_project

            # Test existence and readability of the platform.
            project_path = os.path.join(archive_root, platform, project)
            if platform not in available_platforms or not os.access(project_path, os.R_OK):
                sys.stderr.write('Project {} for {} is not built, or unreadable.\n'.format(project, platform))
                sys.exit(os.EX_NOPERM)
            project_paths += [project_path]
            platform = None
            project = None
        # All looks good. Create the zip!
        sys.stdout.write('Generating an archive file...\n')
        archive_file = zipfile.ZipFile(options.archive, 'w',
                                       compression = zipfile.ZIP_DEFLATED,
                                       allowZip64 = True)
        for project_path in project_paths:
            # XXX should we followlinks=True to walk into directory links?
            for dirpath, dirnames, filenames in os.walk(project_path):
              for filename in filenames:
                file_path = os.path.join(dirpath, filename)
                archive_file.write(file_path,
                                   arcname = file_path.replace(archive_root, ''))
        sys.stdout.write('Archive file {} completed.\n'.format(options.archive))
        archive_file.close()
        sys.exit(os.EX_OK)

    if options.symlink:
        if len(args) != 2 and len(args) != 3:
            sys.stderr.write('You must specify the target and project to symlink, optionally followed by the link name.\n')
            sys.exit(os.EX_USAGE)
        platform = args[0]
        project = args[1]
        link_name = 'crossroad-{}-{}'.format(platform, project)
        if len(args) == 3:
            link_name = args[2]
            # When specifying a link name, it may be somewhere else than current directory.
            link_dir = os.path.dirname(os.path.abspath(link_name))
            if not os.path.exists(link_dir):
                try:
                    os.makedirs(link_dir, exist_ok = True)
                except:
                    sys.stderr.write('The directory {} could not be created. Cancelling.\n'.format(link_dir))
                    sys.exit(os.EX_IOERR)
        if os.path.exists(link_name):
            # TODO: --force option?
            sys.stderr.write('The file "{}" already exists.\n'.format(link_name))
            sys.exit(os.EX_IOERR)
        # Test existence and readability of the platform.
        project_path = os.path.join(xdg_data_home, 'crossroad/roads', platform, project)
        if platform not in available_platforms or not os.access(project_path, os.R_OK):
            sys.stderr.write('Project {} for {} is not built, or unreadable.\n'.format(project, platform))
            sys.exit(os.EX_NOPERM)
        os.symlink(project_path, link_name, target_is_directory=True)
        sys.exit(os.EX_OK)

    if len(args) > 0:
        if args[0] in other_platforms:
            sys.stderr.write('The platform "{}" is not available. Some requirements are missing:\n{}'.format(args[0], other_platforms[args[0]].requires()))
            sys.exit(os.EX_UNAVAILABLE)
        elif args[0] not in available_platforms:
            sys.stderr.write('"{}" is not a platform known by `crossroad`. Do not hesitate to contribute: {}\n'.format(args[0], maintainer))
            sys.exit(os.EX_UNAVAILABLE)

    # If we are here, it means we want to enter a crossroad environment.
    if len(args) == 1:
        projects = get_projects(args[0])
        if len(projects) == 0:
            try:
                project = input("Please enter a new project name for {}: ".format(args[0]))
            except (KeyboardInterrupt, EOFError):
                # Ctrl-c or Ctrl-d cancels.
                sys.stderr.write('\nCancelling.\n')
                sys.exit(os.EX_NOINPUT)
            if project.strip() == '':
                sys.stderr.write('Empty project name. Cancelling.\n')
                sys.exit(os.EX_USAGE)
        else:
            try:
                sys.stderr.write('Existing projects for {}:\n'.format(args[0]))
                for (n, p) in enumerate(projects):
                    sys.stderr.write('\t- enter "{}" ({})\n'.format(p, n))
                sys.stderr.write('\n')
                project = input('Please choose a project id (default: 0), or enter a new project name to create: ')
                if project.strip() == '':
                    project = 0
                try:
                    project_id = int(project)
                    if project_id >= 0 and project_id < len(projects):
                        project = projects[project_id]
                except ValueError:
                    # Project is considered as a string and stays as is.
                    pass
            except KeyboardInterrupt:
                sys.stderr.write('\nCancelling. Bye!\n')
                sys.exit(os.EX_USAGE)
    elif len(args) == 2:
        project = args[1]
    else:
        cmdline.print_version()
        cmdline.print_usage()
        if len(available_platforms) == 0:
            sys.stdout.write('No targets are installed.\nSee the whole list with `crossroad --list-targets`.\n')
        else:
            sys.stdout.write(platform_list)
            if len(other_platforms) > 0:
                sys.stdout.write('\nSome targets are not installed.\nSee the whole list with `crossroad --list-targets`.\n')
        sys.exit(os.EX_USAGE)

    target = args[0]
    shell = None
    environ = os.environ
    try:
        # NOTE: $SHELL is usually the default shell of the user,
        # not necessarilly the current shell. $0 would return the
        # current shell. But is it really what we want?
        shell = os.environ['SHELL']
    except KeyError:
        shell = None

    environ['CROSSROAD_PROJECT'] = project
    # Do we have a script to run?
    if options.script is not None:
        if not os.path.isfile(options.script):
            sys.stderr.write('The script "{}" does not exist.\n'.format(options.script))
            sys.exit(os.EX_NOINPUT)
        environ['CROSSROAD_SCRIPT'] = os.path.abspath(options.script)
        if not options.no_exit:
            environ['CROSSROAD_SCRIPT_EXIT'] = 'yes'
    elif options.no_exit:
        sys.stderr.write('The --no-exit-after-run option is meaningless without --script being set. Exiting.\n')
        sys.exit(os.EX_NOINPUT)

    if shell is None or (shell[-4:] != 'bash' and shell[-3:] != 'zsh'):
        sys.stderr.write("Warning: sorry, only bash and zsh are supported right now (detected by $SHELL environment variable).\n")
        shell = shutil.which('bash')
        if shell is None:
            shell = shutil.which('zsh')
        if shell is None:
            sys.stderr.write(" Neither bash nor zsh were found in your path.\n")
            sys.exit(os.EX_UNAVAILABLE)
        sys.stderr.write(" Defaulting to {}.\n".format(shell))
        sys.stderr.flush()

    if shell[-4:] == 'bash':
        # I could set an updated environment. But bash would still run .bashrc
        # which may overwrite some variables. So instead I set my own bashrc,
        # where I make sure to first run the user rc files.
        bashrc_path = os.path.join(install_datadir, 'crossroad/scripts/shells/bash/bashrc.' + available_platforms[target].name)
        command = [shell, '--rcfile', bashrc_path]
    elif shell[-3:] == 'zsh':
        zdotdir = os.path.join(install_datadir, 'crossroad/scripts/shells/zsh.' + available_platforms[target].name)
        # SETUP the $ZDOTDIR env.
        # If already set, save the old value and set it back at the end.
        # I could not find a way in zsh to run another zshrc and still end up in an interactive shell.
        # The option -i + a file lets think it will do so, but the shell still ends up immediately
        # after the file ran. Modifying the $ZDOTDIR env is the only good way.
        # I don't forget also to run the original .zshenv and .zshrc.
        command = [shell]
        if 'ZDOTDIR' in environ:
            environ['CROSSROAD_OLD_ZDOTDIR'] = environ['ZDOTDIR']
        environ['ZDOTDIR'] = zdotdir
    else:
        # We ensured that a shell is found, or we already exited. This should never be executed.
        sys.stderr.write("Unexpected error. Please contact the developer.\n")
        sys.exit(os.EX_SOFTWARE)

    env_path = os.path.join(xdg_data_home, 'crossroad/roads', available_platforms[target].name, project)
    if not os.path.exists(env_path):
        try:
            sys.stdout.write('Creating project "{}" for target {}...'.format(project, available_platforms[target].name))
            # Is this new project a copy of an existing project?
            if options.copy:
                sys.stdout.write(' as copy of {}.\n'.format(options.copy))
                copy_path = os.path.join(xdg_data_home, 'crossroad/roads', available_platforms[target].name, options.copy)
                if not os.path.exists(copy_path) or not os.access(copy_path, os.R_OK):
                    sys.stderr.write('"{}" does not exist for {}, or it is unreadable.\n'.format(options.copy, available_platforms[target].name))
                    sys.exit(os.EX_CANTCREAT)
                copy_file(copy_path, env_path, copy_path, env_path)
            else:
                sys.stdout.write('\n')
                os.makedirs(env_path, exist_ok = True)
        except PermissionError:
            sys.stderr.write('"{}" cannot be created. Please verify your permissions. Aborting.\n'.format(env_path))
            sys.exit(os.EX_CANTCREAT)
        except NotADirectoryError:
            sys.stderr.write('"{}" exists but is not a directory. Aborting.\n'.format(env_path))
            sys.exit(os.EX_CANTCREAT)
        except shutil.Error:
            sys.stderr.write('{} could not be copied to {}. Please verify your permissions. Aborting.\n'.format(copy_path, env_path))
            sys.exit(os.EX_CANTCREAT)

        # Do not run the target's prepare() script after a copy (which we assume already prepared).
        if not options.copy and not available_platforms[target].prepare(env_path):
            sys.stderr.write('Crossroad failed to prepare the environment for "{}".\n{}'.format(available_platforms[target].name))
            sys.exit(os.EX_CANTCREAT)
    elif options.copy is not None:
        sys.stderr.write('Option --copy cannot be used for existing projects\n')
        sys.exit(os.EX_USAGE)

    environ['CROSSROAD_PREFIX'] = os.path.abspath(env_path)

    print('\033[1;35mYou are now at the crossroads...\033[0m\n')
    shell_proc = subprocess.Popen(command, shell = False, env = environ,
                                  bufsize = 0)
    shell_proc.wait()
    print('\033[1;35mYou can run, you can run.\nTell your friend boy Greg T.\nthat you were standing at the crossroads.')
    print('I believe you were sinking down.\033[0m\n')
    sys.exit(os.EX_OK)

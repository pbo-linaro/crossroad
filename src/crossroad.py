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

### Current Crossroad Environment ###

crossroad_road = None
try:
    crossroad_road = os.environ['CROSSROAD_ROAD']
except KeyError:
    pass

# Redirect to the in-crossroad binary.
if crossroad_road is not None:
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

(available_platforms, other_platforms) = load_platforms()

### Start the Program ###

version = '0.4'
maintainer = '<jehan at girinstud.io>'

usage  = 'Usage: crossroad [<TARGET>] [--help] [--version] [--list-all] [--reset <TARGET 1> [<TARGET 2>...]]\n'
usage += '                 [--symlink <TARGET> [<link-name>]] [--compress <archive.zip> <TARGET 1> [<TARGET 2>...]]'

platform_list = "Available targets:\n"
for name in available_platforms:
    platform = available_platforms[name]
    platform_list += "{:<20} {}\n".format(platform.name, platform.short_description.strip())

unavailable_platform_list = '\nUninstalled targets:\n'
for name in other_platforms:
    platform = other_platforms[name]
    unavailable_platform_list += "{:<20} {}\n".format(platform.name, platform.short_description.strip())

cmdline = optparse.OptionParser(usage,
        version="%prog, version " + version,
        description = "Set a cross-compilation environment for the target platform TARGET",
        conflict_handler="resolve")
cmdline.add_option('-l', '--list-all',
    help = 'list all known platforms',
    action = 'store_true', dest = 'list_all', default = False)
cmdline.add_option('-h', '--help',
    help = 'show this help message and exit. If a TARGET is provided, show information about this platform.',
    action = 'store_true', dest = 'help', default = False)
# TODO: do the same for --host?
cmdline.add_option('-p', '--prefix',
    help = 'outputs the prefix of the named platform.',
    action = 'store', type="string", dest = 'prefix', default = False)
cmdline.add_option('-c', '--compress',
    help = 'compress an archive (zip only), with the given name, of the named platforms.',
    action = 'store', type="string", dest = 'archive', default = None)
cmdline.add_option('-s', '--symlink',
    help = 'create a symbolic link of the named platform.',
    action = 'store_true', dest = 'symlink', default = False)
cmdline.add_option('--reset',
    help = "effectively delete TARGET's tree. Don't do this if you have important data saved in there.",
    action = 'store_true', dest = 'reset', default = False)

(options, args) = cmdline.parse_args()

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
        sys.exit(os.EX_OK)
            
    if options.list_all:
        cmdline.print_version()
        sys.stdout.write(platform_list)
        if len(other_platforms) > 0:
            sys.stdout.write(unavailable_platform_list)
        sys.exit(os.EX_OK)

    if options.prefix:
        platform_name = options.prefix
        if platform_name not in available_platforms:
            sys.stderr.write('Not a valid platform: {}\n'.format(platform_name))
            sys.exit(os.EX_USAGE)

        prefix = os.path.join(xdg_data_home, 'crossroad/roads', platform_name)
        sys.stdout.write(prefix)
        sys.exit(os.EX_OK)

    if options.reset:
        if len(args) == 0:
            sys.stderr.write('You must specify at least one platform name for --reset.\n')
            sys.exit(os.EX_USAGE)

        for platform_name in args:
            if platform_name not in available_platforms:
                sys.stderr.write('Not a valid platform: {}\n'.format(platform_name))
                continue
            platform_path = os.path.join(xdg_data_home, 'crossroad/roads', platform_name)
            # XXX Or a --force option?
            sys.stdout.write('Platform {} ({}) is going to be deleted in'.format(platform_name, platform_path))
            for i in range(5, 0, -1):
                sys.stdout.write(' {}'.format(i))
                sys.stdout.flush()
                time.sleep(1)
            sys.stdout.write('...\nDeleting {}...\n'.format(platform_path))
            try:
                shutil.rmtree(platform_path)
            except:
                sys.stderr.write('Warning: deletion of {} failed with {}\n'.format(platform_path, sys.exc_info()[0]))
        sys.exit(os.EX_OK)

    if options.archive is not None:
        if options.archive[-4:].lower() != '.zip':
            # XXX may support other format in the future, so I could use a generic naming.
            # But in same time, zip seems the most prominent on Windows platform, so for transfer,
            # I support only this for now.
            sys.stderr.write('Error: sorry, only zip format archives are supported for the time being.\n')
            sys.exit(os.EX_UNAVAILABLE)
        if crossroad_road:
            platforms = [crossroad_road]
        else:
            platforms = args
        if len(platforms) == 0:
            sys.stderr.write('You must name at least one platform to include in your archive.\n')
            sys.exit(os.EX_USAGE)
        for platform in platforms:
            # Test existence and readability of the platform.
            platform_path = os.path.join(xdg_data_home, 'crossroad/roads', platform)
            if platform not in available_platforms or not os.access(platform_path, os.R_OK):
                sys.stderr.write('Platform {} is not built, or unreadable.\n'.format(platform))
                sys.exit(os.EX_NOPERM)
        # All looks good. Create the zip!
        sys.stdout.write('Generating an archive file...\n')
        archive_file = zipfile.ZipFile(options.archive, 'w',
                                     compression = zipfile.ZIP_DEFLATED,
                                     allowZip64 = True)
        # XXX the last slash / is important because we will want to remove it from file archive name.
        archive_root = os.path.join(xdg_data_home, 'crossroad/roads/')
        for platform in platforms:
            platform_path = os.path.join(archive_root, platform)
            # XXX should we followlinks=True to walk into directory links?
            for dirpath, dirnames, filenames in os.walk(platform_path):
              for filename in filenames:
                file_path = os.path.join(dirpath, filename)
                archive_file.write(file_path,
                                   arcname = file_path.replace(archive_root, ''))
        sys.stdout.write('Archive file {} completed.\n'.format(options.archive))
        archive_file.close()
        sys.exit(os.EX_OK)

    if options.symlink:
        if len(args) != 1 and len(args) != 2:
            sys.stderr.write('You must specify the platform to symlink, optionally followed by the link name.\n')
            sys.exit(os.EX_USAGE)
        platform = args[0]
        link_name = platform
        if len(args) == 2:
            link_name = args[1]
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
        platform_path = os.path.join(xdg_data_home, 'crossroad/roads', platform)
        print(platform_path)
        if platform not in available_platforms or not os.access(platform_path, os.R_OK):
            sys.stderr.write('Platform {} is not built, or unreadable.\n'.format(platform))
            sys.exit(os.EX_NOPERM)
        os.symlink(platform_path, link_name, target_is_directory=True)
        sys.exit(os.EX_OK)

    # If we are here, it means we want to enter a crossroad environment.
    if len(args) != 1:
        cmdline.print_version()
        cmdline.print_usage()
        sys.stdout.write(platform_list)
        sys.exit(os.EX_USAGE)

    if args[0] in available_platforms:
        # TODO: support more shells.
        try:
            shell = os.environ['SHELL']
        except KeyError:
            sys.stderr.write("No shell detected. Fallbacking to bash.")
            shell = 'bash'

        bashrc_path = os.path.join(install_datadir, 'crossroad/environments/bashrc.' + available_platforms[args[0]].name)
        if shell[-4:] == 'bash':
            # I could set an updated environment. But bash would still run .bashrc
            # which may overwrite some variables. So instead I set my own bashrc.
            command = [shell, '--rcfile', bashrc_path]
        else:
            command = ['bash', '--rcfile', bashrc_path]
            sys.stderr.write("Warning: sorry, only bash is supported right now.")

        env_path = os.path.join(xdg_data_home, 'crossroad/roads', available_platforms[args[0]].name)
        try:
            os.makedirs(env_path, exist_ok = True)
        except PermissionError:
            sys.stderr.write('"{}" cannot be created. Please verify your permissions. Aborting.\n'.format(env_path))
            sys.exit(os.EX_CANTCREAT)
        except NotADirectoryError:
            sys.stderr.write('"{}" exists but is not a directory. Aborting.\n'.format(env_path))
            sys.exit(os.EX_CANTCREAT)

        print('\033[1;35mYou are now at the crossroads...\033[0m\n')
        shell_proc = subprocess.Popen(command, shell=False)
        shell_proc.wait()
        print('\033[1;35mYou can run, you can run.\nTell your friend boy Greg T.\nthat you were standing at the crossroads.')
        print('I believe you were sinking down.\033[0m\n')
        sys.exit(os.EX_OK)
    elif args[0] in other_platforms:
        sys.stderr.write('"{}" is not available. Some requirements are missing:\n{}'.format(args[0], other_platforms[args[0]].requires()))
        sys.exit(os.EX_UNAVAILABLE)
    else:
        sys.stderr.write('"{}" is not a platform known by `crossroad`. Do not hesitate to contribute: {}\n'.format(args[0], maintainer))
        sys.exit(os.EX_UNAVAILABLE)

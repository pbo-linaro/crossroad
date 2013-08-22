#!/usr/bin/python3
# -*- coding: utf-8 -*-
# This file is part of crossroad.
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

### Current Crossroad Environment ###

### Check all available platforms. ###
crossroad_road = None
try:
    crossroad_road = os.environ['CROSSROAD_ROAD']
except KeyError:
    pass

# This string will be replaced by the setup.py at installation time,
# depending on where you installed default data.
install_datadir = os.path.abspath('@DATADIR@')
install_datadir = os.path.abspath('../..')

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
        #sys.path.insert(0, dir)
        #sys.path.pop(0)
        loader = importlib.machinery.SourceFileLoader(module, platform_file)
        try:
            platform = loader.load_module(module)
        except ImportError:
            continue
        except FileNotFoundError:
            #sys.stderr.write ("Module not found: %s\n", platform.path)
            continue
        #except SyntaxError as err:
            #sys.stderr.write ("Syntax error in module %s:%s\n", platform.name, err.text)
        #    continue
        try:
            # TODO: test other mandatory attributes?
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

version = '0.3'
maintainer = '<jehan at girinstud.io>'

usage = 'Usage: %prog [TARGET] [--help] [--version] [--list-all]'

platform_list = "Available platforms:\n"
for name in available_platforms:
    platform = available_platforms[name]
    platform_list += "{:<20} {}\n".format(platform.name, platform.short_description.strip())

unavailable_platform_list = '\nUninstalled platforms:\n'
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
    help = 'show this help message and exit',
    action = 'store_true', dest = 'help', default = False)
if crossroad_road is not None:
    cmdline.add_option('-i', '--install',
        help = 'install a dependency',
        action = 'store_true', dest = 'install', default = False)

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
            
    if crossroad_road is not None and options.install and crossroad_road in available_platforms:
        sys.exit(available_platforms[crossroad_road].install(args))

    if options.list_all:
        cmdline.print_version()
        sys.stdout.write(platform_list)
        if len(other_platforms) > 0:
            sys.stdout.write(unavailable_platform_list)
        sys.exit(os.EX_OK)

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
            sys.stderr.write("Sorry, only bash is supported right now.")

        env_path = os.path.join(xdg_data_home, 'crossroad/roads', available_platforms[args[0]].name)
        try:
            os.chdir(env_path)
        except FileNotFoundError:
            try:
                os.makedirs(env_path)
            except PermissionError:
                sys.stderr.write('"{}" cannot be created. Please verify your permissions. Aborting.\n'.format(env_path))
                sys.exit(os.EX_CANTCREAT)
            os.chdir(env_path)
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

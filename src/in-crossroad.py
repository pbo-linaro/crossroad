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
import subprocess
import inspect
import os.path
import sys
import re

### Current Crossroad Environment ###
crossroad_road = None
try:
    crossroad_road = os.environ['CROSSROAD_ROAD']
except KeyError:
    sys.stderr.write('Error: no Crossroad environment found. Contact the developers.')
    sys.exit(os.EX_DATAERR)

### Check all available platforms. ###

# This string will be replaced by the setup.py at installation time,
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

def load_platform(platform_name):
    '''
    All platforms are available in {datadir}/crossroads/platforms/.
    '''
    datadirs = get_datadirs()
    platform_file = None
    for dir in datadirs:
        # XXX: rename win64.py in w64.py OR load each and check name?
        f = os.path.abspath(os.path.join (dir, 'crossroad/platforms', platform_name + '.py'))
        if os.path.exists(f):
            platform_file = f
            break
    if platform_file is None:
        return None
    # It is supposed to be a python script. Let's try and import it.
    loader = importlib.machinery.SourceFileLoader(platform_name, platform_file)
    try:
        platform = loader.load_module(platform_name)
    except (ImportError, FileNotFoundError):
        return None
    try:
        if not platform.is_available():
            return None
    except AttributeError:
        # not a valid platform.
        return None
    return platform

platform = load_platform(crossroad_road)
if platform is None:
    sys.stderr.write('Error: the current crossroad environment does not seem to exist. Contact the developers.')
    sys.exit(os.EX_DATAERR)

commands = [command[10:] for command in dir(platform) if command[:10] == 'crossroad_' and callable(getattr(platform, command))]

program = 'crossroad'
version = '0.4'
maintainer = 'jehan at girinstud.io'

usage = 'Usage: {} [--help] [--version] <command> [<args>]'.format(program)

if __name__ == "__main__":
    #(options, args) = cmdline.parse_args()
    if len(sys.argv) < 2:
        sys.stdout.write('{} version {} <{}>'.format(program, version, maintainer))
        sys.stdout.write(usage)
        sys.exit(os.EX_USAGE)
    command = None
    command_name = None
    command_args = []
    command_kwargs = {}
    usage_error = False
    show_help = False
    for arg in sys.argv[1:]:
        if command is not None:
            if arg[:2] == '--':
                # TODO: support not boolean options too.
                command_fun = getattr(platform, 'crossroad_' + command)
                (args, varargs, varkw, defaults, kwonlyargs, kwonlydefaults, annotations) = inspect.getfullargspec(command_fun)
                command_kwarg = arg[2:].replace('-', '_')
                if command_kwarg not in kwonlyargs:
                    command_usage = '{} {}'.format(program, command_name)
                    for positional_arg in args:
                        command_usage += ' <{}>'.format(positional_arg)
                    if varargs is not None:
                        command_usage += ' <{}...>'.format(varargs)
                    for option in kwonlyargs:
                        command_usage += ' [--{}]'.format(option)
                    if command_fun.__doc__ is not None:
                        command_usage += '\n{}\n'.format(command_fun.__doc__)
                    else:
                        command_usage += '\n'
                    sys.stderr.write(command_usage)
                    sys.exit(os.EX_USAGE)
                command_kwargs[command_kwarg] = True
            else:
                command_args.append(arg)
            continue
        elif show_help:
            if arg in commands:
                command_fun = getattr(platform, 'crossroad_' + arg)
                (args, varargs, varkw, defaults, kwonlyargs, kwonlydefaults, annotations) = inspect.getfullargspec(command_fun)
                command_usage = '{} {}'.format(program, arg)
                for positional_arg in args:
                    command_usage += ' <{}>'.format(positional_arg)
                    #if positional_arg in annotations and annotations[positional_arg] == list:
                    #    command_usage += '...'
                    #command_usage += '>'
                if varargs is not None:
                    command_usage += ' <{}...>'.format(varargs)
                for option in kwonlyargs:
                    command_usage += ' [--{}]'.format(option)
                if command_fun.__doc__ is not None:
                    command_usage += '\n{}\n'.format(command_fun.__doc__)
                else:
                    command_usage += '\n'
                sys.stdout.write(command_usage)
                sys.exit(os.EX_OK)
            else:
                sys.stderr.write('Unknown option for the "help" command: {}'.format(arg))
                sys.exit(os.EX_USAGE)
        elif arg == '-v' or arg == '--version' or arg == 'version':
            sys.stdout.write('{} version {} <{}>\n'.format(program, version, maintainer))
            sys.exit(os.EX_OK)
        elif arg == '-h' or arg == '--help' or arg == 'help':
            show_help = True
            continue
        elif arg == 'prefix':
            prefix = os.path.join(xdg_data_home, 'crossroad/roads', crossroad_road)
            sys.stdout.write(prefix)
            sys.exit(os.EX_OK)
        elif arg == 'configure':
            if not os.path.exists('configure') and os.path.exists('autogen.sh'):
                sys.stderr.write('Warning: there is no ./configure script in the current directory, but there is an autogen.sh. Running it first.\n')
                # NOTE: some project would configure their autogen.sh to actually run ./configure
                # To be on the safe side, I would add the prefix/host/build info there.
                command = './autogen.sh --prefix=$CROSSROAD_PREFIX --host=$CROSSROAD_HOST --build=$CROSSROAD_BUILD'
                sys.stdout.write('crossroad info: running "{}"\n'.format(command))
                subprocess.call(command, shell=True)
            if not os.path.exists('configure'):
                sys.stderr.write('There is no ./configure script in the current directory.\n')
                sys.exit(os.EX_USAGE)
            # The position should normally be 2 since any other command or option before
            # would be an error. But just in case the logics evolve.
            arg_pos = sys.argv.index(arg)
            # NOTE: with shell=True, subprocess does not deal well with list as a command.
            command = './configure --prefix=$CROSSROAD_PREFIX --host=$CROSSROAD_HOST --build=$CROSSROAD_BUILD ' + ' '.join(sys.argv[arg_pos + 1:])
            sys.stdout.write('crossroad info: running "{}"\n'.format(command))
            sys.exit(subprocess.call(command, shell=True))
        elif arg == 'cmake' or arg == 'ccmake':
            # The position should normally be 2 since any other command or option before
            # would be an error. But just in case the logics evolve.
            arg_pos = sys.argv.index(arg)
            command = '{} -DCMAKE_INSTALL_PREFIX:PATH=$CROSSROAD_PREFIX -DCMAKE_TOOLCHAIN_FILE=$CROSSROAD_CMAKE_TOOLCHAIN_FILE '.format(arg)
            command += ' '.join(sys.argv[arg_pos + 1:])
            sys.stdout.write('crossroad info: running "{}"\n'.format(command))
            sys.exit(subprocess.call(command, shell=True))
        elif arg[:1] == '-':
            sys.stderr.write('Unknown option: {}\n{}\n'.format(arg, usage))
            sys.exit(os.EX_USAGE)
        elif arg.replace('-', '_') in commands:
            command = arg.replace('-', '_')
            command_name = arg
            continue
        else:
            sys.stderr.write('Unknown command: {}\n'.format(arg))
            show_help = True
            usage_error = True
            break

    if show_help:
        command_list = usage
        command_list += '\n\nAny crossroad environment provides the following commands:'
        command_list += '\n{:<20} {}'.format('configure', 'Run `./configure` in the following directory for your cross-compilation environment.')
        command_list += '\n{:<20} {}'.format('cmake', 'Run cmake for your cross-compilation environment.')
        command_list += '\n{:<20} {}'.format('ccmake', 'Run ccmake for your cross-compilation environment.')
        command_list += '\n{:<20} {}'.format('prefix', 'Return the installation prefix.')
        command_list += "\n\nCrossroad's {} environment proposes the following commands:".format(crossroad_road)
        for command in commands:
            command_fun = getattr(platform, 'crossroad_' + command)
            (args, varargs, varkw, defaults, kwonlyargs, kwonlydefaults, annotations) = inspect.getfullargspec(command_fun)
            if command_fun.__doc__ is not None:
                # shortdesc is the first line of the whole command description.
                shortdesc = command_fun.__doc__.strip()
                shortdesc = re.sub(r'\n.*', '', shortdesc)
                command_list += '\n{:<20} {}'.format(command, shortdesc)
            else:
                command_list += '\n{}'.format(command)
        command_list += '\n\nSee `crossroad help <command>` for more information on a specific command.\n'
        sys.stdout.write(command_list)
        if usage_error:
            sys.exit(os.EX_USAGE)
        else:
            sys.exit(os.EX_OK)

    if command is None:
        sys.stdout.write('{} version {} <{}>'.format(program, version, maintainer))
        sys.stdout.write(usage)
        sys.exit(os.EX_USAGE)
    else:
        command_fun = getattr(platform, 'crossroad_' + command)
        (args, varargs, varkw, defaults, kwonlyargs, kwonlydefaults, annotations) = inspect.getfullargspec(command_fun)
        command_fun(*command_args, **command_kwargs)
        sys.exit(os.EX_OK)


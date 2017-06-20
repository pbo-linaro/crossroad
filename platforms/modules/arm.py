#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# This file is part of crossroad.
# Copyright (C) 2014 Jehan <jehan at girinstud.io>
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

'''
Setups a cross-compilation environment for ARM.
'''

# Require python 3.3 for shutil.which
import shutil
import subprocess
import glob
import os.path
import sys

name = 'arm'

# see gcc-i686-linux-android for Android on x86
# Also android-google-arm and android-google-x86 for using Google binaries.

short_description = 'Generic Embedded ABI on ARM'

# android-src-vendor ?
# android-headers ?
mandatory_binaries = {
    'arm-none-eabi-ld': 'gcc-arm-none-eabi',
    }
# arm-none-eabi-newlib must be installed for crt0.o.
# for other: glibc-arm-linux-gnu(-devel).

# Maybe I should have options for -specs, -march, etc.
# https://launchpadlibrarian.net/170926122/readme.txt
# http://stackoverflow.com/questions/19419782/exit-c-text0x18-undefined-reference-to-exit-when-using-arm-none-eabi-gcc
# TODO: add --specs=nosys.specs  to gcc.

languages = {
    'C' : {'arm-none-eabi-gcc': 'gcc-arm-none-eabi'},
    'C++' : {'arm-none-eabi-g++': 'gcc-arm-none-eabi'}
    }

def is_available():
    '''
    Is it possible on this computer?
    '''
    for bin in mandatory_binaries:
        if shutil.which(bin) is None:
            return False
    return True

def requires():
    '''
    Output on standard output necessary packages and what is missing on
    the current installation.
    '''
    requirements = ''
    for bin in mandatory_binaries:
        requirements += '- {} [package "{}"]'.format(bin, mandatory_binaries[bin])
        if shutil.which(bin) is None:
            requirements += " (missing)\n"
        else:
            requirements += " (ok)\n"
    return requirements

def language_list():
    '''
    Return a couple of (installed, uninstalled) language lists.
    '''
    uninstalled_languages = {}
    installed_languages = []
    for name in languages:
        for bin in languages[name]:
            if shutil.which(bin) is None:
                # List of packages to install.
                uninstalled_languages[name] = [languages[name][f] for f in languages[name]]
                # Removing duplicate packages.
                uninstalled_languages[name] = list(set(uninstalled_languages[name]))
                break
        else:
            installed_languages.append(name)
    return (installed_languages, uninstalled_languages)

def prepare(prefix):
    '''
    Prepare the environment.
    Note that copying these libs is unnecessary for building, since the
    system can find these at build time. But when moving the prefix to a
    Windows machine, if ever we linked against these dll and they are
    absent, the executable won't run.
    '''
    try:
        env_bin = os.path.join(prefix, 'bin')
        os.makedirs(env_bin, exist_ok = True)
    except PermissionError:
        sys.stderr.write('"{}" cannot be created. Please verify your permissions. Aborting.\n'.format(env_path))
        return False
    gcc_libs = subprocess.check_output(['arm-none-eabi-gcc', '-print-file-name='], universal_newlines=True)
    # XXX: do we have to do something similar to Win crossbuild by symlinking some libraries?
    #for dll in glob.glob(gcc_libs.strip() + '/*.dll'):
        #try:
            #os.symlink(dll, os.path.join(os.path.join(env_bin, os.path.basename(dll))))
        #except OSError:
            # A failed symlink is not necessarily a no-go. Let's just output a warning.
            #sys.stderr.write('Warning: crossroad failed to symlink {} in {}.\n'.format(dll, env_bin))
    return True

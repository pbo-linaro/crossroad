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
Setups a cross-compilation environment for Android on ARM.
'''

# Require python 3.3 for shutil.which
import shutil
import subprocess
import glob
import os.path
import platform
import re
import sys

name = 'android-arm'

# see gcc-i686-linux-android for Android on x86
# Also android-google-arm and android-google-x86 for using Google binaries.

short_description = 'Generic Android/Bionic on ARM'

# android-src-vendor ?
# android-headers ?
mandatory_binaries = {
    }

languages = {
    'C' : {'arm-linux-androideabi-gcc': 'gcc-arm-linux-androideabi'},
    'C++' : {'arm-linux-androideabi-g++': 'gcc-arm-linux-androideabi'}
    }

def is_available():
    '''
    Is it possible on this computer?
    '''
    return platform.processor() == 'x86_64'

def requires():
    '''
    Output on standard output necessary packages and what is missing on
    the current installation.
    '''
    requirements = ''
    if platform.processor() != 'x86_64':
        requirements = 'Android NDK is only available for Linux 64-bit\n'
    return requirements

def language_list():
    '''
    Return a couple of (installed, uninstalled) language lists.
    '''
    uninstalled_languages = {}
    installed_languages = []
    if is_available():
        installed_languages = ['C', 'C++']
    else:
        uninstalled_languages = languages
    return (installed_languages, uninstalled_languages)

def prepare(prefix):
    '''
    Prepare the environment.
    '''
    try:
        env_bin = os.path.join(prefix, 'bin')
        os.makedirs(env_bin, exist_ok = True)
    except PermissionError:
        sys.stderr.write('"{}" cannot be created. Please verify your permissions. Aborting.\n'.format(env_path))
        return False
    return True

def crossroad_finalize():
    '''
    Clean-out installed pkg-config files so that they output appropriate
    build paths, and not the finale installation paths.
    '''
    prefix = os.path.abspath(os.environ['CROSSROAD_PREFIX'])
    for root, dirs, files in os.walk(prefix):
        if os.path.basename(root) == 'pkgconfig':
            for file in {f for f in files if f.endswith('.pc')}:
                file = os.path.join(root, file)
                try:
                    fd = open(file, 'r')
                    contents = fd.read()
                    fd.close()
                    if re.match(r'^prefix={}'.format(prefix), contents):
                        continue
                    contents = re.sub(r'^prefix=', 'prefix={}'.format(prefix),
                                      contents, count=0, flags=re.MULTILINE)
                except IOError:
                    sys.stderr.write('File "{}" could not be read.\n'.format(from_file))
                    sys.exit(os.EX_CANTCREAT)
                try:
                    fd = open(file, 'w')
                    fd.write(contents)
                    fd.close()
                except IOError:
                    sys.stderr.write('File {} cannot be written.'.format(to_file))
                    sys.exit(os.EX_CANTCREAT)

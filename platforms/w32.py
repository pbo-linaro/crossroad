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

'''
Setups a cross-compilation environment for Microsoft Windows operating systems (32-bit).
'''

# Require python 3.3 for shutil.which
import shutil
import subprocess
import os
import sys

install_datadir = os.path.join(os.path.abspath('@DATADIR@'), 'share')

name = 'w32'

short_description = 'Windows 32-bit'

mandatory_binaries = {
    'i686-w64-mingw32-gcc': 'gcc-mingw-w64-i686',
    'i686-w64-mingw32-ld': 'binutils-mingw-w64-i686'
    }

languages = {
    'C' : {'i686-w64-mingw32-gcc': 'gcc-mingw-w64-i686'},
    'C++': {'i686-w64-mingw32-c++': 'g++-mingw-w64-i686'},
    'Ada': {'i686-w64-mingw32-gnat': 'gnat-mingw-w64-i686'},
    'OCaml': {'i686-w64-mingw32-ocamlc': 'mingw-ocaml'},
    'fortran': {'i686-w64-mingw32-gfortran': 'gfortran-mingw-w64-i686'},
    'Objective C' : {'i686-w64-mingw32-gobjc': 'gobjc-mingw-w64-i686'},
    'Objective C' : {'i686-w64-mingw32-gobjc++': 'gobjc++-mingw-w64-i686'}
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
            requirements += "\n"
    return requirements

def language_list():
    '''
    Return a couple of (installed, uninstalled) language list.
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

def prepare():
    pass

def crossroad_install(*packages:list, src:bool = False):
    '''
    Install the list of packages and all their dependencies.
    If --src is provided, it installs the source packages, and not the main packages.
    '''
    command = [os.path.join(install_datadir, 'crossroad/scripts/crossroad-mingw-install.py'),
               '-r', 'openSUSE_12.1', '-p', 'windows:mingw:win32', '--deps']
    if src:
        command += ['--src']
    command += list(packages)
    subprocess.call(command, shell=False)

def crossroad_list_files(*packages, src:bool = False):
    '''
    List files provided by packages.
    '''
    command = [os.path.join(install_datadir, 'crossroad/scripts/crossroad-mingw-install.py'),
               '-r', 'openSUSE_12.1', '-p', 'windows:mingw:win32', '--list-files']
    if src:
        command += ['--src']
    command += packages
    subprocess.call(command, shell=False)

def crossroad_info(*packages, src:bool = False):
    '''
    Display package details.
    '''
    command = [os.path.join(install_datadir, 'crossroad/scripts/crossroad-mingw-install.py'),
               '-r', 'openSUSE_12.1', '-p', 'windows:mingw:win32', '--info']
    if src:
        command += ['--src']
    command += list(packages)
    subprocess.call(command, shell=False)

def crossroad_uninstall(*packages, src:bool = False):
    '''
    Uninstall packages.
    '''
    command = [os.path.join(install_datadir, 'crossroad/scripts/crossroad-mingw-install.py'),
               '-r', 'openSUSE_12.1', '-p', 'windows:mingw:win32', '--uninstall']
    if src:
        command += ['--src']
    command += list(packages)
    subprocess.call(command, shell=False)


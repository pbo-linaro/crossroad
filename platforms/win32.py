#!/usr/bin/python
# -*- coding: utf-8 -*-

'''
Setups a cross-compilation environment for Microsoft Windows operating systems (32-bit).
'''

# Require python 3.3 for shutil.which
import shutil
import subprocess
import os
import sys

install_datadir = os.path.abspath('@DATADIR@')

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

def install(pkgs, src_pkg):
    '''
    Installing dependencies, etc.
    '''
    command = [os.path.join(install_datadir, 'crossroad/scripts/crossroad-mingw-install.py'),
               '-r', 'openSUSE_12.1', '-p', 'windows:mingw:win32', '--deps']
    if src_pkg:
        command += ['--src']
    command += pkgs
    inst_proc = subprocess.Popen(command, shell=False)
    return inst_proc.wait()

def list_files(pkgs, src_pkg):
    '''
    List package files, etc.
    '''
    command = [os.path.join(install_datadir, 'crossroad/scripts/crossroad-mingw-install.py'),
               '-r', 'openSUSE_12.1', '-p', 'windows:mingw:win32', '--list-files']
    if src_pkg:
        command += ['--src']
    command += pkgs
    output = subprocess.check_output(command, shell=False)
    sys.stdout.write(output.decode('UTF-8'))


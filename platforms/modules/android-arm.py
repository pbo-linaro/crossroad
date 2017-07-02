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
import hashlib
import glob
import os.path
import math
import platform
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import urllib.request
import zipfile

name = 'android-arm'
ndk  = 'android-ndk-r15b'

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
    pass

def download_progress(chunk, max, total):
    # TODO: I will want to have this work by deleting first previous
    # contents on the shell.
    #digits = math.floor(math.log10(total)) + 1
    #sys.stdout.write("{:{width}}/{}\n".format (chunk, total, width=digits))
    if chunk%(total/10) == 0.0:
        sys.stdout.write(".")
        sys.stdout.flush()

def init(environ):
    # The toolchain is installed in the cache directory.
    xdg_cache_home = None
    try:
        xdg_cache_home = os.environ['XDG_CACHE_HOME']
    except KeyError:
        home_dir = os.path.expanduser('~')
        if home_dir != '~':
            xdg_cache_home = os.path.join(home_dir, '.cache')
        else:
            sys.stderr.write('$XDG_CACHE_HOME not set, and this user has no $HOME either.\n')
            sys.exit(os.EX_UNAVAILABLE)
    # Create the directory.
    android_dir = os.path.join(xdg_cache_home, 'crossroad', 'android')
    toolchain_dir = os.path.join(android_dir, 'toolchain')
    gen_ndk = os.path.join(toolchain_dir, 'android-24-arm')
    bin_dir = os.path.join(gen_ndk, 'bin')
    ndk_tmp = tempfile.mkdtemp(prefix='crossroad-')
    try:
        os.makedirs(toolchain_dir)
    except OSError:
        pass
    # Check if we need to install.
    install = False
    for name in languages:
        for bin in languages[name]:
            bin_path = os.path.join(bin_dir, bin)
            if not os.path.exists(bin_path) and \
               shutil.which(bin) is None:
                install = True
                break
        if install:
            break
    if install:
        yn = input('Crossroad will now install Android toolchain [yN] ')
        yn = yn.strip().lower()
        if yn != 'y':
            sys.stderr.write('Android environment initialization aborted.\n')
            sys.exit(os.EX_CANTCREAT)
        # Download the NDK.
        ndk_filename = ndk + '-linux-x86_64.zip'
        ndk_path = os.path.join(toolchain_dir, ndk_filename)
        sha1_checksum = '2690d416e54f88f7fa52d0dcb5f539056a357b3b'
        download_url = 'https://dl.google.com/android/repository/'
        if os.path.exists(ndk_path):
            # Check if the file is safe or corrupted.
            sys.stdout.write('Cached Android NDK found, testing… ')
            test = hashlib.sha1()
            with open(ndk_path, 'rb') as f:
                data = f.read(65536)
                while data:
                    test.update(data)
                    data = f.read(65536)
            if test.hexdigest() != sha1_checksum:
                sys.stdout.write('cached Android NDK corrupted, deleting it.\n')
                os.unlink (ndk_path)
            else:
                sys.stdout.write('keeping cached Android NDK.\n')
        if not os.path.exists(ndk_path):
            sys.stdout.write('Dowloading Android NDK…')
            (_, headers) = urllib.request.urlretrieve(download_url + ndk_filename,
                                                      filename=ndk_path,
                                                      reporthook=download_progress)
            # Check if the file is safe or corrupted.
            sys.stdout.write('Testing download Android NDK… ')
            test = hashlib.sha1()
            with open(ndk_path, 'rb') as f:
                data = f.read(65536)
                while data:
                    test.update(data)
                    data = f.read(65536)
            if test.hexdigest() != sha1_checksum:
                sys.stderr.write('Downloaded Android NDK corrupted, deleting it, aborting.\n')
                os.unlink (ndk_path)
                sys.exit(os.EX_DATAERR)
            else:
                sys.stdout.write('All good!\n')
        sys.stdout.write('Extracting Android NDK in {}…\n'.format(ndk_tmp))
        zip = zipfile.ZipFile(ndk_path, 'r')
        zip.extractall(path=ndk_tmp)
        zip.close()
        sys.stdout.write('Building toolchain…\n')
        # zipfile module loses permissions.
        # See: https://bugs.python.org/issue15795
        os.chmod(os.path.join(ndk_tmp, ndk,
                              'build/tools/make-standalone-toolchain.sh'),
                 stat.S_IXUSR|stat.S_IRUSR|stat.S_IWUSR)
        subprocess.call(['build/tools/make-standalone-toolchain.sh',
                         '--toolchain=arm-linux-androideabi',
                         '--platform=android-24',
                         '--install-dir="{}"'.format(gen_ndk)],
                         cwd=os.path.join(ndk_tmp, ndk),
                         shell=False)
        sys.stdout.write("Fixing file permissions…\n".format(ndk_tmp))
        for root, dirs, files in os.walk(bin_dir):
            # Again, since permissions were lost. Fix where needed.
            for f in files:
                os.chmod(os.path.join(root, f),
                         stat.S_IXUSR|stat.S_IRUSR|stat.S_IWUSR)
        sys.stdout.write("Deleting {}\n".format(ndk_tmp))
        shutil.rmtree(ndk_tmp)
    # Check again if it all worked well.
    install = False
    for name in languages:
        for bin in languages[name]:
            bin_path = os.path.join(bin_dir, bin)
            if not os.path.exists(bin_path) and \
               shutil.which(bin) is None:
                install = True
                sys.stderr.write('Android installation failed.\n')
                break
        if install:
            break
    environ['PATH'] = bin_dir + ':' + environ['PATH']
    return not install

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

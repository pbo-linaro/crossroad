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

name = os.path.basename(os.path.realpath(__file__))[:-3]
# Check here to update the NDK version:
# https://developer.android.com/ndk/downloads/index.html
ndk  = 'android-ndk-r15b'
# The list of valid targets are found under platforms/ in the NDK.
# Even though they go down to API 9 there (so should be installable),
# the `make_standalone_toolchain.py` script sets a min_api variable of
# 14 for 32-bit and 21 for 64-bit platforms.
valid_apis32 = ['14', '15', '16', '17', '18',
                '19', '21', '22', '23', '24', '26']
valid_apis64 = ['21', '22', '23', '24', '26']
if name in ['android-arm', 'android-mips', 'android-x86']:
    valid_apis = valid_apis32
else:
    valid_apis = valid_apis64

toolchains = {
    'android-arm'    : 'arm-linux-androideabi',
    'android-arm64'  : 'aarch64-linux-android',
    'android-mips'   : 'mipsel-linux-android',
    'android-mips64' : 'mips64el-linux-android',
    'android-x86'    : 'x86-',
    'android-x86-64' : 'x86_64-'
    }
hosts = {
    'android-arm'    : 'arm-linux-androideabi',
    'android-arm64'  : 'aarch64-linux-android',
    'android-mips'   : 'mipsel-linux-android',
    'android-mips64' : 'mips64el-linux-android',
    'android-x86'    : 'i686-linux-android',
    'android-x86-64' : 'x86_64-linux-android'
    }

# see gcc-i686-linux-android for Android on x86
# Also android-google-arm and android-google-x86 for using Google binaries.

if name[8:11] == 'x86':
    short_description = 'Generic Android/Bionic on ' + name[8:]
else:
    short_description = 'Generic Android/Bionic on ' + name[8:].upper()

# android-src-vendor ?
# android-headers ?

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
        uninstalled_languages = {
            'C' : {hosts[name] + '-gcc': 'gcc-' + toolchains[name]},
            'C++' : {hosts[name] + '-g++': 'gcc-' + toolchains[name]}
        }
    return (installed_languages, uninstalled_languages)

def prepare(prefix):
    '''
    Prepare the environment.
    '''
    return True

def download_progress(chunk, max, total):
    # TODO: I will want to have this work by deleting first previous
    # contents on the shell.
    #digits = math.floor(math.log10(total)) + 1
    #sys.stdout.write("{:{width}}/{}\n".format (chunk, total, width=digits))
    if chunk%(total/10) == 0.0:
        sys.stdout.write(".")
        sys.stdout.flush()

def init(environ, api:int = None):
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
    # Set the platform/API level.
    if api is None:
        api = input('Specify target Android API: ')
    api = api.strip()
    if api not in valid_apis:
        sys.stderr.write('API "{}" is not available. Valid Android APIs: '.format(api))
        sys.stderr.write(', '.join(valid_apis) + '\n')
        sys.exit(os.EX_UNAVAILABLE)
    # Create the directory.
    android_dir = os.path.join(xdg_cache_home, 'crossroad', 'android')
    toolchain_dir = os.path.join(android_dir, 'toolchain')
    gen_ndk = os.path.join(toolchain_dir, 'android-' + api + name[7:])
    bin_dir = os.path.join(gen_ndk, 'bin')
    ndk_tmp = tempfile.mkdtemp(prefix='crossroad-')
    try:
        os.makedirs(toolchain_dir)
    except OSError:
        pass
    # Check if we need to install.
    install = False
    bin_test = hosts[name] + '-gcc'
    bin_path = os.path.join(bin_dir, bin_test)
    if not os.path.exists(bin_path) and \
       shutil.which(bin_test) is None:
        install = True
    if install:
        yn = input('Crossroad will now install Android toolchain (nearly 1GB download) [Yn] ')
        yn = yn.strip().lower()
        if yn != 'y' and yn != '':
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
            sys.stdout.flush()
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
                         '--toolchain=' + toolchains[name],
                         '--platform=android-' + api,
                         '--install-dir="{}"'.format(gen_ndk)],
                         cwd=os.path.join(ndk_tmp, ndk),
                         shell=False)
        sys.stdout.write("Fixing file permissions…\n".format(ndk_tmp))
        for root, dirs, files in os.walk(gen_ndk):
            parents = root.split('/')
            if 'bin' in parents  or \
               'sbin' in parents or \
               'libexec' in parents:
                # Again, since permissions were lost. Fix where needed.
                # These are the directories where we expect executables.
                for f in files:
                    os.chmod(os.path.join(root, f),
                             stat.S_IXUSR|stat.S_IRUSR|stat.S_IWUSR)
            else:
                # As a special exception, make python files executables.
                # Not sure if that's needed, in the archive, some py
                # files are executables whereas others are not. Let's
                # just not be subtle and make them all so.
                for f in files:
                    if f.endswith('.py'):
                        os.chmod(os.path.join(root, f),
                                 stat.S_IXUSR|stat.S_IRUSR|stat.S_IWUSR)
        sys.stdout.write("Deleting {}\n".format(ndk_tmp))
        shutil.rmtree(ndk_tmp)
    # Check again if it all worked well.
    install = False
    if not os.path.exists(bin_path) and \
       shutil.which(bin_test) is None:
        install = True
        sys.stderr.write('Android installation failed.\n')
    else:
        environ['PATH'] = bin_dir + ':' + environ['PATH']
        environ['CROSSROAD_ANDROID_API'] = api
    return not install

def crossroad_finalize():
    '''
    Clean-out installed pkg-config and libtool files so that they output
    appropriate build paths, and not the finale installation paths.
    '''
    prefix = os.path.abspath(os.environ['CROSSROAD_PREFIX'])
    for root, dirs, files in os.walk(prefix):
        for file in {f for f in files if f.endswith('.pc') or f.endswith('.la')}:
            file = os.path.join(root, file)
            try:
                fd = open(file, 'r')
                contents = fd.read()
                fd.close()
                if file.endswith('.pc'):
                    if re.match(r'^prefix={}'.format(prefix), contents):
                        continue
                    contents = re.sub(r'^prefix=', 'prefix={}'.format(prefix),
                                      contents, count=0, flags=re.MULTILINE)
                elif file.endswith('.la'):
                    contents = re.sub(r"([' ])/usr", "\\1{}/usr".format(prefix),
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

def preconfigure():
    crossroad_finalize()

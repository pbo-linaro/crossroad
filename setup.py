#!/usr/bin/python3
# -*- coding: utf-8 -*-

import distutils.core
import distutils.command.build
import distutils.command.install
import gzip
import sys
import os
import stat
import subprocess
import shutil

version = '0.1'

class build_man(distutils.core.Command):
    '''
    Build the man page.
    '''

    description = 'build the man page'
    user_options = []

    def run(self):
        self.check_dep()
        self.create_build_tree()
        self.build()
        self.compress_man()
        self.clean()

    def initialize_options(self):
        self.cwd = None

    def finalize_options(self):
        self.cwd = os.getcwd()

    def check_dep(self):
        '''
        Check build dependencies.
        '''
        if shutil.which('rst2man') is None:
            sys.stderr.write('`rst2man` is a mandatory building dependency. You will probably find it in a `python3-docutils` package.')
            sys.exit(os.EX_CANTCREAT)

    def create_build_tree(self):
        '''
        Create a build tree.
        '''
        shutil.rmtree('build/', True)
        try:
            os.makedirs('build/man/man1')
        except os.error:
            sys.stderr.write('Build error: failure to create the build/ tree. Please check your permissions.')
            sys.exit(os.EX_CANTCREAT)

    def build(self):
        '''
        Create the manual.
        '''
        try:
            subprocess.check_call(["rst2man", "doc/crossroad.rst", "build/man/man1/crossroad.1"])
        except subprocess.CalledProcessError:
            sys.stderr.write('Build error: `rst2man` failed to build the man page.')
            sys.exit(os.EX_CANTCREAT)

    def compress_man(self):
        '''
        Compress the man.
        '''
        with open('build/man/man1/crossroad.1', 'rb') as manual:
            with gzip.open('build/man/man1/crossroad.1.gz', 'wb') as compressed:
                compressed.writelines(manual)

    def clean(self):
        os.unlink('build/man/man1/crossroad.1')

class my_build(distutils.command.build.build):
    '''
    Override the build to build the manual first.
    '''

    def run(self):
        self.run_command('man')
        distutils.command.build.build.run(self)
        #distutils.command.install.install.run(self)

    def prepare_main_script(self):
        '''
        os.makedirs('build/bin')
        '''
        pass

class my_install(distutils.command.install.install):
    '''
    Override the install to build the manual first.
    '''

    def run(self):
        #print(self.install_data) #/usr/local
        #print(self.install_scripts) #/usr/local/bin
        # Prepare the crossroad script! XXX
        distutils.command.install.install.run(self)

distutils.core.setup(
    name = 'crossroad',
    cmdclass = {'man': build_man, 'build': my_build, 'install': my_install},
    version = version,
    description = 'Cross-Compilation Environment Toolkit.',
    long_description = 'Crossroad is a developer tool to prepare your shell environment for Cross-Compilation.',
    author = 'Jehan',
    author_email = 'jehan at girinstud.io',
    url = 'http://girinstud.io',
    license = 'AGPLv3+',
    classifiers = [
        'License :: OSI Approved :: GNU Affero General Public License v3 or later (AGPLv3+)',
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 3',
    ],
    requires = [],
    scripts = ['build/bin/crossroad'],
    data_files = [('man/man1/', ['build/man/man1/crossroad.1.gz']),
        ('crossroad/scripts/', ['scripts/crossroad-mingw-install.py']),
        ('crossroad/platforms/', ['platforms']),
        ('crossroad/environments/', ['environments']),
        ('crossroad/projects/', ['projects']),
        ],
    )


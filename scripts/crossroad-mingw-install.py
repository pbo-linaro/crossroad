#!/usr/bin/env python3
#
# Copyright (C) Maarten Bosmans 2011
# Copyright (C) Jehan 2013-2020
#
# The contents of this file are subject to the Mozilla Public License Version 1.1; you may not use this file except in
# compliance with the License. You may obtain a copy of the License at http://www.mozilla.org/MPL/

from urllib.request import urlretrieve, urlopen
import urllib.error
import fnmatch
import logging
import os.path
import sys
import shutil
import tarfile
import re
import zipfile
import time
import mimetypes
import subprocess
import glob
import marshal

_packages = []
_package_filelists = {}
_package_src_filelists = {}

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

prefix = None
try:
    prefix = os.path.abspath(os.environ['CROSSROAD_PREFIX'])
except KeyError:
    sys.stderr.write('$CROSSROAD_PREFIX was not set!\n')
    sys.exit(os.EX_UNAVAILABLE)

artifacts = None
try:
    artifacts = os.path.abspath(os.environ['CROSSROAD_HOME'])
    installed_packages_file = os.path.join(artifacts, 'crossroad-mingw-install.installed')
    masked_packages_file = os.path.join(artifacts, 'crossroad-mingw-install.masked')
    repository_file = os.path.join(artifacts, 'crossroad-mingw-install.repository')
except KeyError:
    sys.stderr.write('$CROSSROAD_HOME was not set!\n')
    sys.exit(os.EX_UNAVAILABLE)

_packageCacheDirectory = os.path.join(xdg_cache_home, 'crossroad', 'package')
_repositoryCacheDirectory = os.path.join(xdg_cache_home, 'crossroad', 'repository')
_extractedCacheDirectory = os.path.join(xdg_cache_home, 'crossroad', 'extracted')
_extractedFilesDirectory = os.path.join(xdg_cache_home, 'crossroad', 'prefix')

repositories = {
  'msys2':
    'http://repo.msys2.org/mingw/ARCH/',
  'fedora30':
    'https://download.fedoraproject.org/pub/fedora/linux/releases/30/Everything/x86_64/os/',
  'fedora31':
    'https://download.fedoraproject.org/pub/fedora/linux/releases/31/Everything/x86_64/os/',
  'fedora32':
    'https://download.fedoraproject.org/pub/fedora/linux/releases/32/Everything/x86_64/os/',
  'suse':
    'http://download.opensuse.org/repositories/windows:/mingw:/ARCH/openSUSE_Leap_42.3/'
}

def detect_distribution_repo (options):
  '''
  Detect the current repository distribution so that you install
  libraries compiled by the used compiler by default.
  When your distribution has no Mingw-w64 packages, just use the last
  Fedora repository. You may encounter build issues, but at least you
  tried!
  '''

  reponame = None

  if options.repo is not None:
    # A repo has been specified on this command, bypass settings.
    if options.repo in repositories:
      reponame = options.repo
    else:
      logging.error('"{}" is not a known repository.\n'.format(options.repo))
      sys.exit(os.EX_USAGE)
  else:
    # Look up stored settings.
    try:
      with open(repository_file, 'r') as f:
        contents = f.read().strip()
        if contents in repositories:
          reponame = contents
    except FileNotFoundError:
      pass

    if reponame is None:
      # Finally auto-detect.
      if os.path.isfile('/etc/fedora-release'):
        release = None
        with open('/etc/fedora-release', 'r') as f:
          release = f.read().strip()
          if release.find('Fedora release 30') != -1:
            reponame = 'fedora30'
          elif release.find('Fedora release 31') != -1:
            reponame = 'fedora31'
      elif os.path.isfile('/etc/SuSE-release'):
        reponame = 'suse'

  # Default to msys2 repo.
  if reponame is None:
    reponame = 'msys2'

  repo = repositories[reponame]
  # Unlike Fedora which has both 32-bit and 64-bit Windows package in a
  # same repository, SUSE provides 2 repositories.
  if reponame == 'suse':
    if options.arch == 'w32':
      repo = repo.replace('ARCH', 'win32');
    else:
      repo = repo.replace('ARCH', 'win64');
  elif reponame == 'msys2':
    if options.arch == 'w32':
      repo = repo.replace('ARCH', 'i686');
    else:
      repo = repo.replace('ARCH', 'x86_64');

  return reponame, repo

def get_package_files (package, repo, options):
    '''
    Research and return the list of files for a package name.
    '''
    file_list = None
    real_name = None
    if options.srcpkg:
        filelists = _package_src_filelists
    else:
        filelists = _package_filelists
    try:
        real_name = package
        file_list = filelists[package]
    except KeyError:
        if options.arch == 'w64':
            try:
                if repo == 'msys2':
                    real_name = 'mingw-w64-x86_64-' + package
                else:
                    real_name = 'mingw64-' + package
                file_list = filelists[real_name]
            except KeyError:
                real_name = None
                file_list = None
        if file_list is None:
            # There are some 32-bit package in the 64-bit list.
            try:
                if repo == 'msys2':
                    real_name = 'mingw-w64-i686-' + package
                else:
                    real_name = 'mingw32-' + package
                file_list = filelists[real_name]
            except KeyError:
                real_name = None
                file_list = None
    if file_list is not None:
        if repo == 'msys2':
            if options.arch == 'w64':
                file_list = [f for f in file_list if re.match(r'^mingw64/', f['path']) is not None]
            else:
                file_list = [f for f in file_list if re.match(r'^mingw32/', f['path']) is not None]
        else:
            file_list = [f for f in file_list if re.match(r'/usr/[^/]+-mingw32/sys-root/mingw', f['path']) is not None]
        for f in file_list:
            if repo == 'msys2':
                if options.arch == 'w64':
                    f['path'] = re.sub(r'^mingw64', prefix, f['path'])
                else:
                    f['path'] = re.sub(r'^mingw32', prefix, f['path'])
            else:
                f['path'] = re.sub(r'/usr/[^/]+-mingw32/sys-root/mingw', prefix, f['path'])
    return (real_name, file_list)

def fix_symlink (path):
    '''
    if path is a symlink, fixes it with a relative prefix.
    '''
    if os.path.islink (path):
        link_path = os.readlink (path)
        if os.path.isabs (link_path):
            # First I make it an absolute path in our new prefix.
            link_path = re.sub(r'/usr/[^/]+-mingw32/sys-root/mingw', prefix, link_path)
            # Then I make it a path relative to the symlink file in our same prefix.
            # Because likely relative symlinks won't need to be fixed again,
            # even when we will move the tree to a new prefix.
            link_path = os.path.relpath (link_path, os.path.dirname (path))
            os.unlink (path)
            os.symlink (link_path, path, target_is_directory = os.path.isdir (path))

def fix_package_symlinks (package, repo, options):
    (real_name, file_list) = get_package_files (package, repo, options)
    if file_list is not None:
        for f in file_list:
            fix_symlink (f['path'])

def arch_files_to_package(repository, path):
  files = []
  with open(path, 'r') as f:
    for line in f:
      if line.strip() == '%FILES%':
        break
    for line in f:
      filename = line.strip()
      if filename == '':
        break
      if filename.endswith('/'):
        files += [{'type': 'dir', 'path': filename}]
      else:
        files += [{'type': 'file', 'path': filename}]
  return files

def arch_desc_to_package(repository, path):
  name         = None
  arch         = None
  summary      = None
  description  = None
  project_url  = None
  packager_url = None
  url          = None
  version      = None
  license      = None
  buildtime    = None
  filename     = None
  checksum     = {}
  provides     = set()
  requires     = set()
  with open(path, 'r') as f:
    for line in f:
        if line.strip() == '%FILENAME%':
            filename = f.readline().strip()
            url = os.path.join(repository, filename)
        elif line.strip() == '%ARCH%':
            arch = f.readline().strip()
        elif line.strip() == '%LICENSE%':
            license = f.readline().strip()
        elif line.strip() == '%NAME%':
            name = f.readline().strip()
            packager_url = 'https://packages.msys2.org/package/' + name
        elif line.strip() == '%VERSION%':
            version = f.readline().strip()
            index = version.rfind('-')
            if index != -1:
                rel = version[index + 1:]
                version = version[:index]
            version = { 'epoch': 0, 'ver': version, 'rel': rel }
        elif line.strip() == '%DESC%':
            description = f.readline().strip()
        elif line.strip() == '%URL%':
            project_url = f.readline().strip()
        elif line.strip() == '%SHA256SUM%':
            checksum['sha256'] = f.readline().strip()
        elif line.strip() == '%MD5SUM%':
            checksum['md5'] = f.readline().strip()
        elif line.strip() == '%BUILDDATE%':
            buildtime = int(f.readline().strip())
        elif line.strip() == '%PROVIDES%':
            for deps in f:
                if deps.strip() == '':
                    break;
                provides.add(deps.strip())
        elif line.strip() == '%DEPENDS%':
            for deps in f:
                if deps.strip() == '':
                    break;
                requires.add(deps.strip())
  package = {
      'name': name,
      'arch': arch,
      'summary': summary,
      'description': description,
      'project_url': project_url,
      'packager_url': packager_url,
      'url': url,
      'version': version,
      'license': license,
      'buildtime': buildtime,
      'filename': filename,
      'checksum': checksum,
      'provides': provides,
      'requires': requires,
    }
  return package

def UpdateArchRepository(repositoryLocation, arch, force=True):
  global _packages
  global _package_filelists
  global _package_src_filelists

  _packages = []
  _package_filelists = {}
  _package_src_filelists = {}

  # It is to be noted that 2 files are available, for instance for w64:
  # mingw64.db and mingw64.files. It turns out that the *.files contain
  # also all the information from the *.db. So let's just download the
  # *.files one.
  #db_name = 'ming{}.db'.format(arch)
  db_name = 'ming{}.files'.format(arch)
  db_dir = os.path.join(_repositoryCacheDirectory, 'msys2')
  os.makedirs(db_dir, exist_ok=True)
  db_tar = os.path.join(db_dir, db_name)

  if force and os.path.exists(db_tar):
    os.unlink(db_tar)

  if force or not os.path.exists(db_tar):
    logging.warning('Downloading repository data: {}'.format(repositoryLocation + db_name))
    with urlopen(repositoryLocation + db_name, timeout = 5.0) as db_file:
      with open(db_tar, 'wb') as local_file:
        local_file.write(db_file.read())

  # Cleaning old files once new download completed, so that we still
  # have some old repo data if download failed.
  for f in os.listdir(db_dir):
    if f.startswith('mingw-w64-'):
      os.unlink(os.path.join(db_dir, f, 'desc'))
      os.unlink(os.path.join(db_dir, f, 'files'))
      os.rmdir(os.path.join(db_dir, f))

  logging.warning('Extracting repository data: {}'.format(db_tar))
  tar = tarfile.open(db_tar, 'r:gz')
  tar.extractall(path=db_dir)
  tar.close()

  for package_name in os.listdir(path=db_dir):
    package_dir = os.path.join(db_dir, package_name)
    if os.path.isdir(package_dir):
      desc_path = os.path.join(package_dir, 'desc')
      if os.path.isfile(desc_path):
        package = arch_desc_to_package(repositoryLocation, desc_path)
        _packages += [ package ]

        files_path = os.path.join(package_dir, 'files')
        if os.path.isfile(files_path):
          files = arch_files_to_package(repositoryLocation, files_path)
          _package_filelists[package['name']] = files

  if os.path.exists(db_tar + '.descs'):
    os.unlink(db_tar + '.descs')
  if os.path.exists(db_tar + '.filelists'):
    os.unlink(db_tar + '.filelists')

  # Save serialized databases for later easy reuse.
  with open(db_tar + ".descs", "wb") as f:
    marshal.dump(_packages, f)
  with open(db_tar + ".filelists", "wb") as f:
    marshal.dump(_package_filelists, f)

def OpenArchRepository(repositoryLocation, arch):
  global _packages
  global _package_filelists
  global _package_src_filelists

  # It is to be noted that 2 files are available, for instance for w64:
  # mingw64.db and mingw64.files. It turns out that the *.files contain
  # also all the information from the *.db. So let's just download the
  # *.files one.
  #db_name = 'ming{}.db'.format(arch)
  db_name = 'ming{}.files'.format(arch)
  db_dir = os.path.join(_repositoryCacheDirectory, 'msys2')
  os.makedirs(db_dir, exist_ok=True)
  db_tar = os.path.join(db_dir, db_name)

  try:
    # Try to load directly our serialized database. Unlike the RPM
    # repository where we can check if the database is up-to-date, we
    # can't do so on the Arch repo (not that I found at least). So we
    # just have to rely on people manually updating the repo.
    with open(db_tar + ".descs", "rb") as f:
      _packages = marshal.load(f)
    with open(db_tar + ".filelists", "rb") as f:
      _package_filelists = marshal.load (f)
  except:
    UpdateArchRepository(repositoryLocation, arch, force=False)

def OpenRPMRepository(repositoryLocation, arch):
  from xml.etree.cElementTree import parse as xmlparse
  global _packages
  global _package_filelists
  global _package_src_filelists
  # Check repository for latest primary.xml
  try:
      with urlopen(repositoryLocation + 'repodata/repomd.xml', timeout = 5.0) as metadata:
        doctree = xmlparse(metadata)
      xmlns = 'http://linux.duke.edu/metadata/repo'
      for element in doctree.findall('{%s}data'%xmlns):
        if element.get('type') == 'primary':
          primary_url = element.find('{%s}location'%xmlns).get('href')
        elif element.get('type') == 'filelists':
          filelist_url = element.find('{%s}location'%xmlns).get('href')
      # Make sure all the cache directories exist
      for dir in _packageCacheDirectory, _repositoryCacheDirectory, _extractedCacheDirectory:
        try:
          os.makedirs(dir)
        except OSError: pass
      # Download repository metadata (only if not already in cache)
      primary_filename = os.path.join(_repositoryCacheDirectory, os.path.splitext(os.path.basename(primary_url))[0])
      if not os.path.exists(primary_filename):
        logging.warning('Downloading repository data: {}'.format(repositoryLocation + primary_url))
        with urlopen(repositoryLocation + primary_url, timeout = 5.0) as primaryGzFile:
          import io, gzip
          primaryGzString = io.BytesIO(primaryGzFile.read()) #3.2: use gzip.decompress
          with gzip.GzipFile(fileobj=primaryGzString) as primaryGzipFile:
            with open(primary_filename, 'wb') as primaryFile:
              primaryFile.writelines(primaryGzipFile)
      # Also download the filelist.
      filelist_filename = os.path.join(_repositoryCacheDirectory, os.path.splitext(os.path.basename(filelist_url))[0])
      if not os.path.exists(filelist_filename):
        logging.warning('Downloading repository file list.')
        with urlopen(repositoryLocation + filelist_url, timeout = 5.0) as GzFile:
          import io, gzip
          GzString = io.BytesIO(GzFile.read()) #3.2: use gzip.decompress
          with gzip.GzipFile(fileobj=GzString) as primaryGzipFile:
            with open(filelist_filename, 'wb') as filelist_file:
              filelist_file.writelines(primaryGzipFile)
      # Cleaning old files at the end, so that we still have some old repo data if download failed.
      for f in os.listdir(_repositoryCacheDirectory):
        if f[-14:] == '-filelists.xml' and f != os.path.splitext(os.path.basename(filelist_url))[0]:
            os.unlink(os.path.join(_repositoryCacheDirectory, f))
        if f[-12:] == '-primary.xml' and f != os.path.splitext(os.path.basename(primary_url))[0]:
            os.unlink(os.path.join(_repositoryCacheDirectory, f))
  except:
    # If we can't download but there is already a primary.xml and filelists.xml, let's use them.
    primary_files = glob.glob (_repositoryCacheDirectory + '/*-primary.xml')
    filelist_files = glob.glob (_repositoryCacheDirectory + '/*-filelists.xml')
    if len (primary_files) > 0 and len (filelist_files) > 0:
        # Files exist. In case there are more than 1 (there should not be in stable version,
        # but right now, we never clean out cache), we have no good way to know which is the
        # most recent, because there is no date or id. So we just take the first one at random.
        logging.warning ('Error opening repository. Using cached files instead.')
        primary_filename = primary_files[0]
        filelist_filename = filelist_files[0]
    else:
        # Reraise the download error.
        raise
  try:
      with open(primary_filename + ".data", "rb") as f:
        _packages = marshal.load(f)
  except:
      # Parse package list from XML
      elements = xmlparse(primary_filename)
      xmlns = 'http://linux.duke.edu/metadata/common'
      rpmns = 'http://linux.duke.edu/metadata/rpm'
      _packages = [{
          'name': p.find('{%s}name'%xmlns).text,
          'arch': p.find('{%s}arch'%xmlns).text,
          'summary': p.find('{%s}summary'%xmlns).text,
          'description': p.find('{%s}description'%xmlns).text,
          'project_url': p.find('{%s}url'%xmlns).text,
          'packager_url': None,
          'url': repositoryLocation + p.find('{%s}location'%xmlns).get('href'),
          'version': {'epoch': p.find('{%s}version'%xmlns).get('epoch'),
                      'ver': p.find('{%s}version'%xmlns).get('ver'),
                      'rel': p.find('{%s}version'%xmlns).get('rel')},
          #'license': p.find('{%s}location/{%s}format/{%s}license'%(xmlns, xmlns, rpmns)).text,
          'buildtime': int(p.find('{%s}time'%xmlns).get('build')),
          'filename': os.path.basename(p.find('{%s}location'%xmlns).get('href')),
          'checksum': { p.find('{%s}checksum'%xmlns).get('type') : p.find('{%s}checksum'%xmlns).text },
          'provides': {provides.attrib['name'] for provides in p.findall('{%s}format/{%s}provides/{%s}entry'%(xmlns,rpmns,rpmns))},
          'requires': {req.attrib['name'] for req in p.findall('{%s}format/{%s}requires/{%s}entry'%(xmlns,rpmns,rpmns))}
        } for p in elements.findall('{%s}package'%xmlns)]
      # Note: XPath should be able to find directly with:
      # elements.findall("{%s}package/{%s}name[starts-with(., 'mingw')]/.."% (xmlns,xmlns))
      # Unfortunaly XPath support of Python is too limited, so I have to do
      # it in a separate step below.
      _packages = [p for p in _packages if p['name'].startswith('ming' + arch + '-')]
      with open(primary_filename + ".data", "wb") as f:
        marshal.dump(_packages, f)
  try:
      with open(filelist_filename + ".data", "rb") as f:
        _package_filelists = marshal.load (f)
      with open(filelist_filename + ".src.data", "rb") as f:
        _package_src_filelists = marshal.load (f)
  except:
      # Package's file lists.
      elements = xmlparse(filelist_filename)
      xmlns = 'http://linux.duke.edu/metadata/filelists'
      _package_filelists = {
          p.get('name') : [
            {'type': f.get('type', default='file'), 'path': f.text} for f in p.findall('{%s}file'%xmlns)
        ] for p in elements.findall('{%s}package'%xmlns)
      }
      _package_filelists = {name : _package_filelists[name] for name in _package_filelists if name.startswith('ming' + arch + '-')}
      _package_src_filelists = {
          p.get('name') : [
            {'type': f.get('type', default='file'), 'path': f.text} for f in p.findall('{%s}file'%xmlns)
        ] for p in elements.findall('{%s}package'%xmlns) if p.get('arch') == 'src'}
      _package_src_filelists = {name : _package_src_filelists[name] for name in _package_src_filelists if name.startswith('ming' + arch + '-')}
      with open(filelist_filename + ".data", "wb") as f:
        marshal.dump(_package_filelists, f)
      with open(filelist_filename + ".src.data", "wb") as f:
        marshal.dump(_package_src_filelists, f)

def search_packages(keyword, arch, srcpkg = False, search_files = False):
  # Just in case the user was looking for a specific rpm file,
  # I trim out the filename parts and keep the main naming.
  keyword = re.sub('^mingw(32|64)-', '', packageBaseName(keyword.lower()))
  packages = []
  if search_files:
      if srcpkg:
          filelists = _package_src_filelists
      else:
          filelists = _package_filelists
      filter_func = lambda p: \
          len([f['path'] for f in filelists[p] if os.path.basename(f['path']).lower().find(keyword) != -1]) > 0
      packages = sorted([p for p in filelists if filter_func(p)])
  else:
      filter_func = lambda p: \
         re.sub('^ming' + arch + '-', '', p['name'].lower()).find(keyword) != -1 \
         and ((p['arch'] == 'src') if srcpkg else True)
      packages = sorted([p['name'] for p in _packages if filter_func(p)])
  return packages

def _findPackage(packageName, arch, srcpkg=False):
  if arch == 'w32':
    arch_pkg_prefix = 'mingw-w64-i686-'
  else:
    arch_pkg_prefix = 'mingw-w64-x86_64-'
  filter_func = lambda p: \
    (p['name'] == 'ming' + arch + '-' + packageName          or \
     p['name'] == arch_pkg_prefix + packageName              or \
     p['name'] == packageName or p['filename'] == packageName)  \
    and ((p['arch'] == 'src') if srcpkg else True)
  sort_func = lambda p: p['buildtime']
  packages = sorted([p for p in _packages if filter_func(p)], key=sort_func, reverse=True)
  if len(packages) == 0:
    return None
  if len(packages) > 1:
    logging.error('multiple packages found for %s:', packageName)
    for p in packages:
      logging.error('  %s', p['filename'])
  return packages[0]

def _checkPackageRequirements(package, packageNames):
  allProviders = set()
  for requirement in package['requires']:
    providers = {p['name'] for p in _packages if requirement in p['provides'] or requirement == p['name']}
    if len(providers & packageNames) == 0:
      if len(providers) == 0:
        logging.error('Package %s requires %s, not provided by any package', package['name'], requirement)
      else:
        logging.warning('Package %s requires %s, provided by: %s', package['name'], requirement, ','.join(providers))
        allProviders.add(providers.pop())
  return allProviders

def packageBaseName(rpm):
    return re.sub(r'-([0-9]|\.)+-[0-9]\.[0-9].(src|noarch)\.(rpm|cpio)$', '', rpm)

def packagesDownload(packageNames, arch,
                     installed_packages,
                     masked_packages,
                     withDependencies = False,
                     srcpkg           = False,
                     nocache          = False,
                     force_install    = False):
  packageNames_new = {pn for pn in packageNames if pn.endswith('.rpm')}
  for packageName in packageNames - packageNames_new:
    matchedpackages = {p['name'] for p in _packages if fnmatch.fnmatchcase(p['name'].replace('mingw32-', '').replace('mingw64-', '').replace('mingw-w64-x86_64-', '').replace('mingw-w64-i686-', ''), packageName) and ((p['arch'] == 'src') if srcpkg else True)}
    packageNames_new |= matchedpackages if len(matchedpackages) > 0 else {packageName}
  packageNames = list(packageNames_new)
  allPackageNames = set(packageNames)

  packageFilenames = []
  while len(packageNames) > 0:
    packName = packageNames.pop()
    if not force_install:
      if packName in installed_packages:
        logging.warning('Package "{}" already installed. Skipping.'.format(packName))
        continue
      elif packName in masked_packages:
        logging.warning('Package "{}" is masked. Skipping.'.format(packName))
        continue
    package = _findPackage(packName, arch, srcpkg)
    if package is None:
      logging.error('Package %s not found', packName)
      alt_packages = search_packages(packName, arch, srcpkg)
      if len(alt_packages) > 0:
          logging.error('Did you mean:')
          for alt_pkg in alt_packages:
              logging.error('\t- {}'.format(re.sub('^mingw(32|64)-', '', alt_pkg)))
      logging.error('Exiting without installing.')
      sys.exit(os.EX_NOINPUT)
    dependencies = _checkPackageRequirements(package, allPackageNames)
    if withDependencies and len(dependencies) > 0:
      packageNames.extend(dependencies)
      allPackageNames |= dependencies
    if packName[-6:] == '-devel' and _findPackage(packName[:-6], arch, srcpkg) is not None:
        logging.warning('{} is a devel package. Adding {}'.format(packName, packName[:-6]))
        packageNames.append(packName[:-6])
        allPackageNames.add(packName[:-6])
    localFilenameFull = os.path.join(_packageCacheDirectory, package['filename'])
    os.makedirs(_packageCacheDirectory, exist_ok=True)
    os.makedirs(_extractedCacheDirectory, exist_ok=True)
    # First removing any outdated version of the rpm.
    package_basename = packageBaseName(package['filename'])
    for f in os.listdir(_packageCacheDirectory):
        if packageBaseName(f) == package_basename and f != package['filename']:
            logging.warning('Deleting outdated cached version of {}.'.format(package_basename))
            os.unlink(os.path.join(_packageCacheDirectory, f))
    if nocache or not os.path.exists(localFilenameFull):
        logging.warning('Downloading %s', package['filename'])
        # When I download a rpm, I would also remove any extracted cpio
        # of this package which may have been left behind.
        for f in os.listdir(_extractedCacheDirectory):
            if packageBaseName(f) == package_basename:
                os.unlink(os.path.join(_extractedCacheDirectory, f))
        retry = 4
        last_error = None
        while retry >= 0:
            try:
                with urlopen(package['url'], timeout = 120.0) as remote_package:
                    with open(localFilenameFull, 'wb') as local_file:
                        local_file.write(remote_package.read())
                break
            except urllib.error.URLError as e:
                logging.warning('Download failed: {} (errno: {})'.format(e.reason, e.errno))
                #if e.errno == 110: # ETIMEDOUT
                #logging.warning('Retrying…')
                retry -= 1
                last_error = e
                continue
        else:
            # Errors occured at every attempt.
            # Re-raise the last exception because continuing with a
            # partial list of packages leads to hard-to-debug errors.
            logging.warning('Abandonning.')
            raise last_error
    else:
        logging.warning('Using cached package %s', localFilenameFull)
    packageFilenames.append(package['filename'])
  return (allPackageNames, packageFilenames)

def _extractFile(filename, output_dir=_extractedCacheDirectory):
  try:
    logfile_name = '_crossroad-mingw-install_extractFile.log'
    with open(logfile_name, 'w') as logfile:
      if filename[-5:] == '.cpio':
        # 7z loses links and I can't find an option to change this behavior.
        # So I use the cpio command for cpio files, even though it might create broken links.
        cwd = os.getcwd()
        os.makedirs(output_dir, exist_ok=True)
        os.chdir (output_dir)
        subprocess.check_call('cpio -i --make-directories <' + filename, stderr=logfile, stdout=logfile, shell = True)
        os.chdir (cwd)
      elif filename[-4:] == '.rpm' and shutil.which('rpm2cpio') is not None:
        cwd = os.getcwd()
        os.makedirs(output_dir, exist_ok=True)
        os.chdir (output_dir)
        subprocess.check_call('rpm2cpio "{}" | cpio -i --make-directories '.format(filename), stderr=logfile, stdout=logfile, shell = True)
        os.chdir (cwd)
      else:
        subprocess.check_call(['7z', 'x', '-o'+output_dir, '-y', filename], stderr=logfile, stdout=logfile)
    os.remove(logfile_name)
    return True
  except:
    logging.error('Failed to extract %s', filename)
    return False

def GetBaseDirectory(repo, arch):
  if repo == 'msys2':
    if arch == 'w32' and os.path.exists(os.path.join(_extractedFilesDirectory, 'mingw32')):
      return os.path.join(_extractedFilesDirectory, 'mingw32')
    elif arch == 'w64' and os.path.exists(os.path.join(_extractedFilesDirectory, 'mingw64')):
      return os.path.join(_extractedFilesDirectory, 'mingw64')
  else:
    if arch == 'w32' and os.path.exists(os.path.join(_extractedFilesDirectory, 'usr/i686-w64-mingw32/sys-root/mingw')):
      return os.path.join(_extractedFilesDirectory, 'usr/i686-w64-mingw32/sys-root/mingw')
    elif arch == 'w64' and os.path.exists(os.path.join(_extractedFilesDirectory, 'usr/x86_64-w64-mingw32/sys-root/mingw')):
      return os.path.join(_extractedFilesDirectory, 'usr/x86_64-w64-mingw32/sys-root/mingw')
  return None

def packagesExtract(packageFilenames, srcpkg=False):
  for packageFilename in packageFilenames :
    logging.warning('Extracting %s', packageFilename)
    if packageFilename.endswith('.rpm'):
      if not packagesExtractRPM(packageFilename, srcpkg):
        return False
    else:
      if not packagesExtractTAR(packageFilename, srcpkg):
        return False
  return True

def packagesExtractTAR(packageFilename, srcpkg=False):
  tar_path = os.path.join(_packageCacheDirectory, packageFilename)
  if tar_path.endswith('.tar.xz'):
      tar = tarfile.open(tar_path, 'r:xz')
      tar.extractall(path=_extractedFilesDirectory)
      tar.close()
  elif tar_path.endswith('tar.zst'):
      import zstandard
      import tempfile
      decomp = zstandard.ZstdDecompressor()
      with open(tar_path, 'rb') as inp, tempfile.TemporaryFile() as out:
          decomp.copy_stream(inp, out)
          out.seek(0)
          tar = tarfile.open(fileobj=out, mode='r|')
          tar.extractall(path=_extractedFilesDirectory)
          tar.close()
  else:
      # So far, I've seen only xz and zst-compressed archives in Arch
      # repository. Let's make this as a catch-all for other cases.
      tar = tarfile.open(tar_path, 'r:*')
      tar.extractall(path=_extractedFilesDirectory)
      tar.close()
  return True

def packagesExtractRPM(packageFilename, srcpkg=False):
  rpm_path = os.path.join(_packageCacheDirectory, packageFilename)
  if shutil.which('rpm2cpio') is None:
      # If using 7z, we have to make an intermediary step.
      cpioFilename = os.path.join(_extractedCacheDirectory, os.path.splitext(packageFilename)[0] + '.cpio')
      if not os.path.exists(cpioFilename) and not _extractFile(rpm_path, _extractedCacheDirectory):
          return False
      if srcpkg:
        if not _extractFile(cpioFilename, os.path.join(_extractedFilesDirectory, os.path.splitext(packageFilename)[0])):
            return False
      else:
        if not _extractFile(cpioFilename, _extractedFilesDirectory):
            return False
  elif srcpkg:
      if not _extractFile(rpm_path, os.path.join(_extractedFilesDirectory, os.path.splitext(packageFilename)[0])):
          return False
  else:
      if not _extractFile(rpm_path, _extractedFilesDirectory):
          return False
  return True

def move_files(repo, arch, from_file, to_file):
    if repo == 'msys2':
        if arch == 'w64':
            regexp = re.compile(b'/mingw64')
        else:
            regexp = re.compile(b'/mingw32')
    else:
        regexp = re.compile(b'/usr/[^/]+-mingw32/sys-root/mingw')
    if os.path.isdir(from_file) and not os.path.islink(from_file):
        # A normal directory.
        # Directory symlinks will be later fixed by fix_package_symlinks().
        try:
            os.makedirs(to_file, exist_ok=True)
        except FileExistsError:
            # This exception would not happen if `to_file` exists and is a directory.
            # But I had the strange case where it existed as a file, and the error still occurred.
            # Not sure this is the right solution, but I will just output a warning and delete it.
            logging.warning ("{} exists as a file, but we want a directory. Deleting.")
            os.unlink (to_file)
            os.makedirs(to_file, exist_ok=True)
        for f in os.listdir(from_file):
            move_files(repo, arch, os.path.join(from_file, f), os.path.join(to_file, f))
        shutil.rmtree(from_file)
    elif os.path.islink(from_file):
        try:
            # Don't try to read a symlink since its source may already be
            # gone if it has been moved before.
            # No need to try and fix the link either. fix_package_symlinks()
            # will take care of it later.
            shutil.move(from_file, to_file)
        except FileExistsError:
            os.unlink (to_file)
            shutil.move(from_file, to_file)
    else:
        if to_file[-3:] == '.pc'     or \
           to_file[-3:] == '.la'     or \
           to_file[-3:] == '.py'     or \
           to_file[-7:] == '-config' or \
           (to_file.endswith('gdbus-codegen')    and \
            shutil.which('mimetype') is not None and \
            subprocess.check_output(['mimetype', '-b', from_file], universal_newlines=True)[:5] == 'text/'):
            # XXX I had the case with "bin/gdbus-codegen" which has the prefix inside the script.
            # XXX mimetypes python module would not always work because it only relies on extension.
            # Use mimetype command if possible instead.
            try:
                with open(from_file, 'rb') as fr, open(to_file, 'wb') as fw:
                  for lr in fr:
                    lr = regexp.sub(prefix.encode(), lr, count=0)
                    fw.write(lr)
            except IOError:
                sys.stderr.write('File "{}" could not be moved.\n'.format(from_file))
                sys.exit(os.EX_CANTCREAT)
            # Since it's a move, unlink the original.
            os.unlink (from_file)
        else:
            shutil.move(from_file, to_file)

def CleanExtracted():
    shutil.rmtree(_extractedFilesDirectory, True)

def SetExecutableBit():
    # set executable bit on anything in bin/
    bin_dir = os.path.join(prefix, 'bin')
    if os.path.isdir(bin_dir):
        for f in os.listdir(bin_dir):
            # Make sure I chmod only binary in prefix/ and not linked from elsewhere
            # because I have only control on prefix for sure.
            fullpath = os.path.join(bin_dir, f)
            if os.path.islink (fullpath):
                link_path = os.path.abspath (os.readlink (fullpath))
                if link_path.find (os.path.abspath (prefix)) != 0:
                    continue
            os.chmod(fullpath, 0o755)
    # set executable bit on libraries and executables whatever the path.
    for root, dirs, files in os.walk(prefix):
        for filename in {f for f in files if f.endswith('.dll') or f.endswith('.exe')} | set(dirs):
            fullpath = os.path.join(root, filename)
            if os.path.islink (fullpath):
                link_path = os.path.abspath (os.readlink (fullpath))
                if link_path.find (os.path.abspath (prefix)) != 0:
                    continue
            os.chmod(fullpath, 0o755)

def GetOptions():
  from optparse import OptionParser, OptionGroup #3.2: use argparse

  parser = OptionParser(usage="usage: %prog [options] packages",
                        description="Easy download of RPM packages for Windows.")

  # Options specifiying download repository
  default_arch = "w64"
  default_repo = None
  repoOptions = OptionGroup(parser, "Specify download repository")
  repoOptions.add_option("-a", "--arch", dest="arch", default=default_arch,
                         metavar="ARCH", help="w32 or w64 [%default]")
  repoOptions.add_option("-r", "--repo", dest="repo", default=default_repo,
                         metavar="REPO", help="Download from REPO [%default]")
  parser.add_option_group(repoOptions)

  # Package selection options
  parser.set_defaults(withdeps=False)
  packageOptions = OptionGroup(parser, "Package selection")
  packageOptions.add_option("--update", action="store_true", dest="update", default=False, help="Update the repository data")
  packageOptions.add_option("--deps", action="store_true", dest="withdeps", help="Download dependencies")
  packageOptions.add_option("--no-deps", action="store_false", dest="withdeps", help="Do not download dependencies [default]")
  packageOptions.add_option("--src", action="store_true", dest="srcpkg", default=False, help="Download source instead of noarch package")
  packageOptions.add_option("--nocache", action="store_true", dest="nocache", default=False,
                            help="Force package download even if it is in cache.")
  packageOptions.add_option("--list-files", action="store_true", dest="list_files", default=False, help="Only list the files of a package")
  packageOptions.add_option("--search", action="store_true", dest="search", default=False, help="Search packages.")
  packageOptions.add_option("--info", action="store_true", dest="info", default=False, help="Output information about a package")
  packageOptions.add_option("--uninstall", action="store_true", dest="uninstall", default=False, help="Uninstall the list of packages")
  packageOptions.add_option("--mask", action="store_true", dest="mask", default=False, help="Mask the list of packages")
  packageOptions.add_option("--unmask", action="store_true", dest="unmask", default=False, help="Unmask the list of packages")
  packageOptions.add_option("--list-sources", action="store_true", dest="list_sources", default=False, help="List package sources")
  packageOptions.add_option("--set-source", action="store_true", dest="set_source", default=False, help="Set package source")
  packageOptions.add_option("--force-install", action="store_true",
                            dest="force_install",
                            default=False, help="Force already installed package re-installation")
  parser.add_option_group(packageOptions)

  # Output options
  outputOptions = OptionGroup(parser, "Output options", "Normally the downloaded packages are extracted in the current directory.")
  outputOptions.add_option("--no-clean", action="store_false", dest="clean", default=True,
                           help="Do not remove previously extracted files")
  outputOptions.add_option("-z", "--make-zip", action="store_true", dest="makezip", default=False,
                           help="Make a zip file of the extracted packages (the name of the zip file is based on the first package specified)")
  outputOptions.add_option("-m", "--add-metadata", action="store_true", dest="metadata", default=False,
                           help="Add a file containing package dependencies and provides")
  parser.add_option_group(outputOptions)

  # Other options
  parser.add_option("-q", "--quiet", action="store_false", dest="verbose", default=True,
                    help="Don't print status messages to stderr")

  (options, args) = parser.parse_args()

  return (options, args)

if __name__ == "__main__":
  (options, args) = GetOptions()
  packages = set(args)
  logging.basicConfig(level=(logging.WARNING if options.verbose else logging.ERROR), format='%(message)s', stream=sys.stderr)

  if options.arch != 'w32' and options.arch != 'w64':
    logging.error('"{}" is not a known mingw arch.\n'.format(options.arch))
    sys.exit(os.EX_USAGE)

  # Update the cache directories.
  _packageCacheDirectory = os.path.join(_packageCacheDirectory, options.arch)
  _repositoryCacheDirectory = os.path.join(_repositoryCacheDirectory, options.arch)
  _extractedCacheDirectory = os.path.join(_extractedCacheDirectory, options.arch)
  _extractedFilesDirectory = os.path.join(_extractedFilesDirectory, options.arch)

  reponame, repo = detect_distribution_repo(options)

  if options.list_sources:
    sys.stdout.write('Available repository sources: {}, autodetect.\n'.format(', '.join(repositories)))
    sys.stdout.write('Currently selected repository: {}.\n'.format(reponame))
    sys.exit(os.EX_OK)
  if options.set_source:
    if len(args) != 1:
      sys.stderr.write('Error: only one source repository expected, {} provided.\n'.format(len(args)))
      sys.exit(os.EX_USAGE)
    reponame = args[0]
    if reponame == 'autodetect':
      try:
        os.unlink (repository_file)
      except FileNotFoundError:
        pass
      sys.exit(os.EX_OK)
    elif reponame not in repositories:
      sys.stderr.write('Error: unknown package source "{}".\n'.format(reponame))
      sys.exit(os.EX_DATAERR)
    with open(repository_file, 'w') as f:
      f.write(reponame)
    sys.exit(os.EX_OK)

  # Open repository
  try:
    if reponame in [ 'msys2' ]:
      OpenArchRepository(repo, options.arch)
    else:
      OpenRPMRepository(repo, options.arch)
  except Exception as e:
    sys.exit('Error opening repository:\n\t%s\n\t%s' % (repo, e))

  if options.update:
    try:
      if reponame in [ 'msys2' ]:
        UpdateArchRepository(repo, options.arch, force=True)
      else:
        # Nothing to do for the RPM repo. It'll update by itself when
        # needed.
        pass
    except Exception as e:
      sys.exit(os.EX_UNAVAILABLE)
    sys.exit(os.EX_OK)

  if options.search:
    if (len(packages) == 0):
        logging.error('Please provide at least one package.\n')
        sys.exit(os.EX_USAGE)
    if options.srcpkg:
        package_type = 'Source package'
    else:
        package_type = 'Package'
    for keyword in packages:
        alt_packages = search_packages(keyword, options.arch, options.srcpkg)
        if len(alt_packages) > 0:
            sys.stdout.write('The following packages were found for the search "{}":\n'.format(keyword))
            for alt_pkg in alt_packages:
              if reponame == 'msys2':
                sys.stdout.write('\t- {}\n'.format(re.sub('^mingw-w64-(i686|x86_64)-', '', alt_pkg)))
              else:
                sys.stdout.write('\t- {}\n'.format(re.sub('^mingw(32|64)-', '', alt_pkg)))
        else:
            sys.stdout.write('"{}" not found in any package name.\n'.format(keyword))
        if options.list_files:
            alt_packages = search_packages(keyword, options.arch, options.srcpkg, options.list_files)
            if len(alt_packages) > 0:
                sys.stdout.write('The following packages have files matching the search "{}":\n'.format(keyword))
                for alt_pkg in alt_packages:
                  if reponame == 'msys2':
                    sys.stdout.write('\t- {}\n'.format(re.sub('^mingw-w64-(i686|x86_64)-', '', alt_pkg)))
                  else:
                    sys.stdout.write('\t- {}\n'.format(re.sub('^mingw(32|64)-', '', alt_pkg)))
    sys.exit(os.EX_OK)

  if options.list_files:
    if (len(packages) == 0):
        logging.error('Please provide at least one package.\n')
        sys.exit(os.EX_USAGE)
    if options.srcpkg:
        package_type = 'Source package'
    else:
        package_type = 'Package'
    for package in packages:
        (real_name, file_list) = get_package_files (package, reponame, options)
        if file_list is None:
            sys.stderr.write('{} "{}" unknown.\n'.format(package_type, package))
            alt_packages = search_packages(package, options.arch, options.srcpkg)
            if len(alt_packages) > 0:
                logging.error('\tDid you mean:')
                for alt_pkg in alt_packages:
                    logging.error('\t- {}'.format(re.sub('^mingw(32|64)-', '', alt_pkg)))
        else:
            sys.stdout.write('{} "{}":\n'.format(package_type, real_name))
            for f in file_list:
                if f['type'] == 'dir':
                    # TODO: different color?
                    sys.stdout.write('\t{} (directory)\n'.format(f['path']))
                else:
                    sys.stdout.write('\t{}\n'.format(f['path']))
    sys.exit(os.EX_OK)

  if options.info:
    if (len(packages) == 0):
        logging.error('Please provide at least one package.\n')
        sys.exit(os.EX_USAGE)
    if options.srcpkg:
        package_type = 'Source package'
    else:
        package_type = 'Package'
    for pkg in packages:
        package = _findPackage(pkg, options.arch, options.srcpkg)
        if package is None:
            sys.stderr.write('{} "{}" unknown.\n'.format(package_type, pkg))
            alt_packages = search_packages(pkg, options.arch, options.srcpkg)
            if len(alt_packages) > 0:
                logging.error('\tDid you mean:')
                for alt_pkg in alt_packages:
                    logging.error('\t- {}'.format(re.sub('^mingw(32|64)-', '', alt_pkg)))
            continue
        sys.stdout.write('{} "{}":\n'.format(package_type, package['name']))
        if package['summary'] is not None:
            sys.stdout.write('\tSummary: {}\n'.format(package['summary']))
        sys.stdout.write('\tProject URL: {}\n'.format(package['project_url']))
        if 'packager_url' in package and package['packager_url'] is not None:
            sys.stdout.write('\tPackager URL: {}\n'.format(package['packager_url']))
        if package['url'] is not None:
            sys.stdout.write('\tPackage URL: {}\n'.format(package['url']))
        sys.stdout.write('\tVersion: {} (release: {} - epoch: {})\n'.format(package['version']['ver'],
                                                                            package['version']['rel'],
                                                                            package['version']['epoch']))
        description = re.sub(r'\n', "\n\t             ", package['description'])
        sys.stdout.write('\tDescription: {}\n'.format(description))
    sys.exit(os.EX_OK)

  if options.uninstall:
    if (len(packages) == 0):
        logging.error('Please provide at least one package to uninstall.\n')
        sys.exit(os.EX_USAGE)
    if options.srcpkg:
        package_type = 'Source package'
    else:
        package_type = 'Package'
    file_lists = {}
    for package in packages:
        (real_name, file_list) = get_package_files (package, reponame, options)
        if file_list is None:
            sys.stderr.write('{} "{}" unknown.\n'.format(package_type, package))
            alt_packages = search_packages(package, options.arch, options.srcpkg)
            if len(alt_packages) > 0:
                logging.error('\tDid you mean:')
                for alt_pkg in alt_packages:
                    logging.error('\t- {}'.format(re.sub('^mingw(32|64)-', '', alt_pkg)))
        else:
            file_lists[package] = (real_name, file_list)
    # Do we still have a positive number of packages?
    if (len(file_lists) > 0):
        try:
          with open(installed_packages_file) as f:
            installed_packages = [package.rstrip('\n') for package in f.readlines()]
        except FileNotFoundError:
          installed_packages = []

        sys.stdout.write('Crossroad will uninstall the following packages: {}\nin'.format(" ".join(file_lists)))
        try:
          for i in range(5, 0, -1):
              sys.stdout.write(' {}'.format(i))
              sys.stdout.flush()
              time.sleep(1)
        except KeyboardInterrupt:
          sys.stderr.write('\nCanceling uninstallation\n')
          sys.exit(os.EX_USAGE)
        sys.stdout.write('...\nUninstalling...\n')
        sys.stdout.flush()
        for package in file_lists:
            (real_name, file_list) = file_lists[package]
            sys.stdout.write('Deleting {} "{}"...\n'.format(package_type, package))
            sys.stdout.flush()
            for f in file_list:
                if f['type'] == 'dir':
                    # Only remove empty directories.
                    # Good thing that's exactly what os.rmdir() does!
                    try:
                        os.rmdir (f['path'])
                    except OSError:
                        # Probably non empty.
                        pass
                else:
                    try:
                        os.unlink (f['path'])
                    except FileNotFoundError:
                        # Let's just ignore already removed files.
                        pass
            # Finally I deleted any cached rpm and cpio.
            for f in os.listdir(_packageCacheDirectory):
                if f[:len(real_name)] == real_name:
                    os.unlink(os.path.join(_packageCacheDirectory, f))
            for f in os.listdir(_extractedCacheDirectory):
                if f[:len(real_name)] == real_name:
                    os.unlink(os.path.join(_extractedCacheDirectory, f))
            try:
              installed_packages.remove(real_name)
            except ValueError:
              # The package was already not in the list.
              pass
        with open(installed_packages_file, 'w') as f:
          f.writelines('{}\n'.format(package) for package in installed_packages)
        sys.exit(os.EX_OK)
    else:
        logging.error('Exiting without uninstalling.')
        sys.exit(os.EX_NOINPUT)

  if options.mask:
    if len(packages) == 0:
        logging.error('Please provide at least one package to mask.\n')
        sys.exit(os.EX_USAGE)
    if options.srcpkg:
        package_type = 'Source package'
    else:
        package_type = 'Package'
    mask_list = {}
    for package in packages:
      (real_name, _) = get_package_files (package, reponame, options)
      if real_name is None:
        sys.stderr.write('{} "{}" unknown.\n'.format(package_type, package))
        alt_packages = search_packages(package, options.arch, options.srcpkg)
        if len(alt_packages) > 0:
          logging.error('\tDid you mean:')
          for alt_pkg in alt_packages:
            logging.error('\t- {}'.format(re.sub('^mingw(32|64)-', '', alt_pkg)))
      else:
        mask_list[package] = real_name

    # Do we still have a positive number of packages?
    if len(mask_list) > 0:
        try:
          with open(masked_packages_file) as f:
            masked_packages = [package.rstrip('\n') for package in f.readlines()]
        except FileNotFoundError:
          masked_packages = []

        for package in mask_list:
          real_name = mask_list[package]
          # I delete any cached rpm and cpio.
          for f in os.listdir(_packageCacheDirectory):
            if f[:len(real_name)] == real_name:
              os.unlink(os.path.join(_packageCacheDirectory, f))
          for f in os.listdir(_extractedCacheDirectory):
            if f[:len(real_name)] == real_name:
              os.unlink(os.path.join(_extractedCacheDirectory, f))
          if real_name in masked_packages:
            sys.stdout.write('Package {} already masked. Skipping.\n'.format(package))
          else:
            masked_packages += [ real_name ]

        with open(masked_packages_file, 'w') as f:
          f.writelines('{}\n'.format(package) for package in masked_packages)

        sys.stdout.write('Crossroad masked the following packages: {}\n'.format(" ".join(mask_list)))
        sys.stdout.flush()
        sys.exit(os.EX_OK)
    else:
        logging.error('Exiting without masking anything.')
        sys.exit(os.EX_NOINPUT)

  if options.unmask:
    if len(packages) == 0:
        logging.error('Please provide at least one package to unmask.\n')
        sys.exit(os.EX_USAGE)
    if options.srcpkg:
        package_type = 'Source package'
    else:
        package_type = 'Package'
    unmask_list = {}
    for package in packages:
      (real_name, _) = get_package_files (package, reponame, options)
      if real_name is None:
        sys.stderr.write('{} "{}" unknown.\n'.format(package_type, package))
        alt_packages = search_packages(package, options.arch, options.srcpkg)
        if len(alt_packages) > 0:
          logging.error('\tDid you mean:')
          for alt_pkg in alt_packages:
            logging.error('\t- {}'.format(re.sub('^mingw(32|64)-', '', alt_pkg)))
      else:
        unmask_list[package] = real_name

    # Do we still have a positive number of packages?
    if len(unmask_list) > 0:
        try:
          with open(masked_packages_file) as f:
            masked_packages = [package.rstrip('\n') for package in f.readlines()]
        except FileNotFoundError:
          masked_packages = []

        for package in unmask_list:
          real_name = unmask_list[package]
          if real_name not in masked_packages:
            sys.stdout.write('Package {} is not masked. Skipping.\n'.format(package))
          else:
            masked_packages.remove(real_name)

        with open(masked_packages_file, 'w') as f:
          f.writelines('{}\n'.format(package) for package in masked_packages)

        sys.stdout.write('Crossroad unmasked the following packages: {}\n'.format(" ".join(unmask_list)))
        sys.stdout.flush()
        sys.exit(os.EX_OK)
    else:
        logging.error('Exiting without masking anything.')
        sys.exit(os.EX_NOINPUT)
  if options.clean:
    CleanExtracted()

  # Before starting actual installation, we must check our
  # tool prerequisites.
  if shutil.which('cpio') is None:
    # cpio is a very base command. It is probably everywhere.
    # Yet better safe than sorry, I check.
    logging.error('The software `cpio` is absent from your PATH. Please install it.')
    sys.exit(os.EX_CANTCREAT)

  if shutil.which('rpm2cpio') is None and shutil.which('7z') is None:
    logging.error('You need either one of the 2 following commands: rpm2cpio or 7z\nPlease install one of them or make sure they are in your PATH.')
    sys.exit(os.EX_CANTCREAT)

  if options.makezip or options.metadata:
    package = _findPackage(args[0], options.arch, options.srcpkg)
    if package == None:
      logging.error('Package not found:\n\t%s' % args[0])
      alt_packages = search_packages(args[0], options.arch, options.srcpkg)
      if len(alt_packages) > 0:
          logging.error('Did you mean:')
          for alt_pkg in alt_packages:
              logging.error('\t- {}'.format(re.sub('^mingw(32|64)-', '', alt_pkg)))
      sys.exit(os.EX_UNAVAILABLE)
    packageBasename = re.sub('^mingw(32|64)-|\\.noarch|\\.rpm$', '', package['filename'])

  try:
    with open(installed_packages_file) as f:
      installed_packages = [package.rstrip('\n') for package in f.readlines()]
  except FileNotFoundError:
    installed_packages = []
  try:
    with open(masked_packages_file) as f:
      masked_packages = [package.rstrip('\n') for package in f.readlines()]
  except FileNotFoundError:
    masked_packages = []
  try:
    (packages, package_files) = packagesDownload(packages, options.arch,
                                                 installed_packages,
                                                 masked_packages,
                                                 options.withdeps,
                                                 options.srcpkg,
                                                 options.nocache,
                                                 options.force_install)
  except:
    logging.error('Package download failed. Installation canceled.')
    sys.exit(os.EX_UNAVAILABLE)

  if len(package_files) == 0:
    # An empty package list is not an error (packagesDownload() would
    # exit directly the program upon error). It probably just means all
    # packages were already installed.
    logging.warning('Nothing to do.')
    sys.exit(os.EX_OK)

  CleanExtracted()
  if not packagesExtract(package_files, options.srcpkg):
    logging.error('A package failed to extract. Please report a bug.')
    sys.exit(os.EX_CANTCREAT)

  extracted_prefix = GetBaseDirectory(reponame, options.arch)
  if extracted_prefix is None:
    logging.error('Unexpected error: files were not extracted. Please report a bug.')
    sys.exit(os.EX_CANTCREAT)
  sys.stdout.write('Installing...\n')
  sys.stdout.flush()
  move_files(reponame, options.arch, extracted_prefix, prefix)
  sys.stdout.write('Fixing symlinks...\n')
  sys.stdout.flush()
  for package in packages:
      fix_package_symlinks (package, reponame, options)
  sys.stdout.write('Make binaries executable...\n')
  sys.stdout.flush()
  SetExecutableBit()
  sys.stdout.write('All installations done!\n')
  sys.stdout.flush()

  installed_packages += packages
  installed_packages = list(set(installed_packages))
  with open(installed_packages_file, 'w') as f:
    f.writelines('{}\n'.format(package) for package in installed_packages)

  if options.metadata:
    cleanup = lambda n: re.sub('^mingw(?:32|64)-(.*)', '\\1', re.sub('^mingw(?:32|64)[(](.*)[)]', '\\1', n))
    with open(os.path.join(prefix, packageBasename + '.metadata'), 'w') as m:
      for packageFilename in sorted(package_files):
        package = [p for p in _packages if p['filename'] == packageFilename][0]
        m.writelines(['provides:%s\r\n' % cleanup(p) for p in package['provides']])
        m.writelines(['requires:%s\r\n' % cleanup(r) for r in package['requires']])

  if options.makezip:
    packagezip = zipfile.ZipFile(packageBasename + '.zip', 'w', compression=zipfile.ZIP_DEFLATED)
    for root, dirs, files in os.walk(prefix):
      for filename in files:
        fullname = os.path.join(root, filename)
        packagezip.write(fullname, fullname.replace(prefix, ''))
    packagezip.close() #3.2: use with

  if options.clean:
    CleanExtracted()

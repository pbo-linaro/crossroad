#!/usr/bin/python3
#
# Copyright (C) Maarten Bosmans 2011
# Copyright (C) Jehan 2013
#
# The contents of this file are subject to the Mozilla Public License Version 1.1; you may not use this file except in
# compliance with the License. You may obtain a copy of the License at http://www.mozilla.org/MPL/

from urllib.request import urlretrieve, urlopen
import logging
import os.path
import sys
import shutil
import re
import zipfile
import time
import mimetypes
import subprocess
import glob

# XXX 7z dependency!
# TODO Jehan: make possibility to research amongst packages, and see version before installing.
# Also full list visible?

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

_packageCacheDirectory = os.path.join(xdg_cache_home, 'crossroad', 'package')
_repositoryCacheDirectory = os.path.join(xdg_cache_home, 'crossroad', 'repository')
_extractedCacheDirectory = os.path.join(xdg_cache_home, 'crossroad', 'extracted')
_extractedFilesDirectory = os.path.join(xdg_cache_home, 'crossroad', 'prefix')

def get_package_files (package, options):
    '''
    Research and return the list of files for a package name.
    '''
    filelist = None
    real_name = None
    if options.srcpkg:
        filelists = _package_src_filelists
    else:
        filelists = _package_filelists
    try:
        real_name = package
        file_list = filelists[package]
    except KeyError:
        if options.project == 'windows:mingw:win64':
            try:
                real_name = 'mingw64-' + package
                file_list = filelists[real_name]
            except KeyError:
                real_name = None
                file_list = None
        if file_list is None:
            # There are some 32-bit package in the 64-bit list.
            try:
                real_name = 'mingw32-' + package
                file_list = filelists[real_name]
            except KeyError:
                real_name = None
                file_list = None
    if file_list is not None:
        for f in file_list:
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

def fix_package_symlinks (package, options):
    (real_name, file_list) = get_package_files (package, options)
    if file_list is not None:
        for f in file_list:
            fix_symlink (f['path'])

def OpenRepository(repositoryLocation):
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
        logging.warning('Dowloading repository data')
        with urlopen(repositoryLocation + primary_url, timeout = 5.0) as primaryGzFile:
          import io, gzip
          primaryGzString = io.BytesIO(primaryGzFile.read()) #3.2: use gzip.decompress
          with gzip.GzipFile(fileobj=primaryGzString) as primaryGzipFile:
            with open(primary_filename, 'wb') as primaryFile:
              primaryFile.writelines(primaryGzipFile)
      # Also download the filelist.
      filelist_filename = os.path.join(_repositoryCacheDirectory, os.path.splitext(os.path.basename(filelist_url))[0])
      if not os.path.exists(filelist_filename):
        logging.warning('Dowloading repository file list')
        with urlopen(repositoryLocation + filelist_url, timeout = 5.0) as GzFile:
          import io, gzip
          GzString = io.BytesIO(GzFile.read()) #3.2: use gzip.decompress
          with gzip.GzipFile(fileobj=GzString) as primaryGzipFile:
            with open(filelist_filename, 'wb') as filelist_file:
              filelist_file.writelines(primaryGzipFile)
  except:
    raise
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
      'version': {'epoch': p.find('{%s}version'%xmlns).get('epoch'),
                  'ver': p.find('{%s}version'%xmlns).get('ver'),
                  'rel': p.find('{%s}version'%xmlns).get('rel')},
      #'license': p.find('{%s}location/{%s}format/{%s}license'%(xmlns, xmlns, rpmns)).text,
      'buildtime': int(p.find('{%s}time'%xmlns).get('build')),
      'url': repositoryLocation + p.find('{%s}location'%xmlns).get('href'),
      'filename': os.path.basename(p.find('{%s}location'%xmlns).get('href')),
      'checksum': {'type': p.find('{%s}checksum'%xmlns).get('type'),
                   'sum': p.find('{%s}checksum'%xmlns).text},
      'provides': {provides.attrib['name'] for provides in p.findall('{%s}format/{%s}provides/{%s}entry'%(xmlns,rpmns,rpmns))},
      'requires': {req.attrib['name'] for req in p.findall('{%s}format/{%s}requires/{%s}entry'%(xmlns,rpmns,rpmns))}
    } for p in elements.findall('{%s}package'%xmlns)]
  # Package's file lists.
  elements = xmlparse(filelist_filename)
  xmlns = 'http://linux.duke.edu/metadata/filelists'
  _package_filelists = {
      p.get('name') : [
        {'type': f.get('type', default='file'), 'path': f.text} for f in p.findall('{%s}file'%xmlns)
    ] for p in elements.findall('{%s}package'%xmlns) if p.get('arch') == 'noarch'}
  _package_src_filelists = {
      p.get('name') : [
        {'type': f.get('type', default='file'), 'path': f.text} for f in p.findall('{%s}file'%xmlns)
    ] for p in elements.findall('{%s}package'%xmlns) if p.get('arch') == 'src'}

def _findPackage(packageName, srcpkg=False):
  filter_func = lambda p: (p['name'] == packageName or p['filename'] == packageName) and p['arch'] == ('src' if srcpkg else 'noarch')
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
    providers = {p['name'] for p in _packages if requirement in p['provides']}
    if len(providers & packageNames) == 0:
      if len(providers) == 0:
        logging.error('Package %s requires %s, not provided by any package', package['name'], requirement)
      else:
        logging.warning('Package %s requires %s, provided by: %s', package['name'], requirement, ','.join(providers))
        allProviders.add(providers.pop())
  return allProviders

def packagesDownload(packageNames, withDependencies = False, srcpkg = False, nocache = False):
  from fnmatch import fnmatchcase
  packageNames_new = {pn for pn in packageNames if pn.endswith('.rpm')}
  for packageName in packageNames - packageNames_new:
    matchedpackages = {p['name'] for p in _packages if fnmatchcase(p['name'].replace('mingw32-', '').replace('mingw64-', ''), packageName) and p['arch'] == ('src' if srcpkg else 'noarch')}
    packageNames_new |= matchedpackages if len(matchedpackages) > 0 else {packageName}
  packageNames = list(packageNames_new)
  allPackageNames = set(packageNames)

  packageFilenames = []
  while len(packageNames) > 0:
    packName = packageNames.pop()
    package = _findPackage(packName, srcpkg)
    if package == None:
      logging.error('Package %s not found', packName)
      continue
    dependencies = _checkPackageRequirements(package, allPackageNames)
    if withDependencies and len(dependencies) > 0:
      packageNames.extend(dependencies)
      allPackageNames |= dependencies
    if packName[-6:] == '-devel':
        logging.warning('{} is a devel package. Adding {}'.format(packName, packName[:-6]))
        packageNames.append(packName[:-6])
        allPackageNames.add(packName[:-6])
    localFilenameFull = os.path.join(_packageCacheDirectory, package['filename'])
    if nocache or not os.path.exists(localFilenameFull):
      logging.warning('Downloading %s', package['filename'])
      urlretrieve(package['url'], localFilenameFull)
    else:
      logging.warning('Using cached package %s', localFilenameFull)
    packageFilenames.append(package['filename'])
  return (allPackageNames, packageFilenames)

def _extractFile(filename, output_dir=_extractedCacheDirectory):
  try:
    with open('7z.log', 'w') as logfile:
      if filename[-5:] == '.cpio':
        # 7z loses links and I can't find an option to change this behavior.
        # So I use the cpio command for cpio files, even though it might create broken links.
        cwd = os.getcwd()
        os.chdir (output_dir)
        subprocess.check_call('cpio -i --make-directories <' + filename, stderr=logfile, stdout=logfile, shell = True)
        os.chdir (cwd)
      else:
        subprocess.check_call(['7z', 'x', '-o'+output_dir, '-y', filename], stderr=logfile, stdout=logfile)
    os.remove('7z.log')
  except:
    logging.error('Failed to extract %s', filename)

def GetBaseDirectory(project):
  if project == 'windows:mingw:win32' and os.path.exists(os.path.join(_extractedFilesDirectory, 'usr/i686-w64-mingw32/sys-root/mingw')):
    return os.path.join(_extractedFilesDirectory, 'usr/i686-w64-mingw32/sys-root/mingw')
  elif project == 'windows:mingw:win64' and os.path.exists(os.path.join(_extractedFilesDirectory, 'usr/x86_64-w64-mingw32/sys-root/mingw')):
    return os.path.join(_extractedFilesDirectory, 'usr/x86_64-w64-mingw32/sys-root/mingw')
  return _extractedFilesDirectory

def packagesExtract(packageFilenames, srcpkg=False):
  for packageFilename in packageFilenames :
    logging.warning('Extracting %s', packageFilename)
    cpioFilename = os.path.join(_extractedCacheDirectory, os.path.splitext(packageFilename)[0] + '.cpio')
    if not os.path.exists(cpioFilename):
      _extractFile(os.path.join(_packageCacheDirectory, packageFilename))
    if srcpkg:
      _extractFile(cpioFilename, os.path.join(_extractedFilesDirectory, os.path.splitext(packageFilename)[0]))
    else:
      _extractFile(cpioFilename, _extractedFilesDirectory)

def move_files(from_file, to_file):
    if os.path.isdir(from_file):
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
            move_files(os.path.join(from_file, f), os.path.join(to_file, f))
    else:
        if to_file[-3:] == '.pc':
            try:
                fd = open(from_file, 'r')
                contents = fd.read()
                fd.close()
                contents = re.sub(r'^prefix=.*$', 'prefix=' + prefix, contents, count=0, flags=re.MULTILINE)
            except IOError:
                sys.stderr.write('File "{}" could not be read.\n'.format(from_file))
                sys.exit(os.EX_CANTCREAT)
            try:
                # XXX shouldn't I os.unlink it first, just in case it does exist?
                fd = open(to_file, 'w')
                fd.write(contents)
                fd.close()
            except IOError:
                sys.stderr.write('File {} cannot be written.'.format(to_file))
                sys.exit(os.EX_CANTCREAT)
        elif (mimetypes.guess_type(from_file)[0] is not None and mimetypes.guess_type(from_file)[0][:5] == 'text/') or \
             subprocess.check_output(['mimetype', '-b', from_file], universal_newlines=True)[:5] == 'text/':
            # I had the case with "bin/gdbus-codegen" which has the prefix inside the script.
            # mimetypes python module would not work because it only relies on extension.
            # Use mimetype command if possible instead.
            # XXX should I also want to check binary files?
            try:
                fd = open(from_file, 'r')
                contents = fd.read()
                fd.close()
                contents = re.sub(r'/usr/[^/]+-mingw32/sys-root/mingw', prefix, contents, count=0, flags=re.MULTILINE)
            except (IOError, UnicodeDecodeError):
                #sys.stderr.write('File "{}" could not be read.\n'.format(from_file))
                #sys.exit(os.EX_CANTCREAT)
                # May fail if the file encoding is problematic for instance.
                # When this happens, just bypass the contents check and move the file.
                shutil.move(from_file, to_file)
                return
            try:
                # XXX shouldn't I os.unlink it first, just in case it does exist?
                fd = open(to_file, 'w')
                fd.write(contents)
                fd.close()
            except IOError:
                #sys.stderr.write('File {} cannot be written.'.format(to_file))
                #sys.exit(os.EX_CANTCREAT)
                shutil.move(from_file, to_file)
        elif to_file[-7:] == '-config':
            try:
                fd = open(from_file, 'r')
                contents = fd.read()
                fd.close()
                contents = re.sub(r'/usr/[^/]+-mingw32/sys-root/mingw', prefix, contents, count=0, flags=re.MULTILINE)
            except IOError:
                #sys.stderr.write('File "{}" could not be read.\n'.format(from_file))
                #sys.exit(os.EX_CANTCREAT)
                shutil.move(from_file, to_file)
                return
            try:
                # XXX shouldn't I os.unlink it first, just in case it does exist?
                fd = open(to_file, 'w')
                fd.write(contents)
                fd.close()
            except IOError:
                #sys.stderr.write('File {} cannot be written.'.format(to_file))
                #sys.exit(os.EX_CANTCREAT)
                shutil.move(from_file, to_file)
        else:
            shutil.move(from_file, to_file)

def CleanExtracted():
    shutil.rmtree(os.path.join(_extractedFilesDirectory, 'usr'), True)

def SetExecutableBit():
    # set executable bit on anything in bin/
    bin_dir = os.path.join(prefix, 'bin')
    if os.path.isdir(bin_dir):
        for f in os.listdir(bin_dir):
            os.chmod(os.path.join(bin_dir, f), 0o755)
    # set executable bit on libraries and executables whatever the path.
    for root, dirs, files in os.walk(prefix):
        for filename in {f for f in files if f.endswith('.dll') or f.endswith('.exe')} | set(dirs):
            os.chmod(os.path.join(root, filename), 0o755)

def GetOptions():
  from optparse import OptionParser, OptionGroup #3.2: use argparse

  parser = OptionParser(usage="usage: %prog [options] packages",
                        description="Easy download of RPM packages for Windows.")

  # Options specifiying download repository
  default_project = "windows:mingw:win32"
  default_repository = "openSUSE_11.4"
  default_repo_url = "http://download.opensuse.org/repositories/PROJECT/REPOSITORY/"
  repoOptions = OptionGroup(parser, "Specify download repository")
  repoOptions.add_option("-p", "--project", dest="project", default=default_project,
                         metavar="PROJECT", help="Download from PROJECT [%default]")
  repoOptions.add_option("-r", "--repository", dest="repository", default=default_repository,
                         metavar="REPOSITORY", help="Download from REPOSITORY [%default]")
  repoOptions.add_option("-u", "--repo-url", dest="repo_url", default=default_repo_url,
                         metavar="URL", help="Download packages from URL (overrides PROJECT and REPOSITORY options) [%default]")
  parser.add_option_group(repoOptions)

  # Package selection options
  parser.set_defaults(withdeps=False)
  packageOptions = OptionGroup(parser, "Package selection")
  packageOptions.add_option("--deps", action="store_true", dest="withdeps", help="Download dependencies")
  packageOptions.add_option("--no-deps", action="store_false", dest="withdeps", help="Do not download dependencies [default]")
  packageOptions.add_option("--src", action="store_true", dest="srcpkg", default=False, help="Download source instead of noarch package")
  packageOptions.add_option("--nocache", action="store_true", dest="nocache", default=False,
                            help="Force package download even if it is in cache.")
  packageOptions.add_option("--list-files", action="store_true", dest="list_files", default=False, help="Only list the files of a package")
  packageOptions.add_option("--info", action="store_true", dest="info", default=False, help="Output information about a package")
  packageOptions.add_option("--uninstall", action="store_true", dest="uninstall", default=False, help="Uninstall the list of packages")
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

  if len(args) == 0:
    parser.print_help(file=sys.stderr)
    sys.exit(1)

  return (options, args)

if __name__ == "__main__":
  (options, args) = GetOptions()
  packages = set(args)
  logging.basicConfig(level=(logging.WARNING if options.verbose else logging.ERROR), format='%(message)s', stream=sys.stderr)

  # Open repository
  repository = options.repo_url.replace("PROJECT", options.project.replace(':', ':/')).replace("REPOSITORY", options.repository)
  try:
    OpenRepository(repository)
  except Exception as e:
    sys.exit('Error opening repository:\n\t%s\n\t%s' % (repository, e))

  if options.list_files:
    if (len(packages) == 0):
        logging.error('Please provide at least one package.\n')
        sys.exit(os.EX_USAGE)
    if options.srcpkg:
        package_type = 'Source package'
    else:
        package_type = 'Package'
    for package in packages:
        (real_name, file_list) = get_package_files (package, options)
        if file_list is None:
            sys.stderr.write('{} "{}" unknown.\n'.format(package_type, package))
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
        package = _findPackage(pkg, options.srcpkg)
        if package is None:
            if options.project == 'windows:mingw:win64':
                package = _findPackage("mingw64-" + pkg, options.srcpkg)
            elif options.project == 'windows:mingw:win32':
                package = _findPackage("mingw32-" + pkg, options.srcpkg)
            if package is None:
                sys.stderr.write('{} "{}" unknown.\n'.format(package_type, pkg))
                continue
        sys.stdout.write('{} "{}":\n'.format(package_type, package['name']))
        sys.stdout.write('\tSummary: {}\n'.format(package['summary']))
        sys.stdout.write('\tProject URL: {}\n'.format(package['project_url']))
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
    sys.stdout.write('Crossroad will uninstall the following packages: {}\nin'.format(" ".join(packages)))
    for i in range(5, 0, -1):
        sys.stdout.write(' {}'.format(i))
        sys.stdout.flush()
        time.sleep(1)
    sys.stdout.write('...\nUninstalling...\n')
    sys.stdout.flush()
    for package in packages:
        (real_name, file_list) = get_package_files (package, options)
        if file_list is None:
            sys.stderr.write('{} "{}" unknown.\n'.format(package_type, package))
        else:
            sys.stdout.write('Deleting {} "{}"...\n'.format(package_type, real_name))
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
    sys.exit(os.EX_OK)

  if options.clean:
    CleanExtracted()

  if options.makezip or options.metadata:
    package = _findPackage(args[0]) #if args[0].endswith('.rpm') 
    if package == None: package = _findPackage("mingw32-"+args[0], options.srcpkg)
    if package == None: package = _findPackage("mingw64-"+args[0], options.srcpkg)
    if package == None:
      sys.exit('Package not found:\n\t%s' % args[0])
    packageBasename = re.sub('^mingw(32|64)-|\\.noarch|\\.rpm$', '', package['filename'])

  (packages, packages_rpm) = packagesDownload(packages, options.withdeps, options.srcpkg, options.nocache)

  packagesExtract(packages_rpm, options.srcpkg)
  extracted_prefix = GetBaseDirectory(options.project)
  move_files(extracted_prefix, prefix)
  logging.warning ('Fixing symlinks')
  sys.stdout.flush()
  for package in packages:
      fix_package_symlinks (package, options)
  SetExecutableBit()

  if options.metadata:
    cleanup = lambda n: re.sub('^mingw(?:32|64)-(.*)', '\\1', re.sub('^mingw(?:32|64)[(](.*)[)]', '\\1', n))
    with open(os.path.join(prefix, packageBasename + '.metadata'), 'w') as m:
      for packageFilename in sorted(packages_rpm):
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


# -*- coding: utf-8 -*-
"""
    Copyright (C) 2010 j48antialias
    Copyright (C) 2012-2013 Garrett Brown
    Copyright (C) 2019 Stefano Gottardo - @CastagnaIT
    Repository generator

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSE.txt for more information.
"""
# Compatible only with Python 3
# Based on code by j48antialias:
# https://anarchintosh-projects.googlecode.com/files/addons_xml_generator.py

import os
import re
from zipfile import ZipFile, ZIP_DEFLATED
from mako.template import Template  # How install: python -m pip install mako

PYTHON_COMPILED_EXT = ['.pyc', '.pyo', '.pyd']

# --- GENERATOR CONFIGURATION ---
# > ADDONS_ABSOLUTE_PATH:
# - If 'None': all add-ons contained in 'packages' sub-folder (where there is generator.py) will be taken into account
# - If specified: all add-ons within that path will be taken into account
ADDONS_ABSOLUTE_PATH = 'D:\\GIT'

# > GENERATE_ONLY_ADDONS:
# - If 'None': all add-ons contained in the path will be taken into account
# - If specified: only the mentioned add-ons folders will be taken into account
GENERATE_ONLY_ADDONS = ['plugin.video.netflix']

# > Files and folders to be excluded per add-on, warning: does not take into account absolute paths of sub-folders
ZIP_EXCLUDED_FILES = {'plugin.video.netflix': ['tox.ini']}
ZIP_EXCLUDED_DIRS = {'plugin.video.netflix': ['test', 'docs', '__pycache__']}

ZIP_FOLDER = 'zip'  # Folder that contains all generated add-ons zips


def get_addons_main_path():
    return ADDONS_ABSOLUTE_PATH if ADDONS_ABSOLUTE_PATH else os.path.join(os.getcwd(), 'packages')


def get_addons_folders():
    """Get add-ons folder names"""
    dir_list = sorted(os.listdir(get_addons_main_path()))
    addons_list = []
    for item in dir_list:
        full_path = os.path.join(get_addons_main_path(), item)
        # Check if it is a real directory
        if not os.path.isdir(full_path):
            continue
        # Filter by selected add-ons
        if GENERATE_ONLY_ADDONS and item not in GENERATE_ONLY_ADDONS:
            continue
        # Add only if addon.xml exists
        addon_xml_path = os.path.join(full_path, 'addon.xml')
        if os.path.exists(addon_xml_path):
            addons_list += [full_path]
    return addons_list


def generate_zip_filename(addon_folder_name, addon_version):
    # If this format will be modified is needed to fix also: _file_compare_version()
    return addon_folder_name + '-' + addon_version + '.zip'


class GeneratorXML:
    """
        Generates a new addons.xml file from each addons addon.xml file
        and a new addons.xml.md5 hash file. Must be run from the root of
        the checked-out repo. Only handles single depth folder structure.
    """

    def __init__(self, num_of_previous_ver=0):
        """
        num_of_previous_ver: include the possibility to the users to rollback to previous version with Kodi interface,
        """
        self.generate_addons_file(num_of_previous_ver)
        self.generate_md5_file()
        print("### Finished updating addons xml and md5 files ###")

    def generate_addons_file(self, num_of_previous_ver=0):
        safe_excluded_folders = [ZIP_FOLDER, 'temp', 'packages']

        # Initial XML directive
        addons_xml = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<addons>\n'

        # Add each addon.xml file
        for addon in get_addons_folders():
            # Skip the safe excluded folders
            if addon in safe_excluded_folders:
                continue

            addon_folder_name = os.path.basename(addon)
            addon_xml_path = os.path.join(addon, 'addon.xml')

            try:
                # Get xml content and split lines for stripping
                addon_xml = open(addon_xml_path, 'r', encoding='utf-8').read()
                # Add the addons.xml text to the main xml
                addons_xml += self._format_xml_lines(addon_xml.splitlines())

                if num_of_previous_ver:
                    # Read current add-on version
                    current_addon_version = re.findall(r'version=\"(.*?[0-9])\"', addon_xml)[1]
                    # It is mandatory to check if a zip of the current version has already been generated before
                    zip_filename = generate_zip_filename(addon_folder_name, current_addon_version)
                    if os.path.exists(os.path.join(ZIP_FOLDER, addon_folder_name, zip_filename)):
                        os.remove(os.path.join(ZIP_FOLDER, addon_folder_name, zip_filename))
                    prev_xmls_ver = GeneratorZIP().get_previous_addon_xml_ver(addon_folder_name, num_of_previous_ver)
                    for prev_xml in prev_xmls_ver:
                        addons_xml += self._format_xml_lines(prev_xml.splitlines())

                print(addon_xml_path + ' Success!')
            except Exception as exc:
                # missing or poorly formatted addon.xml
                print(addon_xml_path + ' Fail!')
                print('Exception: {}'.format(exc))
                continue
        # Add closing tag
        addons_xml = addons_xml.strip() + '\n</addons>\n'
        # Save the main XML file
        self._save_file(addons_xml.encode('utf-8'), file='addons.xml')

    def _format_xml_lines(self, xml_lines):
        """Format and clean the rows of the file"""
        xml_formatted = ''
        for line in xml_lines:
            # Skip encoding format line
            if line.find('<?xml') >= 0:
                continue
            # Add the row
            xml_formatted += '  ' + line.rstrip() + '\n'
        return xml_formatted.rstrip() + '\n\n'

    def generate_md5_file(self):
        """Create a new md5 hash"""
        import hashlib
        hexdigest = hashlib.md5(open('addons.xml', 'r', encoding='utf-8').read().encode('utf-8')).hexdigest()

        try:
            self._save_file(hexdigest.encode('utf-8'), file='addons.xml.md5')
        except Exception as exc:
            print('An error occurred creating addons.xml.md5 file!\n{}'.format(exc))

    def _save_file(self, data, file):
        """Write data to the file"""
        try:
            open(file, "wb").write(data)
        except Exception as exc:
            print('An error occurred saving {} file!\n{}'.format(file, exc))


class GeneratorZIP:
    """Generate add-ons ZIP Files"""

    def __init__(self):
        pass

    index_template = """<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 3.2 Final//EN">
<html>
  <head>
     <title>Index of</title>
  </head>
  <body>
    <h1>${header}</h1>
    <table>
    % for name in names:
      % if '.zip' in name or '.md5' in name or '.xml' in name or '.md' in name or '.txt' in name:
      <tr><td><a href="${name}">${name}</a></td></tr>
      % else:
      <tr><td><a href="${name}/">${name}</a></td></tr>
      % endif
    % endfor
    </table>
  </body>
</html>
"""

    def get_dir_items(self, path):
        """Get filtered items of a folder"""
        included_files = ['.md5', 'README.md', '.xml', '.zip']
        if not path:
            path = os.getcwd()
        dir_list = sorted(os.listdir(path))
        folder_items = []
        for item in dir_list:
            if item.startswith('.'):
                continue
            is_dir = os.path.isdir(os.path.join(path, item))
            if is_dir:
                folder_items += [item]
            elif any(item.find(included_file) != -1 for included_file in included_files):
                folder_items += [item]
        return folder_items

    def _file_compare_version(self, item1, item2):
        # This file version compare accept this file name format: some_name-0.15.11.zip
        if '-' in item1 and '-' in item2:
            version1 = item1.split('-')[1][0:-4]
            version2 = item2.split('-')[1][0:-4]
            if list(map(int, version1.split('.'))) < list(map(int, version2.split('.'))):
                return -1
            else:
                return 1
        return 0

    def get_previous_addon_xml_ver(self, addon_folder_name, num_of_previous_ver):
        addon_xmls = []
        index = 0
        from functools import cmp_to_key
        folder_items = sorted(os.listdir(os.path.join(ZIP_FOLDER, addon_folder_name)),
                              key=cmp_to_key(self._file_compare_version), reverse=True)
        for item in folder_items:
            if index == num_of_previous_ver:
                break
            if item.endswith('.zip'):
                with ZipFile(os.path.join(ZIP_FOLDER, addon_folder_name, item), mode='r') as zip_obj:
                    addon_xmls += [zip_obj.read(addon_folder_name + '/addon.xml').decode('utf-8')]
                index += 1
        print('Added to addons.xml also {} of previous {} add-on version'.format(index, addon_folder_name))
        return addon_xmls

    def generate_html_index(self, path):
        if not path:
            path = os.getcwd()
        items_name = self.get_dir_items(path)
        header = os.path.basename(path)
        return Template(self.index_template).render(names=items_name, header=header)

    def generate_zip_files(self, generate_html_indexes=False, delete_py_compiled_files=False):
        if not os.path.exists(ZIP_FOLDER):
            os.makedirs(ZIP_FOLDER)
        for addon in get_addons_folders():
            try:
                addon_folder_name = os.path.basename(addon)
                addon_xml_path = os.path.join(addon, 'addon.xml')
                # Read add-on version
                xml = open(addon_xml_path, 'r', encoding='utf-8').read()
                addon_version = re.findall(r'version=\"(.*?[0-9])\"', xml)[1]

                # Create add-on zip folder
                addon_zip_folder = os.path.join(ZIP_FOLDER, addon_folder_name)
                if not os.path.exists(addon_zip_folder):
                    os.makedirs(addon_zip_folder)

                # Get the excluded directory elements for this addon
                _zip_excluded_files = ZIP_EXCLUDED_FILES.get(addon_folder_name, [])
                _zip_excluded_dirs = ZIP_EXCLUDED_DIRS.get(addon_folder_name, [])

                # Clean original add-on folder from python compiled files
                if delete_py_compiled_files:
                    print('Start cleaning original add-on folder {} from python compiled files'.format(addon))
                    for parent, subfolders, filenames in os.walk(addon):
                        for filename in filenames:
                            filename, file_extension = os.path.splitext(filename)
                            if file_extension in PYTHON_COMPILED_EXT:
                                print('Removing compiled file: {}'.format(os.path.join(parent, filename)))
                                os.remove(os.path.join(parent, filename))
                    print('Cleaning complete.')

                # Create the zip file
                addons_main_path = get_addons_main_path()
                zip_filename = generate_zip_filename(addon_folder_name, addon_version)
                with ZipFile(os.path.join(addon_zip_folder, zip_filename), 'w', ZIP_DEFLATED) as zip_obj:
                    # Iterate over all the files in directory
                    for folder_name, subfolders, filenames in os.walk(addon):
                        # Remove hidden folders
                        subfolders[:] = [d for d in subfolders if not d.startswith('.')]
                        # Remove excluded dirs
                        subfolders[:] = [d for d in subfolders if d not in _zip_excluded_dirs]
                        for filename in filenames:
                            if not delete_py_compiled_files:
                                # Ignore python compiled files
                                _filename, file_extension = os.path.splitext(filename)
                                if file_extension in PYTHON_COMPILED_EXT:
                                    continue
                            # Ignore hidden and excluded files
                            if filename.startswith('.') or filename in _zip_excluded_files:
                                continue
                            # create complete file path of file in directory
                            absname = os.path.abspath(os.path.join(folder_name, filename))
                            arcname = absname[len(addons_main_path) + 1:]
                            # Add file to zip
                            zip_obj.write(absname, arcname)

                if generate_html_indexes:
                    with open(os.path.join(addon_zip_folder, 'index.html'), 'w', encoding='utf-8') as file:
                        file.write(self.generate_html_index(addon_zip_folder))
                print(addon_folder_name + ' (' + addon + ') Success!')
            except Exception as exc:
                import traceback
                print('Exception: {}'.format(exc))
                print(traceback.format_exc())
            print('### Finished zipping ###')

        if generate_html_indexes:
            with open('index.html', 'w', encoding='utf-8') as file:
                file.write(self.generate_html_index(None))
            with open(os.path.join(ZIP_FOLDER, 'index.html'), 'w', encoding='utf-8') as file:
                file.write(self.generate_html_index(ZIP_FOLDER))


if __name__ == "__main__":
    print("Trying to generate addons.xml and addons.md5")
    GeneratorXML(num_of_previous_ver=2)
    print("\r\nTrying to generate zip for each add-on")
    GeneratorZIP().generate_zip_files(generate_html_indexes=True, delete_py_compiled_files=False)

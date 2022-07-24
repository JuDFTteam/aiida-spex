# -*- coding: utf-8 -*-
"""
In this module is the :class:`~aiida_spex.data.spexinp.SpexinpData` class, and methods for SPEX
input manipulation plus methods for extration of AiiDA data structures.
"""
from __future__ import absolute_import
from __future__ import print_function
import os
import re
import six
from lxml import etree

from aiida.orm import Data, Node, load_node
from aiida.common.exceptions import InputValidationError, ValidationError
from aiida.engine.processes.functions import calcfunction as cf

# from aiida_spex.tools.util import replace_tag

# BOHR_A = 0.52917721092

class SpexinpData(Data):
    """
    AiiDA data object representing everything a SPEX calculation needs.

    It is initialized with an absolute path to an ``spex.inp`` file or a
    FolderData node containing ``spex.inp``.
    Other files can also be added that will be copied to the remote machine, where the
    calculation takes place.

    It stores the files in the repository and stores the input parameters of the
    ``spex.inp`` file of SPEX in the database as a python dictionary (as internal attributes).
    When an ``spex.inp`` (name important!) file is added to files.

    # TODO SpexinpData also provides the user with methods to extract AiiDA dataTypes

    Remember that most attributes of AiiDA nodes can not be changed after they
    have been stored in the database! Therefore, you have to use the SpexinpModifier class and its
    methods if you want to change somthing in the ``spex.inp`` file. You will retrieve a new
    SpexinpData that way and start a new calculation from it.
    """

    # search in current folder and search in aiida source code
    # we want to search in the Aiida source directory, get it from python path,
    # maybe better from somewhere else.
    # TODO: don not walk the whole python path, test if dir below is aiida?
    # needs to be improved, schema file is often after new installation not found...
    # installation with pip should always lead to a schema file in the python path, or even specific place

    def __init__(self, **kwargs):
        """
        Initialize a SpexinpData object set the files given
        """
        files = kwargs.pop('files', None)
        node = kwargs.pop('node', None)
        super(SpexinpData, self).__init__(**kwargs)

        search_paths = []

        # Now add also python path maybe will be deactivated
        #if pythonpath is non existent catch error
        try:
            pythonpath = os.environ['PYTHONPATH'].split(':')
        except KeyError:
            pythonpath = []

        for path in pythonpath[:]:
            search_paths.append(path)

        self.set_attribute('_search_paths', search_paths)
        if files:
            if node:
                self.set_files(files, node=node)
            else:
                self.set_files(files)

    @property
    def _search_paths(self):
        """
        A string, which stores the paths to search for  schemafiles
        """
        return self.get_attribute('_search_paths')

    # files
    @property
    def files(self):
        """
        Returns the list of the names of the files stored
        """
        return self.get_attribute('files', [])

    @files.setter
    def files(self, filelist, node=None):
        """
        Add a list of files to SpexinpData.
        Alternative use setter method.

        :param files: list of filepaths or filenames of node is specified
        :param node: a Folder node containing files from the filelist
        """
        for file1 in filelist:
            self.set_file(file1, node=node)

    def set_files(self, files, node=None):
        """
        Add the list of files to the :class:`~aiida_spex.data.spexinp.SpexinpData` instance.
        Can by used as an alternative to the setter.

        :param files: list of abolute filepaths or filenames of node is specified
        :param node: a :class:`~aiida.orm.FolderData` node containing files from the filelist
        """
        for file1 in files:
            self.set_file(file1, node=node)

    def set_file(self, filename, dst_filename=None, node=None):
        """
        Add a file to the :class:`~aiida_fleur.data.fleurinp.SpexinpData` instance.

        :param filename: absolute path to the file or a filename of node is specified
        :param node: a :class:`~aiida.orm.FolderData` node containing the file
        """
        self._add_path(filename, dst_filename=dst_filename, node=node)


    def open(self, key='spex.inp', mode='r'):
        """
        Returns an open file handle to the content of this data node.

        :param key: name of the file to be opened
        :param mode: the mode with which to open the file handle
        :returns: A file handle in read mode
	 """
        return super(SpexinpData, self).open(key, mode=mode)

    def get_content(self, filename='spex.inp'):
        """
        Returns the content of the single file stored for this data node.

        :returns: A string of the file content
        """
        with self.open(key=filename, mode='r') as handle:
            return handle.read()


    def del_file(self, filename):
        """
        Remove a file from SpexinpData instancefind

        :param filename: name of the file to be removed from SpexinpData instance
        """
        # remove from files attr list
        if filename in self.get_attribute('files'):
            try:
                self.get_attribute('files').remove(filename)
                #self._del_attribute(‘filename')
            except AttributeError:
                ## There was no file set
                pass
        # remove from sandbox folder
        if filename in self.list_object_names():#get_folder_list():
            self.delete_object(filename)

    def _add_path(self, file1, dst_filename=None, node=None):
        """
        Add a single file to folder. The destination name can be different.
        ``spex.inp`` is a special case.
        file names are stored in the db, files in the repo.

        """
        #TODO, only certain files should be allowed to be added
        #_list_of_allowed_files = ['spex.inp', 'enpara', 'cdn1', 'sym.out', 'kpts']

        #old_file_list = self.get_folder_list()

        if node:
            if not isinstance(node, Node):
                #try:
                node = load_node(node)
                #except

            if file1 in node.list_object_names():
                file1 = node.open(file1, mode='r')
            else:# throw error? you try to add something that is not there
                raise ValueError("file1 has to be in the specified node")

        if isinstance(file1, six.string_types):
            is_filelike = False

            if not os.path.isabs(file1):
                file1 = os.path.abspath(file1)
                #raise ValueError("Pass an absolute path for file1: {}".format(file1))

            if not os.path.isfile(file1):
                raise ValueError("file1 must exist and must be a single file: {}".format(file1))

            if dst_filename is None:
                final_filename = os.path.split(file1)[1]
            else:
                final_filename = dst_filename
        else:
            is_filelike = True
            final_filename = os.path.basename(file1.name)


        key = final_filename

        old_file_list = self.list_object_names()
        old_files_list = self.get_attribute('files', [])

        if final_filename not in old_file_list:
            old_files_list.append(final_filename)
        else:
            try:
                old_file_list.remove(final_filename)
            except ValueError:
                pass

        if is_filelike:
            self.put_object_from_filelike(file1, key)
            if file1.closed:
                file1 = self.open(file1.name, file1.mode)
            else: #reset reading to 0
                file1.seek(0)
        else:
            self.put_object_from_file(file1, key)

        self.set_attribute('files', old_files_list)

    def _set_inp_dict(self):
        """
        Sets the input_dict from the ``spex.inp`` file attached to SpexinpData

        1. get ``spex.inp``
        2. load ``spex.inp`` file
        3. call inp_to_dict
        4. set input_dict
        """
        from aiida_spex.tools.util import get_inpxml_file_structure, inpxml_todict, clear_xml
        # read spex.inp file
        spexinpfile = self.open(key='spex.inp', mode='r')

        xmlschema_doc = etree.parse(self._schema_file_path)
        xmlschema = etree.XMLSchema(xmlschema_doc)
        parser = etree.XMLParser(attribute_defaults=True)
        #dtd_validation=True

        tree_x = etree.parse(spexinpfile, parser)
        spexinpfile.close()
        # replace XInclude parts to validate against schema
        tree_x = clear_xml(tree_x)

        # check if it validates against the schema
        # TODO validate the input file
        if not xmlschema.validate(tree_x):
            raise InputValidationError("Input file is not validated against the schema.")

        # convert etree into python dictionary
        root = tree_x.getroot()
        inpxml_dict = inpxml_todict(root, inpxmlstructure)
        # set inpxml_dict attribute
        self.set_attribute('inp_dict', inpxml_dict)

    # dict with inp paramters parsed from spex.inp
    @property
    def inp_dict(self):
        """
        Returns the inp_dict (the representation of the ``spex.inp`` file) as it will
        or is stored in the database.
        """
        return self.get_attribute('inp_dict', {})


    # TODO better validation? other files, if has a schema
    def _validate(self):
        """
        A validation method. Checks if an ``spex.inp`` file is in the SpexinpData.
        """
        #from aiida.common.exceptions import ValidationError

        super(SpexinpData, self)._validate()

        if 'spex.inp' in self.files:
            #has_inpxml = True # does nothing so far
            pass
        else:
            raise ValidationError('spex.inp file not in attribute "files". '
                                  'SpexinpData needs to have and spex.inp file!')


    def get_spex_jobs(self):
        '''
        Analyses ``spex.inp`` file to set up a calculation mode. 'jobs' are paths a SPEX
        calculation can take, resulting in different output files.
        This files can be automatically addded to the retrieve_list of the calculation.

        Common jobs are: GW, DIEL, GT, etc,.

        :return: a dictionary containing all possible jobs. A job is activated assigning a
                 non-empty string to the corresponding key.
        '''
        spex_jobs = {'jspins' : '', 'dos' : '', 'band' : '', 'ldau' : '', 'forces' : '',
                       'force_theorem': ''}
        if 'spex.inp' in self.files:
            spex_jobs['jspins'] = self.inp_dict['calculationSetup']['magnetism']['jspins']
            spex_jobs['dos'] = self.inp_dict['output']['dos']#'fleurInput']
            spex_jobs['band'] = self.inp_dict['output']['band']
            spex_jobs['forces'] = self.inp_dict['calculationSetup']['geometryOptimization']['l_f']
            spex_jobs['force_theorem'] = 'forceTheorem' in self.inp_dict
            ldau = False # TODO test if ldau in inp_dict....
            spex_jobs['ldau'] = False
        return spex_jobs


    # Is there a way to give self to calcfunctions?
    @staticmethod
    @cf
    def get_parameterdata(fleurinp):
        """
        This routine returns an AiiDA :class:`~aiida.orm.Dict` type produced from the ``spex.inp``
        file. The returned node can be used for spex as `calc_parameters`.
        This is a calcfunction and keeps the provenance!

        :returns: :class:`~aiida.orm.Dict` node
        """

        return fleurinp.get_parameterdata_ncf()
# -*- coding: utf-8 -*-
###############################################################################
# Copyright (c), Forschungszentrum Jülich GmbH, IAS-1/PGI-1, Germany.         #
#                All rights reserved.                                         #
# This file is part of the AiiDA-SPEX package.                                #
#                                                                             #
# The code is hosted on GitHub at https://github.com/JuDFTteam/aiida-spex     #
# For further information on the license, see the LICENSE.txt file            #
# For further information please visit http://www.flapw.de or                 #
# http://aiida-spex.readthedocs.io/en/develop/                                #
###############################################################################

"""
This module contains the parser for a SPEX calculation.

Please implement file parsing routines that they can be executed from outside
the parser. Makes testing and portability easier. Also without using aiida_classes,
that they might be useful to external tools
"""

import os
from aiida.parsers.parser import Parser
from aiida_spex.calculation.spex import SpexCalculation
from aiida_spex.parsers import SpexOutputParsingError


class SpexParser(Parser):
    """
    This class is the implementation of the Parser class for a SPEX calculation.
    It takes the files recieved from an SPEX calculation and creates AiiDA
    nodes for the Database. Information from the out file is stored in a
    ParameterData node.
    """

    _setting_key = 'parser_options'

    def __init__(self, calc):
        """
        Initialize the instance of SPEXParser
        """
        # check for valid input
        if not isinstance(calc, SpexCalculation):
            raise SpexOutputParsingError(
                "Input calc must be a SpexCalculation")

        # these files should be at least present after success of inpgen
        self._default_files = {calc._OUTPUT_FILE_NAME, calc._INPXML_FILE_NAME}
        self._other_files = {calc._SHELLOUT_FILE_NAME}

        super(SpexParser, self).__init__(calc)

    def parse_with_retrieved(self, retrieved):
        """
        Receives as input a dictionary of the retrieved nodes from an inpgen run.
        Does all the logic here.

        :return: a dictionary of AiiDA nodes for storing in the database.
        """

        successful = True

        # select the folder object
        # Check that the retrieved folder is there
        try:
            out_folder = retrieved[self._calc._get_linkname_retrieved()]
        except KeyError:
            self.logger.error("No retrieved folder found")
            return False, ()

        # check what is inside the folder
        list_of_files = out_folder.get_folder_list()
        self.logger.info("file list {}".format(list_of_files))

        if self._calc._INPXML_FILE_NAME not in list_of_files:
            successful = False
            self.logger.error(
                "XML inp not found '{}'".format(self._calc._INPXML_FILE_NAME))
        else:
            has_xml_inpfile = True

        for file1 in self._default_files:
            if file1 not in list_of_files:
                successful = False
                self.logger.warning(
                    "'{}' file not found in retrived folder, it was probable "
                    "not created by inpgen".format(file1))
        # TODO what about other files?


        new_nodes_list = []
        if self._calc._ERROR_FILE_NAME in list_of_files:
            errorfile = os.path.join(out_folder.get_abs_path('.'),
                                     self._calc._ERROR_FILE_NAME)
            # read
            error_file_lines = ''
            try:
                with open(errorfile, 'r') as efile:
                    error_file_lines = efile.read()# Note: read(),not readlines()
            except IOError:
                self.logger.error(
                    "Failed to open error file: {}.".format(errorfile))
            # if not empty, has_error equals True, parse error.
            if error_file_lines:
                self.logger.error(
                    "The following was written to the error file {} : \n '{}'"
                    "".format(self._calc._ERROR_FILE_NAME, error_file_lines))
                #has_error = True
                successful = False
                return successful, ()

        if has_xml_inpfile:
            # read xmlinp file into an etree
            inpxmlfile = os.path.join(out_folder.get_abs_path('.'),
                                      self._calc._INPXML_FILE_NAME)

            self.logger.info('Bla bla initialized')
            #self.logger.info
            link_name_fleurinp = 'bla'
            # return it to the execmanager
            new_nodes_list.append((link_name_fleurinp, fleurinp_data))

        return successful, new_nodes_list


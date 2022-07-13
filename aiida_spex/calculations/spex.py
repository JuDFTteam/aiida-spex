# -*- coding: utf-8 -*-
###############################################################################
# Copyright (c), Forschungszentrum Jülich GmbH, IAS-1/PGI-1, Germany.         #
#                All rights reserved.                                         #
# This file is part of the AiiDA-SPEX package.                               #
#                                                                             #
# The code is hosted on GitHub at https://github.com/JuDFTteam/aiida-spex     #
# For further information on the license, see the LICENSE.txt file            #
# For further information please visit http://www.flapw.de or                 #
###############################################################################

"""
This file contains a CalcJob that represents SPEX calculation.
"""
from __future__ import absolute_import

import io
import os

import six
from aiida.common.datastructures import CalcInfo, CodeInfo
from aiida.common.exceptions import InputValidationError, UniquenessError
from aiida.common.utils import classproperty
from aiida.engine import CalcJob
from aiida.orm import Dict, RemoteData
from aiida_fleur.calculation.fleur import FleurCalculation


class SpexCalculation(CalcJob):
    """
    Given a DFT result node(or RemoteData), This calculation will retrive and modify the necessary
    files for a SPEX calculation. Prepare and adapt the retrive list and create a
    CalcInfo object for the ExecManager of aiida.
    NOTE: RemoteData or DFT result node must be a result of SPEX workflow implemented in the aiida-fleur plugin
    """

    # Default input and output files
    _INPUT_FILE = "spex.inp"
    _OUTPUT_FILE = "spex.out"

    # these will be shown in AiiDA
    _OUTPUT_FILE_NAME = "spex.out"
    _INPUT_FILE_NAME = "spex.inp"

    # Files needed for the SPEX calculation
    _OUTXML_FILE_NAME = "out.xml"
    _INPXML_FILE_NAME = "inp.xml"
    _SYMXML_FILE_NAME = "sym.xml"
    _ENPARA_FILE_NAME = "enpara"
    # _SYMOUT_FILE_NAME = "sym.out"
    _CDN_HDF5_FILE_NAME = "cdn.hdf"
    _BASIS_FILE_NAME = "basis.hdf"
    _POT_FILE_NAME = "pot.hdf"
    _ECORE_FILE = "ecore"
    _ERROR_FILE_NAME = "out.error"

    # other
    _KPTS_FILE_NAME = "kpts"
    _QPTS_FILE_NAME = "qpts"
    _POT_FILE_NAME = "pot*"
    _POT1_FILE_NAME = "pottot"
    _POT2_FILE_NAME = "potcoul"
    _STRUCTURE_FILE_NAME = "struct.xsf"
    _CDN_LAST_HDF5_FILE_NAME = "cdn_last.hdf"

    # relax (geometry optimization) files
    _RELAX_FILE_NAME = "relax.xml"

    # POLICY
    # We will store everything needed for a further run in the local repository
    # (required files from FLEUR+SPEX), also all important results files.
    # These will ALWAYS be copied from the local repository to the machine
    # If a parent calculation exists, other files will be copied remotely when required
    #######

    _copy_filelist_job_remote = [
        _OUTXML_FILE_NAME,
        _INPXML_FILE_NAME,
        _CDN_HDF5_FILE_NAME,
        _BASIS_FILE_NAME,
        _POT_FILE_NAME,
        _ECORE_FILE,
    ]

    _copy_filelist1 = [_INPUT_FILE_NAME, _ENPARA_FILE_NAME]

    # possible settings_dict keys
    _settings_keys = [
        "additional_retrieve_list",
        "remove_from_retrieve_list",
        "additional_remotecopy_list",
        "remove_from_remotecopy_list",
        "cmdline",
    ]

    @classmethod
    def define(cls, spec):
        super(SpexCalculation, cls).define(spec)

        # spec.input('metadata.options.input_filename', valid_type=six.string_types,
        #            default=cls._INPXML_FILE_NAME)
        spec.input(
            "metadata.options.output_filename",
            valid_type=six.string_types,
            default=cls._OUTPUT_FILE_NAME,
        )
        # inputs
        spec.input(
            "parent_folder",
            valid_type=RemoteData,
            required=False,
            help="Use a remote or local repository folder as parent folder "
            "(also for restarts and similar). It should contain all the "
            "needed files for a SPEX calc, only edited files should be "
            "uploaded from the repository.",
        )
        spec.input(
            "parameters",
            valid_type=six.string_types,
            required=False,
            non_db=True,
            help="Calculation parameters.",
        )

        spec.input(
            "settings",
            valid_type=Dict,
            required=False,
            help="This parameter data node is used to specify for some "
            "advanced features how the plugin behaves. You can add files"
            "the retrieve list, or add command line switches, "
            "for all available features here check the documentation.",
        )

        # parser
        spec.input(
            "metadata.options.parser_name",
            valid_type=six.string_types,
            default="spex.spexparser",
        )

        # declare outputs of the calculation
        spec.output("output_parameters", valid_type=Dict, required=False)
        spec.output("output_params_complex", valid_type=Dict, required=False)
        spec.output("error_params", valid_type=Dict, required=False)
        spec.default_output_node = "output_parameters"

        # exit codes
        spec.exit_code(
            300, "ERROR_NO_RETRIEVED_FOLDER", message="No retrieved folder found."
        )
        spec.exit_code(
            301,
            "ERROR_OPENING_OUTPUTS",
            message="One of the output files can not be opened.",
        )
        spec.exit_code(
            302,
            "ERROR_SPEX_CALC_FAILED",
            message="SPEX calculation failed for unknown reason.",
        )
        spec.exit_code(
            303, "ERROR_NO_SPEXOUT", message="Spex Output file was not found."
        )
        spec.exit_code(
            304,
            "ERROR_SPEXOUT_PARSING_FAILED",
            message="Parsing of SPEX output file failed.",
        )
        spec.exit_code(
            310,
            "ERROR_NOT_ENOUGH_MEMORY",
            message="SPEX calculation failed due to lack of memory.",
        )

    @classproperty
    def _get_output_folder(self):
        return "./"

    def prepare_for_submission(self, folder):
        """
        This is the routine to be called when you make a SPEX calculation.
        This routine checks the inputs and modifies copy lists accordingly.
        The standard files to be copied are given here.

        :param folder: a aiida.common.folders.Folder subclass where
                           the plugin should put all its files.
        """

        local_copy_list = []
        remote_copy_list = []
        remote_symlink_list = []
        mode_retrieved_filelist = []
        filelist_tocopy_remote = []
        settings_dict = {}

        has_parent = False
        copy_remotely = True

        code = self.inputs.code

        if "parent_folder" in self.inputs:
            parent_calc_folder = self.inputs.parent_folder
        else:
            parent_calc_folder = None

        if parent_calc_folder is None:
            has_parent = False
            raise InputValidationError(
                "No parent calculation found. " "Need one fleur calculation."
            )
        else:
            # extract parent calculation
            parent_calcs = parent_calc_folder.get_incoming(node_class=CalcJob).all()
            n_parents = len(parent_calcs)
            if n_parents != 1:
                raise UniquenessError(
                    "Input RemoteData is child of {} "
                    "calculation{}, while it should have a single parent"
                    "".format(n_parents, "" if n_parents == 0 else "s")
                )
            parent_calc = parent_calcs[0].node
            parent_calc_class = parent_calc.process_class
            has_parent = True

            # if inpgen calc do
            # check if folder from db given, or get folder from rep.
            # Parent calc does not has to be on the same computer.

            if parent_calc_class is FleurCalculation:
                new_comp = self.node.computer
                old_comp = parent_calc.computer
                if new_comp.uuid != old_comp.uuid:
                    # don't copy files, copy files locally
                    copy_remotely = False
            else:
                raise InputValidationError("parent_calc, must be a 'fleur calculation'")

        # check existence of settings (optional)
        if "settings" in self.inputs:
            settings = self.inputs.settings
        else:
            settings = None

        if settings is None:
            settings_dict = {}
        else:
            settings_dict = settings.get_dict()

        # check for for allowed keys, ignore unknown keys but warn.
        for key in settings_dict.keys():
            if key not in self._settings_keys:
                self.logger.warning(
                    "settings dict key {} for SPEX calculation"
                    "not recognized, only {} are allowed."
                    "".format(key, self._settings_keys)
                )

        if "parameters" in self.inputs:
            input_parameters = self.inputs.parameters
        else:
            # TODO: raise error if no parameters given, but for now use a general raw parameter
            raise InputValidationError(
                "Input parameters, must be parameters of a valid 'spex inp'"
            )
            # input_parameters ="BZ 4 4 4\nJOB GW 1:(4-12)\nNBAND 80\nITERATE\n"

        if has_parent:
            # copy necessary files
            # TODO: check first if file exist and throw a warning if not
            outfolder_uuid = parent_calc.outputs.retrieved.uuid
            self.logger.info("out folder path {}".format(outfolder_uuid))

            # TODO: not on same computer -> copy needed files from repository
            # if they are not there throw an error
            if copy_remotely:  # on same computer.
                # from fleurmodes
                filelist_tocopy_remote = (
                    filelist_tocopy_remote + self._copy_filelist_job_remote
                )
                # from settings, user specified
                # TODO: check if list?
                for file1 in settings_dict.get("additional_remotecopy_list", []):
                    filelist_tocopy_remote.append(file1)

                for file1 in settings_dict.get("remove_from_remotecopy_list", []):
                    if file1 in filelist_tocopy_remote:
                        filelist_tocopy_remote.remove(file1)

                for file1 in filelist_tocopy_remote:
                    remote_copy_list.append(
                        (
                            parent_calc_folder.computer.uuid,
                            os.path.join(parent_calc_folder.get_remote_path(), file1),
                            self._get_output_folder,
                        )
                    )

                self.logger.info("remote copy file list {}".format(remote_copy_list))

        input_filename = folder.get_abs_path(self._INPUT_FILE_NAME)

        with open(input_filename, "w") as infile:
            # Should there be a title to identify the input?
            infile.write("{}".format(input_parameters))

        ########## MAKE CALCINFO ###########

        calcinfo = CalcInfo()

        calcinfo.uuid = self.uuid
        # Empty command line by default
        # cmdline_params = settings_dict.pop('CMDLINE', [])
        # calcinfo.cmdline_params = (list(cmdline_params)
        #                           + ["-in", self._INPUT_FILE_NAME])

        self.logger.info("local copy file list {}".format(local_copy_list))

        calcinfo.local_copy_list = local_copy_list
        calcinfo.remote_copy_list = remote_copy_list
        calcinfo.remote_symlink_list = remote_symlink_list

        # Retrieve by default the output file and the xml file
        retrieve_list = []
        retrieve_list.append(self._INPUT_FILE_NAME)
        retrieve_list.append(self._OUTPUT_FILE_NAME)
        retrieve_list.append(self._OUTXML_FILE_NAME)
        retrieve_list.append(self._INPXML_FILE_NAME)
        retrieve_list.append(self._ERROR_FILE_NAME)

        for mode_file in mode_retrieved_filelist:
            retrieve_list.append(mode_file)
        self.logger.info("retrieve_list: {}".format(retrieve_list))

        # user specific retrieve
        add_retrieve = settings_dict.get("additional_retrieve_list", [])
        self.logger.info("add_retrieve: {}".format(add_retrieve))
        for file1 in add_retrieve:
            retrieve_list.append(file1)

        remove_retrieve = settings_dict.get("remove_from_retrieve_list", [])
        for file1 in remove_retrieve:
            if file1 in retrieve_list:
                retrieve_list.remove(file1)

        calcinfo.retrieve_list = []
        for file1 in retrieve_list:
            calcinfo.retrieve_list.append(file1)

        codeinfo = CodeInfo()

        # walltime_sec = self.node.get_attribute("max_wallclock_seconds")
        cmdline_params = []  # > spex.out

        # if walltime_sec:
        #     walltime_min = max(1, walltime_sec / 60)
        #     cmdline_params.append("-wtime")
        #     cmdline_params.append("{}".format(walltime_min))

        # user specific commandline_options
        for command in settings_dict.get("cmdline", []):
            cmdline_params.append(command)

        codeinfo.cmdline_params = list(cmdline_params)

        codeinfo.code_uuid = code.uuid
        codeinfo.withmpi = self.node.get_attribute("max_wallclock_seconds")
        codeinfo.stdin_name = self._INPUT_FILE_NAME
        codeinfo.stdout_name = self._OUTPUT_FILE_NAME
        # codeinfo.join_files = True
        codeinfo.stderr_name = self._ERROR_FILE_NAME

        calcinfo.codes_info = [codeinfo]

        return calcinfo

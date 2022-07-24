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
In this module you find the workchain 'SpexJobWorkChain' for the JOB
cycle management of a SPEX calculation with AiiDA.

NOTICE: inorder to avoid large amount of data transfer for upload and dowload ...
... all necessary files for the calculation and restart are kept on the remote machine. ...
... Therefore is is adviced to do the calculation in the same remote machine. 
"""

from __future__ import absolute_import

import six
from aiida.common.exceptions import NotExistent, InputValidationError
from aiida.engine import ToContext, WorkChain
from aiida.engine import calcfunction as cf
from aiida.engine import if_, while_
from aiida.orm import CalcJobNode, Code, Dict, RemoteData, load_node

from aiida_spex.tools.common_spex_wf import (
    find_last_submitted_calcjob,
    get_inputs_spex,
    test_and_get_codenode,
)
from aiida_spex.workflows.base_spex import SpexBaseWorkChain
from aiida_spex.tools.spex_io import get_err_info
from aiida_spex.tools.spexinp_utils import SpexInputValidation, ValidationError


class SpexJobWorkChain(WorkChain):
    """
    Workchain for SPEX calculation.

    It converges the charge density, total energy or the largest force.
    Two paths are possible:

    (1) Start by doing a DFT calculation TODO
    (2) Start from a FLEUR/SPEX calculation, with remoteData

    :param wf_parameters: (Dict), Workchain Specifications
    :param calc_parameters: (Dict), Spexinp Parameters
    :param remote_data: (RemoteData), from a Fleur calculation
    :param spex: (Code)

    :return: output_spexjob_wc_para (Dict), Information of workflow results
        like Success, last result node, list with convergence behavior
    """

    _workflowversion = "1.0.8"
    _default_wf_para = {"spex_runmax": 0}

    _default_options = {
        "resources": {"num_machines": 1, "num_mpiprocs_per_machine": 1},
        "max_wallclock_seconds": 6 * 60 * 60,
        "queue_name": "",
        "custom_scheduler_commands": "",
        "import_sys_environment": False,
        "environment_variables": {},
    }

    @classmethod
    def define(cls, spec):
        super().define(spec)
        spec.input("spex", valid_type=Code, required=True)
        spec.input("options", valid_type=Dict, required=False)
        spec.input("wf_parameters", valid_type=Dict, required=False)

        # spec.input('calc_parameters', valid_type=Dict, required=False)
        spec.input("parameters", valid_type=Dict, required=False)
        spec.input("remote_data", valid_type=RemoteData, required=False)

        spec.input("settings", valid_type=Dict, required=False)
        spec.outline(
            cls.start,
            cls.validate_input,
            cls.run_spex,
            cls.inspect_spex,
            cls.get_res,
            cls.return_results,
        )

        spec.output("output_spexjob_wc_para", valid_type=Dict)
        spec.output("last_spex_calc_output", valid_type=Dict)
        spec.expose_outputs(SpexBaseWorkChain, namespace="last_calc")

        spec.exit_code(
            130, "ERROR_INVALID_INPUT_PARAM", message="Invalid workchain parameters."
        )
        spec.exit_code(
            102,
            "ERROR_SPEX_CALC_FAILED",
            message="SPEX calculation failed for unknown reason.",
        )

    def start(self):
        """
        init context and some parameters
        """
        self.report(
            "INFO: started job workflow version {}" "".format(self._workflowversion)
        )

        ####### init    #######

        # internal para /control para
        self.ctx.last_base_wc = None
        self.ctx.loop_count = 0
        self.ctx.calcs = []
        self.ctx.abort = False

        # return para/vars
        self.ctx.parse_last = True
        self.ctx.successful = True
        self.ctx.total_wall_time = 0
        self.ctx.warnings = []
        self.ctx.errors = []
        self.ctx.info = []

        wf_default = self._default_wf_para
        if "wf_parameters" in self.inputs:
            wf_dict = self.inputs.wf_parameters.get_dict()
        else:
            wf_dict = wf_default

        for key, val in six.iteritems(wf_default):
            wf_dict[key] = wf_dict.get(key, val)
        self.ctx.wf_dict = wf_dict

        self.ctx.serial = self.ctx.wf_dict.get("serial", False)

        defaultoptions = self._default_options.copy()
        user_options = {}
        if "options" in self.inputs:
            user_options = self.inputs.options.get_dict()

        if "options" in self.inputs:
            options = user_options
        else:
            options = defaultoptions
        # we use the same options for both codes, inpgen resources get overridden
        # and queue does not matter in case of direct scheduler

        # extend options given by user using defaults
        for key, val in six.iteritems(defaultoptions):
            options[key] = options.get(key, val)
        self.ctx.options = options

        self.ctx.max_number_runs = self.ctx.wf_dict.get("spex_runmax", 2)
        self.ctx.description_wf = self.inputs.get("description", "") + "|spex_job_wc|"
        self.ctx.label_wf = self.inputs.get("label", "spex_job_wc")

        # return para/vars

    def validate_input(self):
        """
        # validate input parameters
        """
        try:
            SpexInputValidation(**self.inputs.parameters.get_dict())
        except ValidationError as e:
            raise InputValidationError(
                "Found following error in input parameters: {}".format(e)
            )
    def run_spex(self):
        """
        run a SPEX calculation
        """
        self.report("INFO: run SPEX")

        if "settings" in self.inputs:
            settings = self.inputs.settings
        else:
            settings = None

        if self.ctx["last_base_wc"]:
            # will this fail if spex before failed? try needed?
            remote = self.ctx["last_base_wc"].outputs.remote_folder
        elif "remote_data" in self.inputs:
            remote = self.inputs.remote_data
        else:
            remote = None

        if "parameters" in self.inputs:
            params = self.inputs.parameters
        else:
            return self.exit_codes.ERROR_INVALID_INPUT_PARAM

        if "description" in self.inputs:
            description = self.inputs.description
        else:
            description = " "

        if "label" in self.inputs:
            label = self.inputs.label
        else:
            label = " "

        code = self.inputs.spex
        options = self.ctx.options.copy()

        inputs_builder = get_inputs_spex(
            code,
            remote,
            options,
            label=label,
            description=description,
            settings=settings,
            params=params,
        )
        future = self.submit(SpexBaseWorkChain, **inputs_builder)
        self.ctx.loop_count = self.ctx.loop_count + 1
        self.report("INFO: run SPEX number: {}".format(self.ctx.loop_count))
        self.ctx.calcs.append(future)

        return ToContext(last_base_wc=future)

    def inspect_spex(self):
        """
        Analyse the results of the previous Calculation (Spex),
        checking whether it finished successfully or if not, troubleshoot the
        cause and adapt the input parameters accordingly before
        restarting, or abort if unrecoverable error was found
        """
        self.report("INFO: inspect SPEX")
        try:
            base_wc = self.ctx.last_base_wc
        except AttributeError:
            self.ctx.parse_last = False
            error = "ERROR: Something went wrong I do not have a last calculation"
            self.control_end_wc(error)
            return self.exit_codes.ERROR_SPEX_CALC_FAILED

        exit_status = base_wc.exit_status
        if not base_wc.is_finished_ok:
            error = (
                f"ERROR: Last SPEX calculation failed with exit status {exit_status}"
            )
            self.control_end_wc(error)
            return self.exit_codes.ERROR_SPEX_CALC_FAILED
        else:
            self.ctx.parse_last = True

    def get_res(self):
        """
        Check how the last SPEX calculation went
        Parse some results.
        """
        self.report("INFO: get results SPEX")
        if self.ctx.parse_last:
            last_base_wc = self.ctx.last_base_wc
            spex_calcjob = load_node(find_last_submitted_calcjob(last_base_wc))
            walltime = last_base_wc.outputs.output_parameters.dict.walltime

            if isinstance(walltime, int):
                self.ctx.total_wall_time = self.ctx.total_wall_time + walltime

            with spex_calcjob.outputs.retrieved.open(
                spex_calcjob.process_class._ERROR_FILE_NAME, "r"
            ) as errfile:
                output_dict = get_err_info(errfile.read())

            spex_info = output_dict.get("spex_info", [])
            if spex_info is not None:
                self.ctx.info.extend(spex_info)

            spex_warnings = output_dict.get("spex_warnings", [])
            if spex_warnings is not None:
                self.ctx.warnings.extend(spex_warnings)

            spex_errors = output_dict.get("spex_errors", [])
            if spex_errors is not None:
                self.ctx.errors.extend(spex_errors)

    def return_results(self):
        """
        return the results of the calculations
        This should run through and produce output nodes even if everything failed,
        therefore it only uses results from context.
        """
        if self.ctx.last_base_wc:
            try:
                last_calc_uuid = find_last_submitted_calcjob(self.ctx.last_base_wc)
            except NotExistent:
                last_calc_uuid = None
        else:
            last_calc_uuid = None

        try:  # if something failed, we still might be able to retrieve something
            last_calc_out = self.ctx.last_base_wc.outputs.output_parameters
            retrieved = self.ctx.last_base_wc.outputs.retrieved
        except (NotExistent, AttributeError):
            last_calc_out = None
            retrieved = None

        outputnode_dict = {}
        outputnode_dict["workflow_name"] = self.__class__.__name__
        outputnode_dict["workflow_version"] = self._workflowversion
        outputnode_dict["loop_count"] = self.ctx.loop_count
        outputnode_dict["last_calc_uuid"] = last_calc_uuid
        outputnode_dict["total_wall_time"] = self.ctx.total_wall_time
        outputnode_dict["total_wall_time_units"] = "s"
        outputnode_dict["info"] = self.ctx.info
        outputnode_dict["warnings"] = self.ctx.warnings
        outputnode_dict["errors"] = self.ctx.errors

        if self.ctx.successful:
            self.report(
                "STATUS: Done, the termination criteria is reached.\n"
                "INFO: the SPEX calculation "
                "finished after {} SPEX runs and took {} sec \n"
                "".format(self.ctx.loop_count, self.ctx.total_wall_time)
            )
        else:  # Termination ok, but not finished yet...
            if self.ctx.abort:  # some error occurred, do not use the output.
                self.report(
                    "STATUS/ERROR: I abort, see logs and "
                    "errors/warning/hints in output_spexjob_wc_para"
                )

        outputnode_t = Dict(dict=outputnode_dict)
        # what hapens if last_calc_out doesnt exist...
        if last_calc_out:
            outdict = create_spexjob_result_node(
                outpara=outputnode_t,
                last_calc_out=last_calc_out,
                last_calc_retrieved=retrieved,
            )
        else:
            outdict = create_spexjob_result_node(outpara=outputnode_t)

        if last_calc_out:
            outdict["last_spex_calc_output"] = last_calc_out

        if self.ctx.last_base_wc:
            self.out_many(
                self.exposed_outputs(
                    self.ctx.last_base_wc, SpexBaseWorkChain, namespace="last_calc"
                )
            )

        # outdict['output_spexjob_wc_para'] = outputnode
        for link_name, node in six.iteritems(outdict):
            self.out(link_name, node)

    def control_end_wc(self, errormsg):
        """
        Controlled way to shutdown the workchain. will initialize the output nodes
        The shutdown of the workchain will has to be done afterwards
        """
        self.ctx.successful = False
        self.ctx.abort = True
        self.report(errormsg)  # because return_results still fails somewhen
        self.ctx.errors.append(errormsg)
        self.return_results()


@cf
def create_spexjob_result_node(**kwargs):
    """
    This is a pseudo wf, to create the right graph structure of AiiDA.
    This wokfunction will create the output node in the database.
    It also connects the output_node to all nodes the information commes from.
    So far it is just also parsed in as argument, because so far we are to lazy
    to put most of the code overworked from return_results in here.
    """
    for key, val in six.iteritems(kwargs):
        if key == "outpara":  # should be always there
            outpara = val
    outdict = {}
    outputnode = outpara.clone()
    outputnode.label = "output_spexjob_wc_para"
    outputnode.description = "Contains results and information of an spex_job_wc run."

    outdict["output_spexjob_wc_para"] = outputnode
    return outdict

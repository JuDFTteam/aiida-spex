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
This module contains the SpexBaseWorkChain.
SpexBaseWorkChain is a workchain that wraps the submission of
the SPEX calculation. Inheritance from the BaseRestartWorkChain
allows to add scenarios to restart a calculation in an
automatic way if an expected failure occurred.
"""
from __future__ import absolute_import

import six
from aiida import orm
from aiida.common import AttributeDict
from aiida.engine import while_
from aiida.plugins import CalculationFactory, DataFactory

from aiida_spex.calculations.spex import SpexCalculation
from aiida_spex.common.workchain.base.restart import BaseRestartWorkChain
from aiida_spex.common.workchain.spex_utils import (ErrorHandlerReport,
                                               register_error_handler)
from aiida_spex.tools.spexinp_utils import check_parameters


class SpexBaseWorkChain(BaseRestartWorkChain):
    """Workchain to run a SPEX calculation with automated error handling and restarts"""

    _workflowversion = "1.0.0"

    _calculation_class = SpexCalculation

    @classmethod
    def define(cls, spec):
        super().define(spec)
        spec.input("code", valid_type=orm.Code, help="The SPEX code.")
        spec.input(
            "parent_folder",
            valid_type=orm.RemoteData,
            required=False,
            help="An optional working directory of a previously completed calculation to restart from.",
        )
        spec.input(
            "parameters",
            valid_type=orm.Dict,
            required=False,
            help="Calculation parameters.",
        )

        spec.input(
            "settings",
            valid_type=orm.Dict,
            required=False,
            help="Optional parameters to affect the way the calculation job and the parsing"
            " are performed.",
        )
        spec.input(
            "options",
            valid_type=orm.Dict,
            help="Optional parameters to set up computational details.",
        )

        spec.input(
            "description",
            valid_type=six.string_types,
            required=False,
            non_db=True,
            help="Calculation description.",
        )
        spec.input(
            "label",
            valid_type=six.string_types,
            required=False,
            non_db=True,
            help="Calculation label.",
        )

        spec.outline(
            cls.setup,
            cls.validate_inputs,
            while_(cls.should_run_calculation)(
                cls.run_calculation,
                cls.inspect_calculation,
            ),
            cls.results,
        )

        spec.output("output_parameters", valid_type=orm.Dict, required=False)
        spec.output("output_params_complex", valid_type=orm.Dict, required=False)
        spec.output("retrieved", valid_type=orm.FolderData, required=False)
        spec.output("remote_folder", valid_type=orm.RemoteData, required=False)
        spec.output("final_calc_uuid", valid_type=orm.Str, required=False)
        spec.expose_outputs(SpexCalculation)

        spec.exit_code(
            390,
            "ERROR_INVALID_PARAMETERS",
            message="The input parameters are invalid.",
        )

    def validate_inputs(self):
        """
        Validate inputs that might depend on each other and cannot be validated by the spec.
        Also define dictionary `inputs` in the context, that will contain the inputs for the
        calculation that will be launched in the `run_calculation` step.
        """
        self.ctx.inputs = AttributeDict(
            {"code": self.inputs.code, "metadata": AttributeDict()}
        )

        input_options = self.inputs.options.get_dict()
        self.ctx.optimize_resources = input_options.pop("optimize_resources", False)
        self.ctx.inputs.metadata.options = input_options

        if "parent_folder" in self.inputs:
            self.ctx.inputs.parent_folder = self.inputs.parent_folder

        if "description" in self.inputs:
            self.ctx.inputs.metadata.description = self.inputs.description
        else:
            self.ctx.inputs.metadata.description = ""
        if "label" in self.inputs:
            self.ctx.inputs.metadata.label = self.inputs.label
        else:
            self.ctx.inputs.metadata.label = ""

        if "settings" in self.inputs:
            self.ctx.inputs.settings = self.inputs.settings.get_dict()
        else:
            self.ctx.inputs.settings = {}

        if "parameters" in self.inputs:
            isvalid = check_parameters(self.inputs.parameters.get_dict())
            if not isvalid:
                self.exit_codes.ERROR_INVALID_PARAMETERS
            else:
                self.ctx.inputs.parameters = self.inputs.parameters.get_dict()

        if not self.ctx.optimize_resources:
            self.ctx.can_be_optimised = (
                False  # set this for handlers to not change resources
            )
            return

        resources_input = self.ctx.inputs.metadata.options["resources"]
        try:
            self.ctx.num_machines = int(resources_input["num_machines"])
            self.ctx.num_mpiprocs_per_machine = int(
                resources_input["num_mpiprocs_per_machine"]
            )
        except KeyError:
            self.ctx.can_be_optimised = False
            self.report("WARNING: Computation resources were not optimised.")
        else:
            try:
                self.ctx.num_cores_per_mpiproc = int(
                    resources_input["num_cores_per_mpiproc"]
                )
                self.ctx.use_omp = True
                self.ctx.suggest_mpi_omp_ratio = (
                    self.ctx.num_mpiprocs_per_machine / self.ctx.num_cores_per_mpiproc
                )
            except KeyError:
                self.ctx.num_cores_per_mpiproc = 1
                self.ctx.use_omp = False
                self.ctx.suggest_mpi_omp_ratio = 1


@register_error_handler(SpexBaseWorkChain, 1)
def _handle_general_error(self, calculation):
    """
    Calculation failed for unknown reason.
    """
    if calculation.exit_status in SpexCalculation.get_exit_statuses(
        ["ERROR_SPEX_CALC_FAILED"]
    ):
        self.ctx.restart_calc = calculation
        self.ctx.is_finished = True
        self.report(
            "Calculation failed for a reason that can not be resolved automatically"
        )
        self.results()
        return ErrorHandlerReport(
            True, True, self.exit_codes.ERROR_SOMETHING_WENT_WRONG
        )
    else:
        raise ValueError(
            "Calculation failed for unknown reason, please register the "
            "corresponding exit code in this error handler"
        )

# -*- coding: utf-8 -*-
###############################################################################
# Copyright (c), Forschungszentrum Jülich GmbH, IAS-1/PGI-1, Germany.         #
#                All rights reserved.                                         #
# This file is part of the AiiDA-SPEX package.                               #
#                                                                             #
# The code is hosted on GitHub at https://github.com/JuDFTteam/aiida-spex    #
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

from aiida_spex.common.workchain.base.restart import BaseRestartWorkChain
from aiida_spex.common.workchain.utils import register_error_handler, ErrorHandlerReport
from aiida_spex.calculation.spex import SpexCalculation as SpexProcess


class SpexBaseWorkChain(BaseRestartWorkChain):
    """Workchain to run a SPEX calculation with automated error handling and restarts"""
    _workflowversion = '0.1.1'

    _calculation_class = SpexProcess

    @classmethod
    def define(cls, spec):
        super().define(spec)
        spec.input('code', valid_type=orm.Code, help='The SPEX code.')
        spec.input('parent_folder',
                   valid_type=orm.RemoteData,
                   required=False,
                   help='An optional working directory of a previously completed calculation to restart from.')
        spec.input('settings',
                   valid_type=orm.Dict,
                   required=False,
                   help='Optional parameters to affect the way the calculation job and the parsing'
                   ' are performed.')
        spec.input('options', valid_type=orm.Dict, help='Optional parameters to set up computational details.')

        spec.input('description',
                   valid_type=six.string_types,
                   required=False,
                   non_db=True,
                   help='Calculation description.')
        spec.input('label', valid_type=six.string_types, required=False, non_db=True, help='Calculation label.')

        spec.outline(
            cls.setup,
            cls.validate_inputs,
            while_(cls.should_run_calculation)(
                cls.run_calculation,
                cls.inspect_calculation,
            ),
            cls.results,
        )

        spec.output('output_parameters', valid_type=orm.Dict, required=False)
        spec.output('output_params_complex', valid_type=orm.Dict, required=False)
        spec.output('retrieved', valid_type=orm.FolderData, required=False)
        spec.output('remote_folder', valid_type=orm.RemoteData, required=False)
        spec.output('final_calc_uuid', valid_type=orm.Str, required=False)


    def validate_inputs(self):
        """
        Validate inputs that might depend on each other and cannot be validated by the spec.
        Also define dictionary `inputs` in the context, that will contain the inputs for the
        calculation that will be launched in the `run_calculation` step.
        """
        pass



@register_error_handler(SpexBaseWorkChain, 1)
def _handle_general_error(self, calculation):
    """
    Calculation failed for unknown reason.
    """
    if calculation.exit_status in SpexProcess.get_exit_statuses([ 'ERROR_SPEX_CALC_FAILED' ]):
        self.ctx.restart_calc = calculation
        self.ctx.is_finished = True
        self.report('Calculation failed for a reason that can not be resolved automatically')
        self.results()
        return ErrorHandlerReport(True, True, self.exit_codes.ERROR_SOMETHING_WENT_WRONG)
    else:
        raise ValueError('Calculation failed for unknown reason, please register the '
                         'corresponding exit code in this error handler')
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
In this module you find the workchain 'SpexJobWorkChain' for the self-consistency
cycle management of a SPEX calculation with AiiDA.
"""

from __future__ import absolute_import
import six

from aiida.orm import Code, load_node, CalcJobNode
from aiida.orm import RemoteData, Dict
from aiida.engine import WorkChain, while_, if_, ToContext
from aiida.engine import calcfunction as cf
from aiida.common.exceptions import NotExistent


from aiida_spex.tools.common_spex_wf import get_inputs_spex, test_and_get_codenode
from aiida_spex.workflows.base_spex import SpexBaseWorkChain
from aiida_spex.tools.common_spex_wf import find_last_submitted_calcjob


class SpexJobWorkChain(WorkChain):
    """
    Workchain for SPEX calculation.

    It converges the charge density, total energy or the largest force.
    Two paths are possible:

    (1) Start by doing a DFT calculation TODO
    (2) Start from a Fleur calculation, with optional remoteData

    :param wf_parameters: (Dict), Workchain Specifications
    :param calc_parameters: (Dict), Spexinp Parameters
    :param remote_data: (RemoteData), from a Fleur calculation
    :param spex: (Code)

    :return: output_job_wc_para (Dict), Information of workflow results
        like Success, last result node, list with convergence behavior
    """

    _workflowversion = '0.1.0'
    _default_wf_para = {
        'spex_runmax': 1
    }

    _default_options = {
        'resources': {
            'num_machines': 1,
            'num_mpiprocs_per_machine': 1
        },
        'max_wallclock_seconds': 6 * 60 * 60,
        'queue_name': '',
        'custom_scheduler_commands': '',
        'import_sys_environment': False,
        'environment_variables': {}
    }

    @classmethod
    def define(cls, spec):
        super().define(spec)
        spec.input('spex', valid_type=Code, required=True)
        spec.input('options', valid_type=Dict, required=False)
        spec.input('wf_parameters', valid_type=Dict, required=False)

        # spec.input('calc_parameters', valid_type=Dict, required=False)
        spec.input('raw_spexinp', valid_type=six.string_types, non_db=True, required=False)
        spec.input('remote_data', valid_type=RemoteData, required=False)

        spec.input('settings', valid_type=Dict, required=False)
        spec.outline(cls.start, cls.validate_input,
                     cls.run_spex, cls.return_results)

        spec.output('output_job_wc_para', valid_type=Dict)
        spec.output('last_spex_calc_output', valid_type=Dict)

        spec.exit_code(230, 'ERROR_INVALID_INPUT_PARAM', message='Invalid workchain parameters.')

    def start(self):
        """
        init context and some parameters
        """
        self.report('INFO: started job workflow version {}' ''.format(
            self._workflowversion))

        ####### init    #######

        # internal para /control para
        self.ctx.last_base_wc = None
        self.ctx.loop_count = 0
        self.ctx.calcs = []
        self.ctx.abort = False

        wf_default = self._default_wf_para
        if 'wf_parameters' in self.inputs:
            wf_dict = self.inputs.wf_parameters.get_dict()
        else:
            wf_dict = wf_default

        for key, val in six.iteritems(wf_default):
            wf_dict[key] = wf_dict.get(key, val)
        self.ctx.wf_dict = wf_dict

        self.ctx.serial = self.ctx.wf_dict.get('serial', False)

        defaultoptions = self._default_options.copy()
        user_options = {}
        if 'options' in self.inputs:
            user_options = self.inputs.options.get_dict()

        if 'options' in self.inputs:
            options = user_options
        else:
            options = defaultoptions
        # we use the same options for both codes, inpgen resources get overridden
        # and queue does not matter in case of direct scheduler

        # extend options given by user using defaults
        for key, val in six.iteritems(defaultoptions):
            options[key] = options.get(key, val)
        self.ctx.options = options

        self.ctx.max_number_runs = self.ctx.wf_dict.get('spex_runmax', 4)
        self.ctx.description_wf = self.inputs.get(
            'description', '') + '|spex_job_wc|'
        self.ctx.label_wf = self.inputs.get('label', 'spex_job_wc')

        # return para/vars
        self.ctx.successful = True
        self.ctx.warnings = []
        # "debug": {},
        self.ctx.errors = []
        self.ctx.info = []
        self.ctx.total_wall_time = 0

    def validate_input(self):
        """
        # validate input and find out which path (1, or 2) to take
        # return True means run fleur if false run spex directly: TODO
        """
        pass

    def run_spex(self):
        """
        run a SPEX calculation
        """
        self.report('INFO: run SPEX')

        if 'settings' in self.inputs:
            settings = self.inputs.settings
        else:
            settings = None

        if self.ctx['last_base_wc']:
            # will this fail if spex before failed? try needed?
            remote = self.ctx['last_base_wc'].outputs.remote_folder
        elif 'remote_data' in self.inputs:
            remote = self.inputs.remote_data
        else:
            remote = None

        # This should move to validation
        # if 'calc_parameters' in self.inputs:
        #     params = self.inputs.calc_parameters
        if 'raw_spexinp' in self.inputs:
            params = self.inputs.raw_spexinp
        else:
            return self.exit_codes.ERROR_INVALID_INPUT_PARAM


        label = ' '
        description = ' '

        code = self.inputs.spex
        options = self.ctx.options.copy()

        inputs_builder = get_inputs_spex(code,
                                         remote,
                                         options,
                                         label,
                                         description,
                                         settings, params)
        future = self.submit(SpexBaseWorkChain, **inputs_builder)
        self.ctx.loop_count = self.ctx.loop_count + 1
        self.report('INFO: run SPEX number: {}'.format(self.ctx.loop_count))
        self.ctx.calcs.append(future)

        return ToContext(last_base_wc=future)

    def return_results(self):
        """
        return the results of the calculations
        This should run through and produce output nodes even if everything failed,
        therefore it only uses results from context.
        """
        if self.ctx.last_base_wc:
            try:
                last_calc_uuid = find_last_submitted_calcjob(
                    self.ctx.last_base_wc)
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
        outputnode_dict['workflow_name'] = self.__class__.__name__
        outputnode_dict['workflow_version'] = self._workflowversion
        outputnode_dict['loop_count'] = self.ctx.loop_count
        outputnode_dict['last_calc_uuid'] = last_calc_uuid
        outputnode_dict['total_wall_time'] = self.ctx.total_wall_time
        outputnode_dict['total_wall_time_units'] = 's'
        outputnode_dict['info'] = self.ctx.info
        outputnode_dict['warnings'] = self.ctx.warnings
        outputnode_dict['errors'] = self.ctx.errors

        if self.ctx.successful:
            self.report('STATUS: Done, the termination criteria is reached.\n'
                        'INFO: the SPEX calculation '
                        'finished after {} SPEX runs and took {} sec \n'
                        ''.format(self.ctx.loop_count, self.ctx.total_wall_time))
        else:  # Termination ok, but not finished yet...
            if self.ctx.abort:  # some error occurred, do not use the output.
                self.report(
                    'STATUS/ERROR: I abort, see logs and ' 'errors/warning/hints in output_job_wc_para')

        outputnode_t = Dict(dict=outputnode_dict)
        # this is unsafe so far, because last_calc_out could not exist...
        if last_calc_out:
            outdict = create_job_result_node(outpara=outputnode_t,
                                             last_calc_out=last_calc_out,
                                             last_calc_retrieved=retrieved)
        else:
            outdict = create_job_result_node(outpara=outputnode_t)

        if last_calc_out:
            outdict['last_spex_calc_output'] = last_calc_out

        #outdict['output_job_wc_para'] = outputnode
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
def create_job_result_node(**kwargs):
    """
    This is a pseudo wf, to create the right graph structure of AiiDA.
    This wokfunction will create the output node in the database.
    It also connects the output_node to all nodes the information commes from.
    So far it is just also parsed in as argument, because so far we are to lazy
    to put most of the code overworked from return_results in here.
    """
    for key, val in six.iteritems(kwargs):
        if key == 'outpara':  # should be always there
            outpara = val
    outdict = {}
    outputnode = outpara.clone()
    outputnode.label = 'output_job_wc_para'
    outputnode.description = (
        'Contains results and information of an spex_job_wc run.')

    outdict['output_job_wc_para'] = outputnode
    return outdict

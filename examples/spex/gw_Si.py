# -*- coding: utf-8 -*-
"""
Here we run the FleurScfWorkChain
"""
# pylint: disable=invalid-name
from __future__ import absolute_import
from __future__ import print_function
import argparse
from pprint import pprint
from ase import io


from aiida.plugins import DataFactory
from aiida.orm import load_node
from aiida.engine import submit, run

# import the FleurinpgenCalculation
from aiida_spex.workflows.job import SpexJobWorkChain
from aiida_spex.tools.common_spex_wf import is_code, test_and_get_codenode

Dict = DataFactory('dict')

### Defaults ###
options = Dict(dict={'resources': {"num_machines": 1, "num_mpiprocs_per_machine": 2},
                     #  'queue_name': 'devel',
                     #  'custom_scheduler_commands': '#SBATCH --account="jpgi10"',
                     'max_wallclock_seconds':  30*60})

wf_parameters = Dict(dict={'spex_runmax': 1, #Note that runmax > 1 only works with RESTART keyword
                     'serial': False})

remote_data = load_node(44402) # Remote data folder must have necessary files for a spex run
raw_spexinp="BZ 4 4 4\nJOB GW 1:(4-12)\nNBAND 80\nITERATE\n"
parameters = Dict(dict={
    'BZ': [4,4,4],
    'NBAND': 80,
    'KPT':{
        'R': [0.5,0.5,0.5],
        'X': [0.0,0.5,0.5]
    },
    'KPTPATH':['G','R','X','G'],
    'JOB': {
        'KS': {'1':(4,12)},
        'GW': {'1':(4,12)}
    },
    'ITERATE': True # default = True
})


inputs = {}
spex_code = is_code(44190)
inputs['spex'] = test_and_get_codenode( spex_code, expected_code_type='spex.spex')
inputs['options'] = options
inputs['wf_parameters'] = wf_parameters

inputs['remote_data'] = remote_data
# inputs['calc_parameters'] = parameters
inputs['raw_spexinp'] = raw_spexinp


res = submit(SpexJobWorkChain, **inputs)
print(("RUNTIME INFO: {}".format(res)))

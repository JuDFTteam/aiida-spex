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
from aiida_fleur.workflows.scf import FleurScfWorkChain
from aiida_fleur.tools.common_fleur_wf import is_code, test_and_get_codenode

Dict = DataFactory('dict')
FleurinpData = DataFactory('fleur.fleurinp')
StructureData = DataFactory('structure')

### Defaults ###
wf_para = Dict(dict={'fleur_runmax': 2,
                     'density_converged': 0.001,
                     'energy_converged': 0.002,
                     'mode': 'gw',  # 'force', 'energy', 'density', 'gw
                     'itmax_per_run': 20,
                     'use_relax_xml': False,
                     'serial': False})

options = Dict(dict={'resources': {"num_machines": 1, "num_mpiprocs_per_machine": 8},
                     #  'queue_name': 'devel',
                     'custom_scheduler_commands': '#SBATCH --account="jpgi10"',
                     'max_wallclock_seconds':  30*60})


struct = io.read('Si_mp-165_conventional_standard.cif')
structure = StructureData(ase=struct)

parameters = Dict(dict={
    #     'atom': {'element': 'Si',
    #  'jri': 981,
    #  'rmt': 2.1,
    # 'dx' : 0.015,
    #  'lmax': 12,
    #  },
    'comp': {'kmax': 5.0,
             #  'gmax': 15.0,
             #  'gmaxxc': 12.5
             },
    'kpt': {'div1': 4,
            'div2': 4,
            'div3': 4
            }
})

# submit
default = {'structure': structure,
           'wf_parameters': wf_para,
           'options': options,
           'calc_parameters': parameters
           }
inputs = {}

inputs['wf_parameters'] = default['wf_parameters']
inputs['structure'] = default['structure']
inputs['calc_parameters'] = default['calc_parameters']
inputs['options'] = default['options']


inpgen_code = is_code(19877) 
inputs['inpgen'] = test_and_get_codenode(
    inpgen_code, expected_code_type='fleur.inpgen')
fleur_code = is_code(19878)
inputs['fleur'] = test_and_get_codenode(
    fleur_code, expected_code_type='fleur.fleur')

res = submit(FleurScfWorkChain, **inputs)
print(("RUNTIME INFO: {}".format(res)))

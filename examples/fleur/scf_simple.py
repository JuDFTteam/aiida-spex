# -*- coding: utf-8 -*-
"""
Here we run the FleurScfWorkChain
"""
# pylint: disable=invalid-name
from __future__ import absolute_import
from __future__ import print_function
import argparse
from pprint import pprint


from aiida.plugins import DataFactory
from aiida.orm import load_node
from aiida.engine import submit, run

from aiida_fleur.workflows.scf import FleurScfWorkChain
from aiida_fleur.tools.common_fleur_wf import is_code, test_and_get_codenode

Dict = DataFactory('dict')
FleurinpData = DataFactory('fleur.fleurinp')
StructureData = DataFactory('structure')

### Defaults ###
options = Dict(dict={'resources': {"num_machines": 1, "num_mpiprocs_per_machine": 24},
                     'custom_scheduler_commands': '#SBATCH --account="jpgi10"', 
                     'max_wallclock_seconds':   2*60*60})

wf_para = Dict(dict={'fleur_runmax': 4,
                     'density_converged': 0.00002,
                     'energy_converged': 0.002,
                     'mode': 'gw',
                     'itmax_per_run': 20,
                     'force_dict': {'qfix': 2, 'forcealpha': 0.5, 'forcemix': 'BFGS'},
                     'serial': False})


# MAPI -12 atom cubic system
bohr_a_0 = 0.52917721092  # A
# a = 7.497 * bohr_a_0
a = 6.3200  # A
cell = [[a, 0.0, 0.0],
        [0.0, a, 0.0],
        [0.0, 0.0, a]]
structure = StructureData(cell=cell)
structure.append_atom(position=(-0.78100, 0.00000, 0.00000), symbols='C', name='C')
structure.append_atom(position=(0.78100, 0.00000, 0.00000), symbols='N', name='N')
structure.append_atom(position=(1.13767, 0.99611, -0.15956), symbols='H', name='H1')
structure.append_atom(position=(1.13767, -0.63623, -0.78288), symbols='H', name='H2')
structure.append_atom(position=(1.13767, -0.35987, 0.94243), symbols='H', name='H3')
structure.append_atom(position=(-1.13767, 0.35987, -0.94243), symbols='H', name='H4')
structure.append_atom(position=(-1.13767, 0.63623, 0.78288), symbols='H', name='H5')
structure.append_atom(position=(-1.13767, -0.99611, 0.15956), symbols='H', name='H6')
structure.append_atom(position=(0.5000 * a, 0.5000 * a, 0.5000 * a), symbols='Pb', name='Pb')
structure.append_atom(position=(0.5000 * a, 0.5000 * a, 1.0000 * a), symbols='I', name='I1')
structure.append_atom(position=(0.5000 * a, 0.0000, 0.5000 * a), symbols='I', name='I2')
structure.append_atom(position=(1.0000 * a, 0.5000 * a, 0.5000 * a), symbols='I', name='I3')
structure.pbc = (True, True, True)



parameters = Dict(dict={
    'atom': {
        'element': 'Pb',
        'lo': '5d',
    },
    'comp': {
        'kmax': 3.5,
        'gmaxxc': 9.0,
        'gmax': 11
    },
    'kpt': {
        'div1': 4,
        'div2': 4,
        'div3': 4
    }})

default = {'structure': structure,
           'wf_parameters': wf_para,
           'options': options,
           'calc_parameters': parameters
           }

####

inputs = {}

inputs['wf_parameters'] = default['wf_parameters']
inputs['structure'] = default['structure']
inputs['calc_parameters'] = default['calc_parameters']
inputs['options'] = default['options']
fleur_code = is_code(19878)
inputs['fleur'] = test_and_get_codenode(fleur_code, expected_code_type='fleur.fleur')
inpgen_code = is_code(19877)
inputs['inpgen'] = test_and_get_codenode(inpgen_code, expected_code_type='fleur.inpgen')

res = submit(FleurScfWorkChain, **inputs)
print("##################### Submited FleurScfWorkChain #####################")
print(("Runtime info: {}".format(res)))
print("##################### Finished submiting FleurScfWorkChain #####################")
# print("##################### Running FleurScfWorkChain #####################")
# res = run(FleurScfWorkChain, **inputs)
# print("##################### Finished running FleurScfWorkChain #####################")

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
                     'mode': 'gw',
                     'itmax_per_run': 9,
                     'use_relax_xml': False,
                     'serial': False})

options = Dict(dict={'resources': {"num_machines": 1, "num_mpiprocs_per_machine": 2},
                     #  'queue_name': 'devel',
                     #  'custom_scheduler_commands': '#SBATCH --account="jpgi10"',
                     'max_wallclock_seconds':  30*60})


# MAPI -12 atom cubic system
bohr_a_0 = 0.52917721092
a = 5.43  # in A
cell = [[a, 0, 0],
        [0, a, 0],
        [0, 0, a]]
structure = StructureData(cell=cell)
structure.append_atom(position=(0.125*a, 0.125*a, 0.125*a),
                      symbols='Si', name='Si1')
structure.append_atom(position=(-0.125*a, -0.125*a, -
                      0.125*a), symbols='Si', name='Si2')
structure.pbc = (True, True, True)

parameters = Dict(dict={
    'comp': {'kmax': 4.0},
    'kpt': {'div1': 4, 'div2': 4, 'div3': 4}
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


inpgen_code = is_code(44188)
inputs['inpgen'] = test_and_get_codenode(
    inpgen_code, expected_code_type='fleur.inpgen')
fleur_code = is_code(44189)
inputs['fleur'] = test_and_get_codenode(
    fleur_code, expected_code_type='fleur.fleur')

res = submit(FleurScfWorkChain, **inputs)
print(("RUNTIME INFO: {}".format(res)))

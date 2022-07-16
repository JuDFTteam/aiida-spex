import re
from io import StringIO

import numpy as np
import pandas as pd


def get_run_info(contents):
    run_patterns = [
        re.compile(r'Version\s*(\d+[.]\d+\s* \(.*\))'),
        re.compile(r'Execution time:\s*(.*)'),
        re.compile(r'Compiler:\s*(.*)'),
        re.compile(r'Hostname:\s*(.*)'),
        re.compile(r'Interfaced to \s*(.*)'),
        re.compile(r'MPI:\s*(.*)'),
    ]
    run_info = {
        'version':None,
        'execution_time':None,
        'compiler':None,
        'hostname':None,
        'interfaced_to':None,
        'mpi':None,
    }
    for key, pattern in zip(run_info.keys(),run_patterns):
        match = pattern.search(contents)
        if match:
            run_info[key]= re.sub(' +|\n',' ' ,match.group(1).strip())

    return run_info

def get_basic_info(contents):
    basic_info = {
        'number_of_spins':None,
        'number_of_centers':None,
        'number_of_types':None,
        'equivalent_atoms':None,
        'lattice_parameter':None,
        'primitive_vectors':None,
        'unit_cell_volume':None,
        'reciprocal_vectors':None,
        'reciprocal_volume':None,
        'reciprocal_cutoff':None,
    }

    basic_patterns = [
        re.compile(r'Number of spins\s*=\s*(\d+)'),
        re.compile(r'centers\s*=\s*(\d+)'),
        re.compile(r'types\s*=\s*(\d+)'),
        re.compile(r'equivalent atoms\s*=\s*(.*)'),
        re.compile(r'Lattice parameter\s*=\s*(\d+.\d+)'),
        re.compile(r'Primitive vectors\s*=((\s*.*){3})'),
        re.compile(r'Unit-cell volume\s*=\s*(\d+.\d+)'),
        re.compile(r'Reciprocal vectors\s*=((\s*.*){3})'),
        re.compile(r'Reciprocal volume\s*=\s*(\d+.\d+)'),
        re.compile(r'Reciprocal cutoff\s*=\s*(\d+.\d+)'),
    ]
    for key, pattern in zip(basic_info.keys(),basic_patterns):
        match = pattern.search(contents)
        if match:
            basic_info[key]= re.sub(' +|\n',' ' ,match.group(1).strip())
    basic_info['primitive_vectors'] = np.array(basic_info['primitive_vectors'].split(),dtype=float).reshape(3,3)
    basic_info['reciprocal_vectors'] = np.array(basic_info['reciprocal_vectors'].split(),dtype=float).reshape(3,3)
    basic_info['number_of_spins'] = int(basic_info['number_of_spins'])
    basic_info['number_of_centers'] = int(basic_info['number_of_centers'])
    basic_info['number_of_types'] = int(basic_info['number_of_types'])
    basic_info['unit_cell_volume'] = float(basic_info['unit_cell_volume'])
    basic_info['reciprocal_volume'] = float(basic_info['reciprocal_volume'])
    return basic_info

def get_unitcell_info(contents):
    # basic_info = get_basic_info(contents)
    # TODO instead of all the info just parse the centers 
    pattern = re.compile(r'centers\s*=\s*(\d+)')
    number_of_centers = pattern.search(contents).group(1)
    unitcell_patterns = [
        re.compile(r'#\s+Ty\s+El\s+Coord.\s*((\s*.*){'+number_of_centers+r'})'),
        re.compile(r'Number of symmetry operations\s*=\s*(\d+)'),
        re.compile(r'Number of valence electrons:\s*(\d+)'),
        re.compile(r'Number of k points:\s+(\d+)'),
        re.compile(r'in IBZ:\s+(\d+)'),
        # The following are specific to KPTPATH keyword
        # re.compile(r'K points in path:\s+((.+\n)*)'),
        # re.compile(r'List of k points\s+((.+\n)*)')
    ]
    unitcell_info = {
        'unitcell_geometry':None,
        'number_of_symmetry_operations':None,
        'number_of_valence_electrons':None,
        'number_of_k_points':None,
        'number_of_k_points_in_ibz':None,
        # 'k_points_in_path':None,
        # 'list_of_k_points':None,
    }

    for key, pattern in zip(unitcell_info.keys(),unitcell_patterns):
        match = pattern.search(contents)
        if match:
            unitcell_info[key]= re.sub(' +|\n',' ' ,match.group(1).strip())
    
    unitcell_info['unitcell_geometry'] = np.array(unitcell_info['unitcell_geometry'].split()).reshape(-1,6)
    unitcell_info['number_of_symmetry_operations'] = int(unitcell_info['number_of_symmetry_operations'])
    unitcell_info['number_of_valence_electrons'] = int(unitcell_info['number_of_valence_electrons'])
    unitcell_info['number_of_k_points'] = int(unitcell_info['number_of_k_points'])
    unitcell_info['number_of_k_points_in_ibz'] = int(unitcell_info['number_of_k_points_in_ibz'])

    # unitcell_info['k_points_in_path'] = np.array(unitcell_info['k_points_in_path'].split()).reshape(-1,3)
    # unitcell_info['list_of_k_points'] = np.array(unitcell_info['list_of_k_points'].split()).reshape(-1,4)
    return unitcell_info



def spexout_parser(spexout_file):
    """
    spexout_file: a file object
    returns: a dictionary with the parsed data
    Parse SPEX output file and return a dictionary with the data.
    """
    run_info = get_run_info(spexout_file)
    basic_info = get_basic_info(spexout_file)
    unitcell_info = get_unitcell_info(spexout_file)
    return {**run_info, **basic_info, **unitcell_info}

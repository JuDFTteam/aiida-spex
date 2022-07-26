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

import re
# from io import StringIO

import numpy as np
import pandas as pd


def get_run_info(contents):
    run_patterns = [
        re.compile(r"Version\s*(\d+[.]\d+\s* \(.*\))"),
        re.compile(r"Execution time:\s*(.*)"),
        re.compile(r"Compiler:\s*(.*)"),
        re.compile(r"Hostname:\s*(.*)"),
        re.compile(r"Interfaced to \s*(.*)"),
        re.compile(r"MPI:\s*(.*)"),
        re.compile(r"Timing:\s*([0-9]+)\n")
    ]
    run_info = {
        "version": None,
        "execution_time": None,
        "compiler": None,
        "hostname": None,
        "interfaced_to": None,
        "mpi": None,
        'walltime': None
    }
    for key, pattern in zip(run_info.keys(), run_patterns):
        match = pattern.search(contents)
        if match:
            run_info[key] = re.sub(" +|\n", " ", match.group(1).strip())

    run_info['walltime'] =int(run_info['walltime'])

    return run_info

def get_err_info(contents):
    '''
    Get info/warning/error information from out.error file.
    '''
    err_info = {}
    err_info['spex_errors']  = re.findall(r"SPEX-ERROR.*", contents)
    err_info['spex_warnings'] = re.findall(r'SPEX-WARNING.*', contents)
    err_info['spex_info'] = re.findall(r'SPEX-INFO.*', contents)
    return err_info


def get_basic_info(contents):
    basic_info = {
        "number_of_spins": None,
        "number_of_centers": None,
        "number_of_types": None,
        "equivalent_atoms": None,
        "lattice_parameter": None,
        "primitive_vectors": None,
        "unit_cell_volume": None,
        "reciprocal_vectors": None,
        "reciprocal_volume": None,
        "reciprocal_cutoff": None,
    }

    basic_patterns = [
        re.compile(r"Number of spins\s*=\s*(\d+)"),
        re.compile(r"centers\s*=\s*(\d+)"),
        re.compile(r"types\s*=\s*(\d+)"),
        re.compile(r"equivalent atoms\s*=\s*(.*)"),
        re.compile(r"Lattice parameter\s*=\s*(\d+.\d+)"),
        re.compile(r"Primitive vectors\s*=((\s*.*){3})"),
        re.compile(r"Unit-cell volume\s*=\s*(\d+.\d+)"),
        re.compile(r"Reciprocal vectors\s*=((\s*.*){3})"),
        re.compile(r"Reciprocal volume\s*=\s*(\d+.\d+)"),
        re.compile(r"Reciprocal cutoff\s*=\s*(\d+.\d+)"),
    ]
    for key, pattern in zip(basic_info.keys(), basic_patterns):
        match = pattern.search(contents)
        if match:
            basic_info[key] = re.sub(" +|\n", " ", match.group(1).strip())
    basic_info["primitive_vectors"] = np.array(
        basic_info["primitive_vectors"].split(), dtype=float
    ).reshape(3, 3)
    basic_info["reciprocal_vectors"] = np.array(
        basic_info["reciprocal_vectors"].split(), dtype=float
    ).reshape(3, 3)
    basic_info["number_of_spins"] = int(basic_info["number_of_spins"])
    basic_info["number_of_centers"] = int(basic_info["number_of_centers"])
    basic_info["number_of_types"] = int(basic_info["number_of_types"])
    basic_info["unit_cell_volume"] = float(basic_info["unit_cell_volume"])
    basic_info["reciprocal_volume"] = float(basic_info["reciprocal_volume"])
    return basic_info


def get_unitcell_info(contents):
    # basic_info = get_basic_info(contents)
    # TODO instead of all the info just parse the centers

    list_of_k_points =[]
    k_points_in_ibz = []

    # k-point list from the spex.out file
    pattern = re.compile(r"List of k points\s+((.+\n)*)")
    match = pattern.search(contents)

    if match:
        list_of_k_points = re.sub(" +|\n", " ", match.group(1).strip())
        list_of_k_points = np.array(list_of_k_points.split()).reshape(-1, 4)

    # k-points in the IBZ
    pattern = re.compile(r"(\d+)\s+\(((?:-?\d+\.\d+\,?){3})\)\s+\[\s?((?:\s?-?\d+\.\d+\,?\s?){3})\]\s+eq:\s+(\d+)\n")
    match = pattern.findall(contents)

    if match:
        k_points_in_ibz = np.array(match)
        k_points_in_ibz = pd.DataFrame(k_points_in_ibz, columns=['k_point_number', 'k_point_coordinates', 'k_point_rlat', 'equivalant_k_points'])

    pattern = re.compile(r"centers\s*=\s*(\d+)")
    number_of_centers = pattern.search(contents).group(1)
    unitcell_patterns = [
        re.compile(r"#\s+Ty\s+El\s+Coord.\s*((\s*.*){" + number_of_centers + r"})"),
        re.compile(r"Number of symmetry operations\s*=\s*(\d+)"),
        re.compile(r"Number of valence electrons:\s*(\d+)"),
        re.compile(r"Number of k points:\s+(\d+)"),
        re.compile(r"in IBZ:\s+(\d+)")
    ]
    unitcell_info = {
        "unitcell_geometry": None,
        "number_of_symmetry_operations": None,
        "number_of_valence_electrons": None,
        "number_of_k_points": None,
        "number_of_k_points_in_ibz": None,
        "list_of_k_points": [],
        "k_points_in_ibz": []

    }

    for key, pattern in zip(unitcell_info.keys(), unitcell_patterns):
        match = pattern.search(contents)
        if match:
            unitcell_info[key] = re.sub(" +|\n", " ", match.group(1).strip())

    unitcell_info["unitcell_geometry"] = np.array(
        unitcell_info["unitcell_geometry"].split()
    ).reshape(-1, 6)
    unitcell_info["number_of_symmetry_operations"] = int(
        unitcell_info["number_of_symmetry_operations"]
    )
    unitcell_info["number_of_valence_electrons"] = int(
        unitcell_info["number_of_valence_electrons"]
    )
    unitcell_info["number_of_k_points"] = int(unitcell_info["number_of_k_points"])
    unitcell_info["number_of_k_points_in_ibz"] = int(
        unitcell_info["number_of_k_points_in_ibz"]
    )

    unitcell_info["list_of_k_points"] = list_of_k_points
    unitcell_info["k_points_in_ibz"] = k_points_in_ibz.to_dict("list")

    return unitcell_info

def get_out_info(content):
    is_gap =False
    is_fermi=True
    is_max = False
    out_info={}
    energy_unit = "Ha"

    # Energy gap
    pattern = re.compile(r"Energy gap:\s+(-?\d+\.\d+)\s+Ha")
    match = pattern.findall(content)
    if match:
        is_gap = True
        out_info["energy_gap"] = np.array(match).astype(float)
    
    #Fermi energy
    pattern = re.compile(r"Fermi energy:\s+(-?\d+\.\d+)\s+Ha")
    match = pattern.findall(content)
    if match:
        is_fermi = True
        out_info["fermi_energy"] = np.array(match).astype(float)
    
    #Maximal energy
    pattern = re.compile(r"Maximal energy:\s+(-?\d+\.\d+)\s+Ha")
    match = pattern.findall(content)
    if match:
        is_max = True
        out_info["maximal_energy"] = np.array(match).astype(float)
    
    if any([is_gap, is_fermi, is_max]):
        out_info["energy_unit"] = energy_unit

    return out_info



def spexout_parser(spexout_file):
    """
    spexout_file: a file object
    returns: a dictionary with the parsed data
    Parse SPEX output file and return a dictionary with the data.
    """
    run_info = get_run_info(spexout_file)
    basic_info = get_basic_info(spexout_file)
    unitcell_info = get_unitcell_info(spexout_file)
    out_info = get_out_info(spexout_file)
    return {**run_info, **basic_info, **unitcell_info, **out_info}

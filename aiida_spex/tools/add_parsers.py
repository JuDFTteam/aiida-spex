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

from aiida.orm import Dict
from aiida.common.exceptions import NotExistent
import re
import numpy as np
import pandas as pd
from io import StringIO

# Parser registry defines a parser_name and a file/list of files to be parsed.
# The parser name is used to identify the parser in the SpecificParser class.
parser_registry = {
    "project": "spex.binfo",
    "gw": "spex.out",
    "ks": "spex.out",
    "dos": "spex.dos",
    "dielec": "dielecR",
    "plussoc": "spex.out",
}


def project_parser(parser_name, content, out_dict=None):
    """
    Parses the spex.binfo file for a project calculation.
    """
    return_dict = {}
    atoms = np.array(out_dict["unitcell_geometry"])[:, 2]
    binfo = pd.read_csv(
        StringIO(content),
        delim_whitespace=True,
        comment="#",
        skip_blank_lines=True,
        header=None,
    )
    binfo.columns = ["band", "energy"] + [
        f"{i}_{l}"
        for i, l in [(i, l) for i in atoms for l in ["s", "p", "d", "f", "g"]]
    ]
    pattern = re.compile(r"k point \d+: \((.*)\)")
    kpoints = pattern.findall(content)
    kpoints = [list(map(float, kpoint.split(","))) for kpoint in kpoints]

    return_dict = {
        "results": binfo.to_dict("list"),
        "kpoints": kpoints,
        "parser": parser_name,
    }

    return return_dict


def get_gw_energies(kpt_energies, k_point, out_dict=None):
    """
    Create a dataframe from the gw energies.
    """
    df = pd.read_csv(StringIO(kpt_energies), sep="\s+", header=None)
    diag_r = pd.DataFrame()
    diag_i = pd.DataFrame()
    diag_r[
        ["Bd", "vxc", "sigmax", "sigmac", "Z", "KS", "HF", "GW", "lin/dir"]
    ] = df.iloc[::2]
    diag_i[["sigmac", "Z", "GW", "lin/dir"]] = df.iloc[1::2].dropna(axis=1, how="all")
    diag_i.reset_index(drop=True, inplace=True)
    diag_r.reset_index(drop=True, inplace=True)
    diag_r["Bd"] = diag_r["Bd"].astype(int)
    diag_i["Bd"] = diag_r["Bd"]
    diag_r["kpoint"] = int(k_point)
    diag_i["kpoint"] = int(k_point)
    if int(out_dict["number_of_spins"]) == 2:
        spins = np.ones(diag_r.shape[0], dtype=int)
        spins[1::2] += 1
        diag_r["spin"] = spins
        diag_i["spin"] = spins
    else:
        diag_r["spin"] = 1
        diag_i["spin"] = 1

    return diag_r, diag_i


def gw_parser(parser_name, content, out_dict=None):
    """
    Parses the spex.out file for a GW calculation.
    """
    energy_eigenvalues = {}
    if "list_of_k_points" in out_dict:
        list_of_k_points = out_dict["list_of_k_points"]
    else:
        raise ValueError("Could not find the k-point list in the output file/output dictionary.")


    # Energy eigen values
    r_energies = []
    i_energies = []
    for k_point in list_of_k_points[:, 0]:
        pattern = re.compile(
            r"#{2,}\n#{2,} K POINT:\s+"
            + k_point
            + r"\s+#{2,}\n#{2,}\n{3}-{3}\sDIAGONAL ELEMENTS \[eV\] -{3}\n{2}\sBd\s+vxc\s+sigmax\s+sigmac\s+Z\s+KS\s+HF\s+GW\s+lin/dir\s\n((.+\n)*)",
            re.MULTILINE,
        )
        kpt_energies = pattern.search(content).group(1)
        rdf, idf = get_gw_energies(kpt_energies, k_point, out_dict)
        r_energies.append(rdf)
        i_energies.append(idf)

    energies_real = pd.concat(r_energies, axis=0, ignore_index=True)
    energies_imag = pd.concat(i_energies, axis=0, ignore_index=True)

    energy_eigenvalues["real"] = energies_real.to_dict("list")
    energy_eigenvalues["imag"] = energies_imag.to_dict("list")
    
    return_dict = {
        "results": energy_eigenvalues,
        "parser": parser_name,
    }
    return return_dict


def get_ks_energies(kpt_energies, k_point, out_dict=None):
    """
    Create a dataframe from the ks energies.
    """
    df = pd.read_csv(StringIO(kpt_energies), sep="\s+", header=None)
    diag_r = pd.DataFrame()
    diag_r[["Bd", "vxc", "KS"]] = df.iloc[::2]
    diag_r.reset_index(drop=True, inplace=True)
    diag_r["Bd"] = diag_r["Bd"].astype(int)
    diag_r["kpoint"] = int(k_point)
    if int(out_dict["number_of_spins"]) == 2:
        spins = np.ones(diag_r.shape[0], dtype=int)
        spins[1::2] += 1
        diag_r["spin"] = spins
    else:
        diag_r["spin"] = 1

    return diag_r


def ks_parser(parser_name, content, out_dict=None):
    """
    Parser for the KS energies
    """
    if "list_of_k_points" in out_dict:
        list_of_k_points = out_dict["list_of_k_points"]
    else:
        raise ValueError("Could not find the k-point list in the output file/output dictionary.")

    r_energies = []
    for k_point in list_of_k_points[:, 0]:
        pattern = re.compile(
            r"#{2,}\n#{2,} K POINT:\s+"
            + k_point
            + r"\s+#{2,}\n#{2,}\n{3}-{3}\sDIAGONAL ELEMENTS \[eV\] -{3}\n{2}\sBd\s+vxc\s+KS\s\n((.+\n)*)",
            re.MULTILINE,
        )
        kpt_energies = pattern.search(content).group(1)
        rdf = get_ks_energies(kpt_energies, k_point, out_dict)
        r_energies.append(rdf)

    energies_real = pd.concat(r_energies, axis=0, ignore_index=True)

    return_dict = {
        "results": energies_real.to_dict("list"),
        "parser": parser_name,
    }
    return return_dict


def dielec_parser(parser_name, content, out_dict=None):
    """
    Parses the dielectric function from the dielecR output file.
    """
    dielec_df = pd.read_csv(
        StringIO(content),
        sep="\s+",
        header=None,
        comment="#",
        names=["Frequency", "Real", "Imaginary"],
    )

    p_lattvec = re.compile(r"# lattvec:\s*(.*)")
    match = p_lattvec.search(content)
    lattvec = match.group(1)

    p_kpoint = re.compile(r"# k point:\s*(.*)")
    match = p_kpoint.findall(content)
    kpoint = match
    if not kpoint:
        kpoint = []

    p_kindex = re.compile(r"# k index:\s*(.*)")
    match = p_kindex.findall(content)
    kindex = match
    if not kindex:
        kindex = []

    p_spin = re.compile(r"# spin:\s*(.*)")
    match = p_spin.findall(content)
    spin = match
    if not spin:
        spin = []

    return_dict = {
        "results": dielec_df.to_dict("list"),
        "lattvec": lattvec,
        "kpoint": kpoint,
        "kindex": kindex,
        "spin": spin,
        "parser": parser_name,
    }
    return return_dict


def plussoc_parser(parser_name, content, out_dict=None):
    """
    Parses the PLUSSOC output file.
    """
    pattern = re.compile(r"K point\s+(\d+)\s+->\s+\d+\n((?:\s+\d.*\n){1,})((?:.+\n)*)")
    matches = pattern.findall(content)
    kpt, eq_kpt, eigenvalues = [], [], []
    for match in matches:
        t_match = [re.sub("\ +|\n", " ", w) for w in match]
        kpt.append(int(t_match[0].strip()))
        eq_kpt.append(t_match[1].strip())
        eigenvalues.append(t_match[2].strip())
    plussoc_df = pd.DataFrame(
        data={
            "k_point_number": kpt,
            "equivalant_k_points": eq_kpt,
            "eigenvalues": eigenvalues,
        }
    )
    plussoc_df["k_point_number"] = plussoc_df["k_point_number"].astype(int)
    plussoc_df["equivalant_k_points"] = plussoc_df["equivalant_k_points"].apply(
        lambda x: np.array(x.split()).reshape(-1, 4)
    )
    plussoc_df["eigenvalues"] = plussoc_df["eigenvalues"].apply(
        lambda x: np.array(x.split()).astype(float)
    )

    return_dict = {
        "results": plussoc_df.to_dict("list"),
        "parser": parser_name,
    }
    return return_dict


def spexfile_parse(parser_name, content, out_dict=None):
    """
    Using the parser_name provided to the class, this function calles the method that corresponds to the parser_name and returns a dictionary of results
    :return: a dictionary.
    """
    if parser_name == "project":
        return project_parser(parser_name, content, out_dict)
    elif parser_name == "gw":
        return gw_parser(parser_name, content, out_dict)
    elif parser_name == "dielec":
        return dielec_parser(parser_name, content, out_dict)
    elif parser_name == "plussoc":
        return plussoc_parser(parser_name, content, out_dict)
    else:
        return {}

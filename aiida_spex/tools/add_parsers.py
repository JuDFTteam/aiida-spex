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
    "dos": "spex.dos",
    "dielec": "dielecR",
}


def project_parser(parser_name, out_dict, content):
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
        "binfo": binfo.to_dict("list"),
        "kpoints": kpoints,
        "parser": parser_name,
    }

    return return_dict


def get_gw_energies(kpt_energies, k_point, out_dict):
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


def gw_parser(parser_name, out_dict, content):
    pattern = re.compile(r"List of k points\s+((.+\n)*)")
    match = pattern.search(content)

    if match:
        list_of_k_points = re.sub(" +|\n", " ", match.group(1).strip())
    else:
        raise ValueError("Could not find the k-point list in the output file")

    list_of_k_points = np.array(list_of_k_points.split()).reshape(-1, 4)

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

    return_dict = {
        "e_real": energies_real.to_dict("list"),
        "e_imag": energies_imag.to_dict("list"),
        "parser": parser_name,
    }
    return return_dict


def spexfile_parse(parser_name, out_dict, content):
    """
    Using the parser_name provided to the class, this function calles the method that corresponds to the parser_name and returns a dictionary of results
    :return: a dictionary.
    """
    if parser_name == "project":
        return project_parser(parser_name, out_dict, content)
    elif parser_name == "gw":
        return gw_parser(parser_name, out_dict, content)
    else:
        return {}

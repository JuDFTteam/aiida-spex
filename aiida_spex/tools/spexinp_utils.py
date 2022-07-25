import sys
from aiida_spex import __version__ as aiida_spex_version
import pandas as pd
from pydantic import BaseModel, ValidationError, validator, StrictStr, StrictInt, StrictFloat, Extra
from typing import (
    Deque, Dict, FrozenSet, List, Optional, Sequence, Set, Tuple, Union
)

keyword_reference = {
    "global": [
        "CUSTOM",
        "ALIGNBD",
        "BANDOMIT",
        "BLOECHL",
        "BZ",
        "CHKMISM",
        "CHKOLAP",
        "CORES",
        "CORESOC",
        "CUTZERO",
        "DELTAEX",
        "ENERGY",
        "FIXPHASE",
        "GAUSS",
        "IBC",
        "ITERATE",
        "JOB",
        "KPT",
        "KPTPATH",
        "MEM",
        "MPIKPT",
        "MPISPLIT",
        "NBAND",
        "NOSYM",
        "PLUSSOC",
        "RESTART",
        "STOREBZ",
        "TIMING",
        "TRSOFF",
        "WRITE",
        "WRTKPT",
    ],
    "sections": {
        "ANALYZE": ["DIPOLE", "KINETIC", "MTACCUR", "DOS", "PROJECT"],
        "COULOMB": ["CHKCOUL", "LEXP", "MULTIPOLE", "NOSTORE", "STEPRAD", "TSTCOUL"],
        "LAPW": ["EPAR", "GCUT", "LCUT", "LO"],
        "MBASIS": [
            "ADDBAS",
            "CHKPROD",
            "GCUT",
            "LCUT",
            "NOAPW",
            "OPTIMIZE",
            "SELECT",
            "TOL",
            "WFADJUST",
        ],
        "SENERGY": [
            "ALIGNVXC",
            "CONTINUE",
            "CONTOUR",
            "DIVLOG",
            "FREQINT",
            "MESH",
            "MPIBLK",
            "MPISYM",
            "ORDER",
            "SMOOTH",
            "SPECTRAL",
            "VXC",
            "ZERO",
        ],
        "SUSCEP": [
            "DISORDER",
            "FPADE",
            "FSPEC",
            "HILBERT",
            "HUBBARD",
            "MULTDIFF",
            "PLASMA",
            "TETRAF",
            "WGHTTHR",
        ],
        "WANNIER": [
            "BACKFOLD",
            "CUTGOLD",
            "DISENTGL",
            "FROZEN",
            "INTERPOL",
            "IRREP",
            "MAXIMIZE",
            "ORBITALS",
            "PLOT",
            "RSITE",
            "SUBSET",
            "UREAD",
            "WBLOCH",
            "WSCALE",
        ],
        "WFPROD": ["APPROXPW", "FFT", "LCUT", "MINCPW", "MPIMT", "MPIPW"],
    },
}
necessary_keys = ["BZ"]
nonempty_keys = ["BZ", "KPT", "KPTPATH"] + list(keyword_reference["sections"].keys())
job_spectra = ["DIELEC", "SUSCEP", "SUSCEPR", "SCREEN", "SCREENW"]


def check_parameters(parameters):
    if parameters:
        global_keys = list(map(lambda x: x.upper(), parameters.keys()))
        if not all(elem in global_keys for elem in necessary_keys):
            # print(f"Some parameters are missing check docuentation for  necessary parameters")
            return False
        for key in parameters:
            key_upper = key.upper()
            sections = keyword_reference["sections"]
            sections_list = list(sections.keys())
            if key_upper in nonempty_keys:
                if not parameters[key]:
                    # print(f"{key_upper} cannot be empty")
                    return False

            if key_upper not in keyword_reference["global"] + sections_list:
                # print(f"'{key_upper}' not a valid keyword")
                return False

            if key_upper in sections:
                for key2 in parameters[key]:
                    key2_upper = key2.upper()
                    if key2_upper not in sections[key_upper]:
                        # print(f"'{key2_upper}' is not a vaid keyword for the section {key_upper}")
                        return False
        return True

    else:
        print("No parameters provided")
        return False


def format_job(val):
    """
    Format the JOB line for the spex.inp file
    """
    job_string = "JOB "
    if val:
        for (
            key2,
            val2,
        ) in val.items():  # key2=KS, DIELEC, val2 = { '1': {'range':[],'step':0.01}}
            if val2:
                job_string += f"{key2} "
                if key2 in job_spectra:
                    for (
                        key3,  #'1','R', etc,
                        val3,  # {'range':[],'step':0.01}
                    ) in val2.items():  # key3=R, val3={range:..., step:...}
                        spectra_range = "{"
                        if isinstance(val3["range"], list):
                            s_range = val3["range"]
                            start = str(s_range[0])
                            end = str(s_range[1])
                            spectra_range += f"{start}:{end}"
                        else:
                            print(f"Spectral function {key2} must have a range")
                            sys.exit(1)
                        spectra_range += f",{val3['step']}" + "}"
                        job_string += f"{key3.upper()}:{spectra_range}"
                else:
                    for key3, val3 in val2.items():  # key3=R, val3=[...]
                        if isinstance(val3, list):
                            for val4 in val3:
                                band_range = []
                                if isinstance(val4, list):
                                    start = str(val4[0])
                                    end = str(val4[1])
                                    band_range.append(f"{start}-{end}")
                                else:
                                    band_range.append(str(val4))
                            job_string += (
                                f"{key3.upper()}:({','.join(map(str,band_range))}) "
                            )
        return job_string + "\n"
    else:
        return job_string + "\n"


def format_section(key, val):
    section_string = "SECTION " + f"{key}\n"
    for key2, val2 in val.items():
        section_string += f"{key2.upper()} {val2.upper()}\n"
    return section_string + "END\n"


def format_kpt(val):
    kpt_string = "KPT "
    for k, v in val.items():
        kpt_string += f"{k}=({v[0]},{v[1]},{v[2]}) "
    return kpt_string + "\n"


def format_kptpath(val):
    if "npoints" in val.keys():
        npoints = val["npoints"]
        kptpath_string = "KPTPATH " + f"({','.join(map(str,val['path']))}) {npoints}\n"
    else:
        kptpath_string = "KPTPATH " + f"({','.join(map(str,val['path']))}) \n"
    return kptpath_string

def format_energy(val):
    if 'filename' in val.keys():
        filename = val['filename']
        energy_string = "ENERGY " + f"{filename}\n"
    elif isinstance(val, str):
        energy_string = "ENERGY " + f"{val}\n"
    return energy_string

def format_spex_inp(key, val):
    spex_inp_string = ""
    if isinstance(val, dict):
        if val:
            if key == "KPT":
                spex_inp_string += format_kpt(val)
            elif key == "KPTPATH":
                spex_inp_string += format_kptpath(val)
            elif key in keyword_reference["sections"]:
                spex_inp_string += format_section(key, val)
            elif key == "JOB":
                spex_inp_string += format_job(val)
            elif key == "ENERGY":
                spex_inp_string += format_energy(val)
            else:
                print(f"{key} format not implemented use CUSTOM key instead")
                sys.exit(1)
        else:
            spex_inp_string += f"{key}\n"
    elif isinstance(val, list):
        if val:
            if key == "BZ":
                spex_inp_string += f"{key} {val[0]} {val[1]} {val[2]}\n"
        else:
            spex_inp_string += f"{key}\n"
    return spex_inp_string


def make_spex_inp(parameters):
    """
    Make a spex input file from a dictionary of parameters
    parameters: dictionary of parameters
    Returns: spex input file in a single string format
    """
    spex_inp_string = (
        f"# SPEX input file generated by aiida-spex v{aiida_spex_version}\n"
    )
    for key, val in parameters.items():
        key_upper = key.upper()
        if key_upper != "CUSTOM":
            if isinstance(val, str):
                spex_inp_string += f"{key_upper} {val}\n"
            if isinstance(val, int):
                spex_inp_string += f"{key_upper} {val}\n"
            if isinstance(val, float):
                spex_inp_string += f"{key_upper} {val}\n"
            if isinstance(val, dict) or isinstance(val, list):
                spex_inp_string += format_spex_inp(key_upper, val)
        if key_upper == "CUSTOM":
            # TODO report the custom is not validated
            spex_inp_string += f"{val}\n"
    return spex_inp_string


def make_energy_inp(energy_inp_dict, with_e='GW'):
    """
    Make a energy input file from a dictionary of parameters
    parameters: dictionary of parameters
    Returns: energy input file in a single string format
    """
    real_energy_inp_dict = energy_inp_dict["e_real"]
    real_energy_inp_df = pd.DataFrame.from_dict(real_energy_inp_dict)
    energy_keys_list = list(real_energy_inp_df.columns)
    if with_e not in energy_keys_list:
        raise ValueError(f"{with_e} is not in the parsed output file")

    real_energy_inp_string = f"# ENERGY input file generated by aiida-spex v{aiida_spex_version}\n# Energy = {with_e}\n\n#  n  k s    Energy\n"
    for i, row in real_energy_inp_df.iterrows():
        real_energy_inp_string += f"  {int(row['Bd']):d} {int(row['kpoint']):2d} {int(row['spin']):d} {row[with_e]:9.5f}\n"
    return real_energy_inp_string



class SpexInputValidation(BaseModel, extra=Extra.forbid):
    """
    Validate the input parameters of the SpexInput class
    """
    bz: List[StrictInt]
    chkmism: Optional[None] = None
    chkolap: Optional[None] = None
    coresoc: Optional[None] = None
    cutzero: Optional[None] = None
    deltaex: Optional[StrictStr] = None
    energy: Optional[Union[Dict, StrictStr]] = None
    fixphase: Optional[None] = None
    gauss: Optional[List[StrictFloat]] = None
    iterate: Optional[StrictStr] = None
    kpt: Optional[Dict[StrictStr, List[Union[StrictFloat, StrictInt]]]] = None
    kptpath: Optional[List[StrictStr]] = None
    mem: Optional[StrictStr] = None
    mpikpt: Optional[None] = None
    mpisplit: Optional[StrictStr] = None
    nband: Optional[Union[StrictInt, StrictStr, StrictFloat]] = None
    nosym: Optional[None] = None
    plussoc: Optional[None] = None
    restart: Optional[None] = None
    storebz: Optional[None] = None
    timing: Optional[None] = None
    trsoff: Optional[None] = None
    write: Optional[None] = None
    wrtkpt: Optional[None] = None
    job: Optional[Dict] = None
    analyze: Optional[Dict] = None
    coulomb: Optional[Dict] = None
    lapw: Optional[Dict] = None
    mbasis: Optional[Dict] = None
    senergy: Optional[Dict] = None
    suscep: Optional[Dict] = None
    wannier: Optional[Dict] = None
    wfprod: Optional[Dict] = None
    custom: Optional[StrictStr] = None

ValidationError = ValidationError
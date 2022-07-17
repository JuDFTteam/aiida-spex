from aiida.orm import Dict
from aiida.common.exceptions import NotExistent
import re
import numpy as np
import pandas as pd
from io import StringIO

# Parser registry defines a parser_name and a file/list of files to be parsed.
# The parser name is used to identify the parser in the SpecificParser class.
parser_registry = {"project": "spex.binfo"}


def project_parser(parser_name, out_dict, content):
    atoms=np.array(out_dict['unitcell_geometry'])[:,2]
    binfo = pd.read_csv(
                StringIO(content), 
                delim_whitespace=True,
                comment="#",
                skip_blank_lines=True,
                header=None
                )
    binfo.columns = [ "band", "energy"] + [f"{i}_{l}" for i,l in [(i,l) for i in atoms for l in ["s","p","d","f","g"]]]
    return {"binfo": binfo.to_dict('list'), "parser_name": parser_name}


def spexfile_parse(parser_name, out_dict, content):
    """
    Using the parser_name provided to the class, this function calles the method that corresponds to the parser_name and returns a dictionary of results
    :return: a dictionary.
    """
    if parser_name == "project":
        return project_parser(parser_name, out_dict, content)
    else:
        return {}

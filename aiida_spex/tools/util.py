# -*- coding: utf-8 -*-
###############################################################################
# Copyright (c), Forschungszentrum Jülich GmbH, IAS-1/PGI-1, Germany.         #
#                All rights reserved.                                         #
# This file is part of the AiiDA-FLEUR package.                               #
#                                                                             #
# The code is hosted on GitHub at https://github.com/JuDFTteam/aiida-fleur    #
# For further information on the license, see the LICENSE.txt file            #
# For further information please visit http://www.flapw.de or                 #
# http://aiida-fleur.readthedocs.io/en/develop/                               #
###############################################################################
"""
This file is just were to hardcode some schema file paths
"""

from __future__ import absolute_import
import os

PACKAGE_DIRECTORY = os.path.dirname(os.path.abspath(__file__))

def get_internal_search_paths():
    """
    returns all abs paths to dirs where schema files might be
    """
    schema_paths = [PACKAGE_DIRECTORY]
    return schema_paths

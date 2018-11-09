# -*- coding: utf-8 -*-
###############################################################################
# Copyright (c), Forschungszentrum Jülich GmbH, IAS-1/PGI-1, Germany.         #
#                All rights reserved.                                         #
# This file is part of the AiiDA-SPEX package.                                #
#                                                                             #
# The code is hosted on GitHub at https://github.com/JuDFTteam/aiida-spex     #
# For further information on the license, see the LICENSE.txt file            #
# For further information please visit http://www.flapw.de or                 #
# http://aiida-spex.readthedocs.io/en/develop/                                #
###############################################################################

'''
AiiDA-SPEX
'''
from aiida.parsers.exceptions import OutputParsingError

#mainly created this Outputparsing error, that the user sees, that it comes from parsing a Spex calculation.
class SpexOutputParsingError(OutputParsingError):
    pass
    # if you want to do something special here do it

# -*- coding: utf-8 -*-
###############################################################################
# Copyright (c), Forschungszentrum Jülich GmbH, IAS-1/PGI-1, Germany.         #
#                All rights reserved.                                         #
# This file is part of the AiiDA-FLEUR package.                               #
#                                                                             #
# The code is hosted on GitHub at https://github.com/broeder-j/aiida-fleur    #
# For further information on the license, see the LICENSE.txt file            #
# For further information please visit http://www.flapw.de or                 #
# http://aiida-fleur.readthedocs.io/en/develop/                               #
###############################################################################

import pytest

@pytest.mark.usefixtures("aiida_env")
class TestAiida_spex_entrypoints:
    """
    tests all the entry points of the aiida spex package. Therefore if the package is 
    reconized by AiiDA and installed right. 
    """
    
    # Calculations

    def test_spex_calculation_entry_point(aiida_env):
        from aiida.orm import CalculationFactory
        
        spex_calculation = CalculationFactory('spex.spex')
        assert spex_calculation is not None
    
    
    # Parsers

    def test_spex_parser_entry_point(aiida_env):
        from aiida.parsers import ParserFactory
        from aiida_spex.parsers.spex import SpexParser

        parser = ParserFactory('spex.spexparser')
        assert parser == SpexParser


    # Workflows/workchains

    def test_spex_scf_wc_entry_point(aiida_env):
        from aiida.orm import WorkflowFactory
        from aiida_spex.workflows.scf_gw import spex_scf_gw_wc
        
        workflow = WorkflowFactory('spex.scf_gw')
        assert workflow == spex_scf_gw_wc
        
    def test_spex_gw0_wc_entry_point(aiida_env):
        from aiida.orm import WorkflowFactory
        from aiida_spex.workflows.gw0 import spex_gw0_wc
        
        workflow = WorkflowFactory('spex.gw0')
        assert workflow == spex_gw0_wc
        
    def test_fleur_band_wc_entry_point(aiida_env):
        from aiida.orm import WorkflowFactory
        from aiida_spex.workflows.band import spex_band_wc
        
        workflow = WorkflowFactory('spex.band')
        assert workflow == spex_band_wc


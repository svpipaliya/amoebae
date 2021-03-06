#!/usr/bin/env python3
"""PyTest tests for the afa_to_nex.py module.
"""
import os
import sys
sys.path.append(os.path.join(os.path.dirname(sys.path[0]),'amoebaelib')) # Customize.

from afa_to_nex import \
determine_alphabet, \
afa_to_nex, \
nex_to_afa, \
delete_extra_mesquite_lines, \
nex_to_phylip, \
nex_to_mbnex, \
align_fa, \
align_all_fa, \
align_one_fa


def test_determine_alphabet():  # ***Incomplete test
    """Test the determine_alphabet function in the afa_to_nex.py file.
    """
    ##########################
    # Arrange.
    filepath = "filepath"

    ##########################
    # Act.
    #x = determine_alphabet(filepath)

    ##########################
    # Assert.
    assert True == True # ***Temporary.



def test_afa_to_nex():  # ***Incomplete test
    """Test the afa_to_nex function in the afa_to_nex.py file.
    """
    ##########################
    # Arrange.
    infilepath = "infilepath"
    outfilepath = "outfilepath=None"

    ##########################
    # Act.
    #x = afa_to_nex(infilepath,
    #		outfilepath)

    ##########################
    # Assert.
    assert True == True # ***Temporary.



def test_nex_to_afa():  # ***Incomplete test
    """Test the nex_to_afa function in the afa_to_nex.py file.
    """
    ##########################
    # Arrange.
    infilepath = "infilepath"
    outfilepath = "outfilepath"

    ##########################
    # Act.
    #x = nex_to_afa(infilepath,
    #		outfilepath)

    ##########################
    # Assert.
    assert True == True # ***Temporary.



def test_delete_extra_mesquite_lines():  # ***Incomplete test
    """Test the delete_extra_mesquite_lines function in the afa_to_nex.py file.
    """
    ##########################
    # Arrange.
    infilepath = "infilepath"

    ##########################
    # Act.
    #x = delete_extra_mesquite_lines(infilepath)

    ##########################
    # Assert.
    assert True == True # ***Temporary.



def test_nex_to_phylip():  # ***Incomplete test
    """Test the nex_to_phylip function in the afa_to_nex.py file.
    """
    ##########################
    # Arrange.
    infilepath = "infilepath"
    outfilepath = "outfilepath"

    ##########################
    # Act.
    #x = nex_to_phylip(infilepath,
    #		outfilepath)

    ##########################
    # Assert.
    assert True == True # ***Temporary.



def test_nex_to_mbnex():  # ***Incomplete test
    """Test the nex_to_mbnex function in the afa_to_nex.py file.
    """
    ##########################
    # Arrange.
    infilepath = "infilepath"
    outfilepath = "outfilepath"
    mrbayescodeblocks = "mrbayescodeblocks"

    ##########################
    # Act.
    #x = nex_to_mbnex(infilepath,
    #		outfilepath,
    #		mrbayescodeblocks)

    ##########################
    # Assert.
    assert True == True # ***Temporary.



def test_align_fa():  # ***Incomplete test
    """Test the align_fa function in the afa_to_nex.py file.
    """
    ##########################
    # Arrange.
    infilepath = "infilepath"
    outfilepath = "outfilepath"
    aamatrix_path = "aamatrix_path"
    program = "program='muscle'"

    ##########################
    # Act.
    #x = align_fa(infilepath,
    #		outfilepath,
    #		aamatrix_path,
    #		program)

    ##########################
    # Assert.
    assert True == True # ***Temporary.



def test_align_all_fa():  # ***Incomplete test
    """Test the align_all_fa function in the afa_to_nex.py file.
    """
    ##########################
    # Arrange.
    indirpath = "indirpath=None"
    outdirpath = "outdirpath=None"

    ##########################
    # Act.
    #x = align_all_fa(indirpath,
    #		outdirpath)

    ##########################
    # Assert.
    assert True == True # ***Temporary.



def test_align_one_fa():  # ***Incomplete test
    """Test the align_one_fa function in the afa_to_nex.py file.
    """
    ##########################
    # Arrange.
    infilepath = "infilepath"
    outdirpath = "outdirpath=None"
    program = "program=None"
    aamatrix_path = "aamatrix_path=None"

    ##########################
    # Act.
    #x = align_one_fa(infilepath,
    #		outdirpath,
    #		program,
    #		aamatrix_path)

    ##########################
    # Assert.
    assert True == True # ***Temporary.



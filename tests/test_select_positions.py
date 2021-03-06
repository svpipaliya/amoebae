#!/usr/bin/env python3
"""PyTest tests for the select_positions.py module.
"""
import os
import sys
sys.path.append(os.path.join(os.path.dirname(sys.path[0]),'amoebaelib')) # Customize.

from select_positions import \
trim_one_column_from_alignment, \
check_whether_all_cols_unique_seqs, \
recursively_remove_positions, \
optimize_position_selection


def test_trim_one_column_from_alignment():  # ***Incomplete test
    """Test the trim_one_column_from_alignment function in the select_positions.py file.
    """
    ##########################
    # Arrange.
    alignment = "alignment"
    alignment2 = "alignment2"
    column_index = "column_index"

    ##########################
    # Act.
    #x = trim_one_column_from_alignment(alignment,
    #		alignment2,
    #		column_index)

    ##########################
    # Assert.
    assert True == True # ***Temporary.



def test_check_whether_all_cols_unique_seqs():  # ***Incomplete test
    """Test the check_whether_all_cols_unique_seqs function in the select_positions.py file.
    """
    ##########################
    # Arrange.
    alignment_path = "alignment_path"

    ##########################
    # Act.
    #x = check_whether_all_cols_unique_seqs(alignment_path)

    ##########################
    # Assert.
    assert True == True # ***Temporary.



def test_recursively_remove_positions():  # ***Incomplete test
    """Test the recursively_remove_positions function in the select_positions.py file.
    """
    ##########################
    # Arrange.
    recursion_num = "recursion_num"

    ##########################
    # Act.
    #x = recursively_remove_positions(recursion_num)

    ##########################
    # Assert.
    assert True == True # ***Temporary.



def test_optimize_position_selection():  # ***Incomplete test
    """Test the optimize_position_selection function in the select_positions.py file.
    """
    ##########################
    # Arrange.
    model_name = "model_name"
    outdirpath = "outdirpath"
    timestamp = "timestamp"

    ##########################
    # Act.
    #x = optimize_position_selection(model_name,
    #		outdirpath,
    #		timestamp)

    ##########################
    # Assert.
    assert True == True # ***Temporary.



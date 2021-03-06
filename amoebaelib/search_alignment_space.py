#!/usr/bin/env python3
# Copyright 2018 Lael D. Barlow
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#     http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# 

"""Contains functions for searching for alignments that support given tree
topologies (comparing alternative topologies).
"""
from datapaths import DataPaths
import sys
import os
import numpy as np
import collections
import argparse
import subprocess
import time
import datetime
import glob
import shutil
import re
import statistics
import pandas as pd
import random
import copy

from trim_nex import trim_nex
from paralogue_counter import get_seq_obj_from_srch_res_csv_info
import column_header_lists
from phylo_clas import ModelInfoFromCSV,\
get_clade_name_from_model, code_names_in_ali, quote_tree, code_tree,\
uncode_tree, uncode_tree_obj
from paralogue_counter import add_seq_to_alignment3
from select_seqs import get_ml_tree_branch_lengths
from amoebae_m import find_input_file_in_parent_directory

# If running on computecanada, set Qt to offscreen mode so that it works on clusters.
import platform
graham_node = re.compile(r"node='gra\d+")
if 'computecanada' in str(platform.uname()) or\
    graham_node.search(str(platform.uname())) is not None:
    os.environ['QT_QPA_PLATFORM']='offscreen'

#from select_seqs import get_clade_name_from_model2,\
#get_nodes_of_interest, get_list_of_leaf_names_for_node, TaxonomicInfo,\
#get_taxonomic_info, define_nodestyles_dict_for_colourcoding,\
#define_textface_for_labeling_stem, get_corresponding_node,\
#get_ml_tree_branch_lengths, get_branch_length_info, reduce_alignment


# Import functions for working with sequences, alignments, and trees.
from Bio import AlignIO
from Bio import SeqIO
from Bio.Alphabet import IUPAC, Gapped
from afa_to_nex import delete_extra_mesquite_lines, afa_to_nex, nex_to_afa, nex_to_phylip
from Bio.Align import MultipleSeqAlignment
from Bio.Seq import Seq
from Bio.SeqRecord import SeqRecord
from ete3 import Tree, faces, AttrFace, TreeStyle, NodeStyle, TextFace

# Define classes.

class TaxonomicInfo():
    """Class for storing taxonomic info.
    """
    def __init__(self, superbranch, supergroup, group, species):
        self.superbranch = superbranch
        self.supergroup = supergroup
        self.group= group
        self.species = species




# Define functions.


def trim_one_column_from_alignment(alignment, alignment2, column_index):
    """Take a nexus alignment file path and remove column at a given index
    (first column has index 0).
    """
    with open(alignment) as infh, open(alignment2, 'w') as o:
        # Parse input alignment file.
        alignment_obj = AlignIO.read(infh, 'nexus')
        # Record input alignment length.
        len1 = len(alignment_obj[0].seq)
        # Remove relevant column from alignment object.
        alignment_obj2 = alignment_obj[:, :column_index] + alignment_obj[:, column_index + 1:]
        # Check that the alignment length is shorter by one column.
        len2 = len(alignment_obj2[0].seq)
        assert len1 - len2 == 1
        # Write modified alignment object to output file path.
        AlignIO.write(alignment_obj2, o, 'nexus')


def get_taxa_represented_in_clade(clade, ml_tree_info_dict):
    """Make a list of taxonomic terms currently represented in the clade.
    """
    taxa_represented = []
    for seqname in\
    ml_tree_info_dict[clade]['seq names by descending length']:
        # Get species name from sequence name.
        #species_name = seqname.replace('__', ' ').replace('_', ' ').split(' ', 1)[1]
        species_name = get_species_name_from_seq_id(seqname)
        # Get taxonomic information for species name from info csv file.
        ti = get_taxonomic_info(species_name)
        # Add taxon names to taxa represented.
        taxa_represented = taxa_represented\
                + list(set([ti.superbranch, ti.supergroup, ti.group, ti.species]))
    return taxa_represented


def get_species_name_from_seq_id(seq_id):
    """Take a fasta sequence id/header/taxon name for one of the sequences in
    an alignment or FASTA file, and return the species name that it contains.
    """
    #species_name = seq_id.replace('__', ' ').replace('_', ' ').split(' ', 1)[1]
    #print('WARNING: Remember to update parsing of species names for new trees.')
    # For parsing new sequence ids:
    species_name = seq_id.split('__')[0].replace('_', ' ')
    assert len(species_name) > 0
    return species_name


def get_names_of_dispensable_seqs_in_clade(clade,
                                           ml_tree_info_dict,
                                           essential_taxa):
    """Take a clade name and a dictionary of info for the tree that it came
    from, and determine which ones are dispensable taxonomically.
    """
    # Make a list of taxonomic terms currently represented in the clade.
    taxa_represented = get_taxa_represented_in_clade(clade, ml_tree_info_dict)

    ## Print.
    #print('\n--------------------------------')
    #print('BEGIN get_names_of_dispensable_seqs_in_clade function call\n')

    #print('Essential taxa:')
    #for i in essential_taxa:
    #    print(i)

    #print('\nTaxa represented already:')
    #for i in list(set(taxa_represented)):
    #    print(i)

    #print('\nEssential taxa represented already, but only once:')
    #for i in list(set(taxa_represented)):
    #    if i in essential_taxa:
    #        if taxa_represented.count(i) == 1:
    #            print(i)

    #print('\nDecisions for each sequence:')

    # Initiate list of names for dispensable sequences.
    names_of_dispensable_seqs = []

    # Iterate over all the sequence names in the clade.
    for seqname in\
    ml_tree_info_dict[clade]['seq names by descending length']:

        # Get species name from sequence name.
        species_name = get_species_name_from_seq_id(seqname)

        # Get taxonomic information for species name from info csv file.
        ti = get_taxonomic_info(species_name)
        ti_list = [ti.superbranch, ti.supergroup, ti.group, ti.species]

        # Determine whether any of the taxonomy terms are in the essential
        # list.
        essential_terms = []
        for x in ti_list:
            if x in essential_taxa:
                essential_terms.append(x)

        # Check whether any of the terms appear in the taxa_represented list
        # only once (if so then the sequence is essential).
        seq_is_essential = False
        for term in essential_terms:
            if taxa_represented.count(term) == 1:
                seq_is_essential = True

        # Add to list if not essential.
        if not seq_is_essential:
            names_of_dispensable_seqs.append(seqname)

        #x = 'Essential'
        #if not seq_is_essential:
        #    x = 'Dispensable'
        #print(', '.join([seqname, species_name] + ti_list + [x]))
        #print(seqname)
        #print('\tessential terms: ' + ', '.join(essential_terms))
        #print('\t' + x)

    ## Print.
    #print('\nDispensable seqs:')
    #for i in names_of_dispensable_seqs:
    #    print(i)
    #print('\nEND get_names_of_dispensable_seqs_in_clade function call')
    #print('--------------------------------\n')

    # Return list of sequence names for dispensable sequences.
    return names_of_dispensable_seqs


def new_seq_in_clade_dispensable(essential_taxa,
                                 clade,
                                 additional_seq_id):
    """Take a list of essential taxonomic terms, a list of taxa represented in
    a clade with an added sequence (including from the added sequence), and the
    sequence ID of the sequence that was added. Return true if the additional
    sequences is taxonomically dispensable to the clade.
    """
    # Initiate variable for determining whether the added sequence is
    # dispensable.
    new_seq_dispensable = True

    # Iterate over all the sequence names in the clade.
    taxonomic_terms_in_clade = []
    for seqname in [x.name for x in clade.get_leaves()]:
        # Get species name from sequence name.
        species_name = get_species_name_from_seq_id(seqname)

        # Get taxonomic information for species name from info csv file.
        ti = get_taxonomic_info(species_name)
        ti_list = [ti.superbranch, ti.supergroup, ti.group, ti.species]

        # Add to list of taxa represented.
        taxonomic_terms_in_clade = taxonomic_terms_in_clade + ti_list

    # Get species name from sequence name.
    added_species_name = get_species_name_from_seq_id(additional_seq_id)

    # Get taxonomic information for species name from info csv file.
    added_species_ti = get_taxonomic_info(added_species_name)
    added_species_ti_list = [ti.superbranch, ti.supergroup, ti.group, ti.species]

    # Determine whether any of the taxonomy terms for the added species are
    # in the essential list.
    essential_terms = []
    for x in added_species_ti_list:
        if x in essential_taxa:
            essential_terms.append(x)
    # Check whether any of the terms appear in the taxa_represented list
    # only once (if so then the sequence is essential).
    for term in essential_terms:
        if taxonomic_terms_in_clade.count(term) == 1:
            new_seq_dispensable = True
            break

    # Return result.
    return new_seq_dispensable 


def get_new_type_seqs_dict(seqname, ml_tree_info_dict, type_seqs_dict):
    """Take a type sequence name dictionary and a sequence name, and return a
    new dictionary with the sequence replaced with another sequence if
    necessary.
    """
    # Copy the input dict.
    type_seqs_dict2 = type_seqs_dict.copy()

    # Determine whether the seqname is one of the type seqnames in the dict.
    is_type_seq = False
    for clade in type_seqs_dict2.keys():
        if seqname == type_seqs_dict2[clade]:
            is_type_seq = True
    
            # If it is a type seq, then replace it with another sequence name.
            # Identify an alternative type sequence for the same
            # (current) clade.
            for seqname2 in\
            reversed(ml_tree_info_dict[clade]\
            ['seq names by descending length'].copy()):
                if seqname2 != seqname:
                    # Change type seq for clade to a different sequence.
                    type_seqs_dict2[clade] = seqname2
    
    # Return the new dict.
    return type_seqs_dict2


def reduce_alignment(alignment_file, output_alignment_file, removal_name_list):
    """Take file path for an existing alignment and an output alignment, and
    a list of sequence names for removal. Write the reduced alignment to the
    output path in nexus format. Note: This function assumes that the names in
    the removal lit and the alignment are all either coded or uncoded.
    """
    # Check that at least one sequence name listed for removal.
    assert len(removal_name_list) > 0

    # Remove extra mesquite lines if present.
    delete_extra_mesquite_lines(alignment_file)

    # Get list of names of sequences in alignment.
    names_in_alignment = [x.id for x in AlignIO.read(alignment_file, 'nexus')]

    # Check number of sequences in input alignment.
    num_seqs1 = len(names_in_alignment)

    # Check that all the sequences listed for removal are actually in the input
    # alignment.
    #names_in_alignment = [x.replace('-', '_') for x in names_in_alignment]
    for name in removal_name_list:
        assert name in names_in_alignment, """Sequence %s cannot be identified
        in the alignment %s and therefore cannot be removed.""" % (name,
                os.path.basename(alignment_file))
        # If this happens, then maybe there are characters that are in the
        # alignment that were changed or removed when parsing the resulting
        # tree ('.' or '-' ?). This shouldn't be a problem with the new trees.
    #assert\
    #len(list(set(removal_name_list).intersection(set(names_in_alignment))))\
    #== len(removal_name_list)

    # Make a copy of the input alignment file with the listed sequences
    # removed.
    coded_seqs_to_not_remove_from_dataset = []
    with open(alignment_file) as infh, open(output_alignment_file, 'w') as o:
        alignment = AlignIO.read(infh, 'nexus')
        #print('number of seqs in original alignment')
        #print(len(alignment))
        alignment2 = MultipleSeqAlignment([])
        #print('number of seqs in alignment2:')
        #print(len(alignment2))
        #print('Removing sequences from alignment.')
        #ali_len = len(alignment)
        removed_a_seq = False
        inum = -1 
        for i in alignment:
            inum += 1
            if i.id not in removal_name_list:
                alignment2.append(alignment[inum])
            else:
                removed_a_seq = True
        assert removed_a_seq

        alignment3 =\
        MultipleSeqAlignment(alignment2[:,:])
        #print('number of seqs in alignment3:')
        #print(len(alignment3))

        # Get list of sequences in new alignment.
        ids_in_alignment3 = []
        for i in alignment3:
            ids_in_alignment3.append(i.id)

        # Write reduced alignment.
        #print('Writing modified alignment file:\n\t%s' % o.name)
        AlignIO.write(alignment3, o, 'nexus')

    # Check that number of sequences in new alignment is one less than in the
    # input alignment.
    num_seqs2 = len(AlignIO.read(output_alignment_file, 'nexus'))
    assert num_seqs2 + 1 == num_seqs1


def write_constraint_tree_without_extra_parentheses(ete3_tree_obj, tree_outpath):
    """Take an ETE3 TreeNode object and write to a file, but ensure that there
    are not double outer parentheses in the output newick tree.
    """
    # Write tree object to a newick file without any branch info.
    ete3_tree_obj.write(outfile=tree_outpath, format=9)

    # Check whether there are double outer parentheses.
    double_outer_parentheses = False
    with open(tree_outpath, 'r') as infh:
        newick_tree_string = infh.read().strip()
        if newick_tree_string.startswith('(('):
            last_parenthesis_position = len(newick_tree_string[2:-2])
            string_position_num = 0
            open_parenthesis_count = 1
            for i in newick_tree_string[2:-2]:
                string_position_num += 1
                if string_position_num == last_parenthesis_position:
                    double_outer_parentheses = True
                    break
                # This perhaps assumes that there are no parentheses in the
                # taxon names.
                if i == '(':
                    open_parenthesis_count += 1
                elif i == ')':
                    open_parenthesis_count += -1
                if open_parenthesis_count == 0:
                    break

    # If necessary, modify the newick tree string in the output file.
    if double_outer_parentheses:
        newick_tree_string = None
        with open(tree_outpath) as infh:
            newick_tree_string = infh.read().strip()
        with open(tree_outpath, 'w') as o:
            newick_tree_string_without_extra_parentheses =\
                    newick_tree_string[1:-2] + ';\n'
            o.write(newick_tree_string_without_extra_parentheses)


def get_seq_placement_in_tree(ml_placement_tree_path,
                              seq_to_add,
                              type_seqs_dict,
                              essential_taxa):
    """Parse a tree to find out where a sequence was placed.
    """
    # Parse tree using ete3.
    # Note: parentheses and commas get replaced with underscores.
    t1 = Tree(ml_placement_tree_path, quoted_node_names=True)

    ## Convert names in tree back to original names.
    #uncode_tree_obj(t1, outtablefp)

    ## Define name for tree without branch lengths.
    #simple_tree = tree_file_path.rsplit('_', 1)[0] + '_TEMP2' 

    ## Write simple tree to a new file 
    #t1.write(format=9, outfile=simple_tree)

    ## Parse simple tree.
    #t2 = Tree(simple_tree)

    # Print simple tree.
    #print('ML tree:')
    #print(t1)


    # Make a copy of the tree object.
    t2 = t1.copy()

    # Get list of "type" sequences from input.
    type_seq_list = type_seqs_dict.values()

    # For each "type" sequence, traverse all nodes and find the node with
    # the largest number of child nodes that are leaf (terminal) nodes,
    # containing the "type" sequence of interest, but not containing any of
    # the other "type" sequences.
    ts_num = 0
    first_type_seq_node_name = None
    ts_that_additional_seq_was_placed_in = None
    for ts in type_seq_list:
        ts_num += 1

        if ts_num == 1:
            first_type_seq_node_name = ts
            # Root on another "type" sequence for the first type sequence in
            # the list to get whole clade, then root the tree on the ancestor
            # node of that first clade.

            # Get a node name for a node corresponding to a different
            # "type" sequence.
            other_type_seq_node_name = None
            for i in type_seq_list:
                if i != ts:
                    other_type_seq_node_name = i
                    break

            # Get node corresponding to a different "type" sequence.
            other_type_seq_node = None
            for node in t2.traverse():
                if node.name == other_type_seq_node_name:
                    other_type_seq_node = node
                    break

            # Root on the other "type" sequence node.
            t2.set_outgroup(other_type_seq_node)

            #print('\n\n\nTree rooted on a type sequence other than the first type sequence.')
            #print(t2)

        elif ts_num == 2:
            # Root on the first "type" sequence node for all subsequent
            # clades.
            first_type_seq_node = None
            for node in t2.traverse():
                leaf_list = []
                for leaf in node.get_leaves():
                    if leaf.name == first_type_seq_node_name:
                        first_type_seq_node = node
                        break
            t2.set_outgroup(first_type_seq_node)
            #print('\n\n\nTree re-rooted on first type sequence:')
            #print(t2)


        # Make a copy of the tree topology to work with for each run
        # through this loop.
        t3 = t2.copy()

        # Make a list of nodes that contain type seq, but not any others. #
        # SEPARATE
        nodes_of_interest = []
        for node in t3.traverse():
            # Search in nodes that contain the type sequence.
            if node.search_nodes(name=ts):
                # Search in nodes that don't contain other type sequences.
                contains_other_type_seqs = False
                for ts2 in type_seq_list:
                    if not ts2 == ts:
                        if node.search_nodes(name=ts2):
                            contains_other_type_seqs = True
                if not contains_other_type_seqs:
                    # Add nodes of interest to list.
                    nodes_of_interest.append(node)

        # find the node with the most child leaf nodes.
        #node_num = 0
        #for node in nodes_of_interest:
        #    node_num += 1 
        #    print('Node ' + str(node_num) + ' Number of leaves:  ' + str(len(node.get_leaves())))
        #    print(node)
        node_w_most_leaves = sorted(nodes_of_interest, key=lambda x:\
                len(x.get_leaves()), reverse=True)[0]
        node_w_most_leaves.name = 'X'
        #print('\n\nClade defined by sequence ' + ts + ':')
        #print(node_w_most_leaves)

        #name_of_additional_seq = record.description
        name_of_additional_seq = seq_to_add.id #record.id # + ' ' + record.description

        #print('\n\n\n')
        #print(name_of_additional_seq)
        #print('\n\n\n')
        #for i in [x.name for x in node_w_most_leaves.get_leaves()]:
        #    print(i)
        #print('\n\n\n')

        if name_of_additional_seq.strip() in [x.name for x in node_w_most_leaves.get_leaves()]:
            ts_that_additional_seq_was_placed_in = ts
            #print('%s is in this clade.' % name_of_additional_seq)

            ## Make a list of taxonomic terms currently represented in the clade.
            #taxa_represented = get_taxa_represented_in_clade(node_w_most_leaves,
            #                                                 ml_tree_info_dict)

            ## Get clade name for type seq name from type seqs dict.
            #clade_name = None
            #for c in type_seqs_dict.keys():
            #    if type_seqs_dict[c] ==\
            #    ts_that_additional_seq_was_placed_in:
            #        clade_name = c
            #        break
            #assert clade_name is not None

            # Determine which seqs in the clade are dispensable, considering their
            # taxonomic placement.
            #names_of_dispensable_seqs_in_clade =\
            #get_names_of_dispensable_seqs_in_clade(clade_name,
            #                                       ml_tree_info_dict,
            #                                       essential_taxa,
            #                                       taxa_represented) 
            additional_seq_dispensable =\
            new_seq_in_clade_dispensable(essential_taxa,
                                         node_w_most_leaves,
                                         seq_to_add.id)

            # Determine whether the additional sequence is dispensable
            # or not in the new clade.
            if not additional_seq_dispensable:
                added_seq_adds_essential_taxon = True
                new_seq_essential = True
            
            # Break the loop, because no other clades need to be
            # considered after the relevant clade has been identified.
            break

    # Return the name of the type sequence of the clade that the sequence is
    # placed in.
    return ts_that_additional_seq_was_placed_in


def modify_alignment_in_x_way(previous_ali_tree_tuple, mod_type):
    """Modify an alignment (and associated tree) and return a tuple with all
    the same type of elements as the input tuple, except for the new
    alignment (and associated tree).
    """
    # Unpack objects from input tuple.
    iteration = previous_ali_tree_tuple[0]
    tree = previous_ali_tree_tuple[1]
    #print('tree:')
    #print(tree)
    alignment = previous_ali_tree_tuple[2]
    positions_attempted_to_remove = previous_ali_tree_tuple[3]
    subs_model = previous_ali_tree_tuple[4]
    type_seqs_dict = previous_ali_tree_tuple[5]
    ml_tree_info_dict = previous_ali_tree_tuple[6]
    seqs = previous_ali_tree_tuple[7]
    seqs_attempted_to_remove = previous_ali_tree_tuple[8]
    seqs_attempted_to_add = previous_ali_tree_tuple[9]
    essential_taxa = previous_ali_tree_tuple[10]
    stop = previous_ali_tree_tuple[11]
    new_seq_essential = previous_ali_tree_tuple[12]
    modified_clade_name = previous_ali_tree_tuple[13]

    # Check that the stop variable was not set to True in the last iteration.
    assert not stop

    # Define the current iteration number (for naming output files).
    iteration2 = iteration + 1

    # Define path to new alignment file.
    alignment2 = alignment.rsplit('_', 1)[0] + '_' + str(iteration2) + '.nex'

    # Determine number of sequences in input alignment.
    seqnames_in_alignment = [x.id for x in AlignIO.read(alignment, 'nexus')]
    num_seqs_in_alignment = len(seqnames_in_alignment)

    # Define path to new tree file.
    tree2 = os.path.join(alignment2.rsplit('.', 1)[0] + '_newick.tre')

    # Determine number of sequences represented in the input tree.
    seqnames_in_tree = [x.name for x in Tree(tree).get_leaves()]
    num_seqs_in_tree = len(seqnames_in_tree)

    # Check that number of sequences in alignment and tree are the same.
    assert num_seqs_in_alignment == num_seqs_in_tree

    ## Check that the sequence names in the alignment and the tree are the same.
    #print('Name in alignment\tName in tree')
    #for i, j in zip(sorted(seqnames_in_alignment), sorted(seqnames_in_tree)):
    #    print(i + '\t' + j)
    #    assert i == j, """These sequence names should be the same."""

    # Define output path for annotated tree image file.
    annotated_tree_outpath2 =\
    os.path.join(alignment2.rsplit('.', 1)[0] + '_annotated_result.png')

    # Define output directory path.
    outputdir = os.path.dirname(alignment2)

    # Initiate variable for new type sequence dictionary.
    type_seqs_dict2 = None

    # Initiate variable to store name of the clade that is modified here.
    modified_clade_name2 = None

    #############################################
    #############################################
    # This portion of the code is different depending on what type of
    # modification is needed:

    if mod_type == 'remove_seqs':
        # Check that essential taxa were specified.
        assert len(essential_taxa) > 0, """No essential taxa are specified."""

        # Determine what sequence to remove.

        # Set variables that won't be modified.
        subs_model2 = subs_model
        positions_attempted_to_remove2 = positions_attempted_to_remove
        seqs_attempted_to_add2 = seqs_attempted_to_add

        # Initiate variables that will be modified later.
        seqs_attempted_to_remove2 = seqs_attempted_to_remove

        # Determine the clade with the worst support.
        #clades_by_ascending_ratio = sorted(branch_length_info_dict.keys(),\
        #        key=lambda x: branch_length_info_dict[x]['stem/branch ratio'])
        clade_list = list(ml_tree_info_dict.keys())
        clade_list.remove('internal branches info list')
        #clades_by_ascending_support_measure =\
        #sorted(clade_list, key=lambda x: ml_tree_info_dict[x]['alrt support'])
        clades_by_ascending_support_measure =\
        sorted(clade_list,\
                key=lambda x: ml_tree_info_dict[x]['stem/branch ratio'])

        removed_a_sequence = False

        for clade in clades_by_ascending_support_measure:
            # Determine which seqs in the clade are dispensable, considering their
            # taxonomic placement.
            names_of_dispensable_seqs_in_clade =\
            get_names_of_dispensable_seqs_in_clade(clade,
                                                   ml_tree_info_dict,
                                                   essential_taxa,
                                                   ) 
            ## Get list of sequence names in clade by descending order of branch
            ## length (from the root of the clade).
            #seqnames = ml_tree_info_dict[clade]['seq names by descending length']

            # Remove sequence names from the list that have already been removed
            # (and did not improve the tree).
            for seqname in seqs_attempted_to_remove:
                if seqname in names_of_dispensable_seqs_in_clade:
                    names_of_dispensable_seqs_in_clade.remove(seqname)

            # Iterate over sequence names in descending order of branch length.
            for seqname in names_of_dispensable_seqs_in_clade:
                # Try removing the corresponding sequence from the
                # tree, and see whether it improves the branch length
                # ratios.
                print('\t\tremoving sequence %s' % seqname)

                # If the sequence is a type sequence, then you have to
                # choose another sequence in the clade as a replacement
                # type sequence.
                type_seqs_dict2 = get_new_type_seqs_dict(seqname,
                                                         ml_tree_info_dict,
                                                         type_seqs_dict)

                # Remove seq from alignment.
                print('\t\t\tWriting reduced alignment to ' +\
                        os.path.basename(alignment2))
                reduce_alignment(alignment, alignment2, [seqname])


                # Code alignment (get table file).???

                # Remove seq from parsed tree object, and
                # use that as a constraint tree.
                # Copy tree.
                #t2 = t1.copy()
                #t2 = Tree(tree, quoted_node_names=False)
                t2 = Tree(tree, quoted_node_names=True) # Whether quoted_node_names is true or false may be different for older trees.

                # Get a list of all node objects with the same name as the
                # sequence of interest.
                seq_nodes = t2.search_nodes(name=seqname)

                # Check that one and only one such node was found.
                assert len(seq_nodes) == 1, """Sequence names in tree may not
                be formatted as expected."""

                # Remove the node from the new tree object.
                node_to_remove = seq_nodes[0]
                t2_len_before = len(t2.get_leaves())
                node_to_remove.delete()

                # Check that a node was actually removed.
                t2_len_after = len(t2.get_leaves())
                assert t2_len_before == t2_len_after + 1

                # Write modified tree to a file.
                print('\t\t\tWriting annotated tree to ' +\
                        os.path.basename(tree2))
                #t2.write(outfile=tree2, format=9)
                write_constraint_tree_without_extra_parentheses(t2, tree2)

                # Add sequence name to list of sequences that have been removed. 
                seqs_attempted_to_remove2.append(seqname)

                # Record name of clade that was modified.
                modified_clade_name2 = clade

                # Break the loop so that only one sequence gets removed per
                # iteration.
                removed_a_sequence = True
                break

            # Break this loop too, if a sequence was removed.
            if removed_a_sequence:
                break

        # Check that a sequence was removed, if not then stop iterating.
        if removed_a_sequence:
            # Check that the output alignment has one less sequence than the
            # input alignment.
            num_seqs_in_new_alignment = len(AlignIO.read(alignment2, 'nexus'))
            assert num_seqs_in_new_alignment + 1 == num_seqs_in_alignment
            # Check that the output tree has one less sequence than the input
            # tree.
            num_seqs_in_new_tree = len(list(Tree(tree2).get_leaves()))
            assert num_seqs_in_new_tree + 1 == num_seqs_in_tree
        else:
            print('Could not find a sequence to remove.')
            # Stop iterative calling of modify_seq_in_x_way function (at least
            # with the current modification type).
            stop = True


    elif mod_type == 'add_seqs':
        # Check that a file with sequences to try adding was specified.
        assert len(seqs) > 0, """No sequences provided as input."""

        # Determine what sequence to add.

        # Set variables that won't be modified.
        subs_model2 = subs_model
        positions_attempted_to_remove2 = positions_attempted_to_remove
        seqs_attempted_to_remove2 = seqs_attempted_to_remove
        type_seqs_dict2 = type_seqs_dict

        # Initiate variables that will be modified later.
        seqs_attempted_to_add2 = seqs_attempted_to_add

        # Initiate variable to indicate whether a sequence was found to add or
        # not.
        added_a_sequence = False

        # Initiate variables to indicate whether the new tree and alignment are
        # usable (if the added sequence was placed into a clade of interest or
        # not).
        ali_and_tree_usable = False
        any_ali_and_tree_usable = False

        # Initiate a variable to indicate whether the added sequence adds an
        # essential taxon that was missing in the clade before (if it does,
        # then even if the resulting tree yields lower support then it still
        # might be considered better).
        added_seq_adds_essential_taxon = False

        # Determine which sequences, if any, could be added to the tree.
        seqnames_in_tree = [x.name.strip('\"') for x in Tree(tree).get_leaves()]
        all_seqnames = [x.id for x in seqs] 
        seqnames_to_be_added = []
        for seqname in all_seqnames:
            if seqname not in seqs_attempted_to_add2 + seqnames_in_tree:
                # Add sequence name to list.
                seqnames_to_be_added.append(seqname)

        # Make a list of taxonomic terms currently represented in the clade.
        #taxa_represented = get_taxa_represented_in_clade(clade, ml_tree_info_dict)
        # *** ToDo: Add functionality to add sequences with taxonomic terms in
        # the essential taxa list that are missing in the taxa_represented
        # list.
        if len(seqnames_to_be_added) == 0:
            print('Could not find a sequence to add.')
            # Stop iterative calling of modify_seq_in_x_way function (at least
            # with the current modification type).
            stop = True
        else:
            # Shuffle the sequences if it's the first iteration.
            if iteration == 0:
                # Define a seed for the random shuffle of sequences so that it
                # can be reproduced.
                seed = 12345
                # Shuffle the list of sequences deterministically
                # (reproducibly).
                random.Random(seed).shuffle(seqs)
            
            # Loop over candidate sequences and try adding them to the tree.
            seq_to_add = None
            for seq in seqs:
                if seq.id in seqnames_to_be_added:
                    seq_to_add = seq
                else:
                    # Try another sequence in the list.
                    continue

                assert seq_to_add is not None
                print('\t\tAdding sequence ' + seq_to_add.id)

                # Add to list of sequences added to to the tree.
                seqs_attempted_to_add2.append(seq_to_add.description)

                # Add sequence to alignment.
                add_seq_to_alignment3(seq_to_add, alignment, alignment2)

                # Check that the added sequence is not identical (after trimming)
                # to a sequence already present in the trimmed alignment. 
                ali_with_new_seq = AlignIO.read(alignment2, 'nexus')
                last_seq = ali_with_new_seq[-1]
                identical_to_existing_seq = False
                for xseq in ali_with_new_seq[:-1]:
                    #print(str(xseq.seq))
                    #print(str(last_seq.seq))
                    if str(xseq.seq) == str(last_seq.seq):
                        identical_to_existing_seq = True
                        print('\t\t\tThe sequence is identical to a previous one')
                        break

                # Only run a tree if the added sequence is not identical to any
                # existing sequences.
                ts_that_additional_seq_was_placed_in = None
                if not identical_to_existing_seq: 
                    # Use the previous constraint tree as a constraint tree.
                    constraint_tree_fp = get_constraint_tree_fp(alignment)
                    #constraint_tree_fp = tree
                    # Unless the path to such a file doesn't exist, then just use
                    # whatever tree was input.
                    if not os.path.isfile(constraint_tree_fp):
                        print('\n\n\nConstraint tree doesnt exist:')
                        print(constraint_tree_fp)
                        print('\n\n\n')
                        assert 2!=2
                        constraint_tree_fp = tree

                    # Call function to run IQtree (specifying option to input a
                    # constraint tree and run ML search with the -g option instead of
                    # using the -te, --alrt, and --abayes options.
                    place_seq = True
                    ml_placement_tree_path =\
                    run_tree_for_branch_lengths_and_supports_for_topology(
                                                                  constraint_tree_fp,
                                                                  alignment2,
                                                                  subs_model,
                                                                  outputdir,
                                                                  place_seq)

                    # Indicate that a new tree was produced.
                    added_a_sequence = True

                    # Confirm that the sequence went into one of the clades of
                    # interest, and which clade it was placed in.
                    #first_type_seq_node_name = None
                    ts_that_additional_seq_was_placed_in =\
                    get_seq_placement_in_tree(ml_placement_tree_path,
                                              seq_to_add,
                                              type_seqs_dict,
                                              essential_taxa)

                    # If the sequence could not be placed in any of the clades of interest,
                    # then set the name of the type sequence to a string 'None'.
                    if ts_that_additional_seq_was_placed_in is None:
                        ts_that_additional_seq_was_placed_in = 'None'

                    # If the sequence was placed in a clade of interest, then the tree
                    # is usable.
                    if ts_that_additional_seq_was_placed_in is not None\
                    and ts_that_additional_seq_was_placed_in != 'None':
                        # Change variable to indicate that the alignment and
                        # tree are usable.
                        ali_and_tree_usable = True 

                        # Get name of clade that the type sequence is in.
                        clade_name =\
                        get_clade_name_from_model2(ts_that_additional_seq_was_placed_in,
                                                   type_seqs_dict2)

                        # Record name of clade that was modified.
                        modified_clade_name2 = clade_name

                    else:
                        print('\t\t\tThe sequence was not placed in any of the clades of interest')

                    ## Temp:
                    ## Check that the clade that the additional sequence was placed in was
                    ## identified.
                    #assert ts_that_additional_seq_was_placed_in is not None, """Sequence was
                    #not placed in any of the clades of interest: %s""" % record.description

                    # Parse tree using ete3.
                    # Note: parentheses and commas get replaced with underscores.
                    t1 = Tree(ml_placement_tree_path, quoted_node_names=True)

                    # Write modified tree to a file.
                    print('\t\t\tWriting annotated tree to ' +\
                            os.path.basename(tree2))
                    #t1.write(outfile=tree2, format=9)
                    write_constraint_tree_without_extra_parentheses(t1, tree2)




                # *** This check may be redundant.
                # Check that a sequence was added, if not then stop iterating.
                if added_a_sequence and ali_and_tree_usable and not identical_to_existing_seq:
                    # Check that the output alignment has one more sequence than the
                    # input alignment.
                    num_seqs_in_new_alignment = len(AlignIO.read(alignment2, 'nexus'))
                    assert num_seqs_in_new_alignment == num_seqs_in_alignment + 1
                    # Check that the output tree has one less sequence than the input
                    # tree.
                    num_seqs_in_new_tree = len(list(Tree(tree2).get_leaves()))
                    assert num_seqs_in_new_tree == num_seqs_in_tree + 1

                    # Change variable value to indicate that a usable sequence
                    # was found.
                    any_ali_and_tree_usable = True
                    
                    # Break the loop over the sequences to add.
                    break

                else:
                    # Do not use the alignment and tree if the above conditions are not
                    # met (try another sequence).
                    pass

        # Stop this type of modification if no sequences could be found that
        # actually work.
        if not any_ali_and_tree_usable:
            stop = True


    elif mod_type == 'remove_columns':
        # Set variables that won't be modified.
        subs_model2 = subs_model
        seqs_attempted_to_remove2 = seqs_attempted_to_remove
        type_seqs_dict2 = type_seqs_dict
        seqs_attempted_to_add2 = seqs_attempted_to_add

        # Initiate variables that will be modified later.
        positions_attempted_to_remove2 = positions_attempted_to_remove
        
        # The tree topology will be the same, so just copy the tree topology
        # file to the new path.
        # Read input tree and write to a new file.
        t2 = Tree(tree, quoted_node_names=True) # Whether quoted_node_names is true or false may be different for older trees.
        t2.write(outfile=tree2, format=9)

        #shutil.copyfile(tree, tree2)

        # Define variable for storing True if a column was removed.
        removed_a_column = False

        # Parse input alignment, and find a column to try to remove.
        with open(alignment) as infh:
            alignment_obj = AlignIO.read(infh, 'nexus')

            # Get length of sequences in alignment.
            seq_len = alignment_obj.get_alignment_length()

            # get a list of columns as strings in the original alignment.
            columns = [alignment_obj[:, col] for col in range(seq_len)] 

            # Iterate over column sequences and remove a column that has
            # not been removed before.
            column_index = -1
            for column in columns:
                column_index += 1
                # Determine whether the column has been removed before.
                if not column in positions_attempted_to_remove:
                    # Remove column from alignment.
                    trim_one_column_from_alignment(alignment, alignment2,
                            column_index)
                    # Define path to new modified alignment file.
                    new_alignment = alignment2

                    print('\t\t\tRemoved column from alignment')

                    # Set variable to indicate that a column was successfully
                    # removed.
                    removed_a_column = True

                    # Add column to list of columns that have been removed.
                    positions_attempted_to_remove2.append(column)

                    # Break this loop if a column was removed.
                    if removed_a_column:
                        break

        # Check that a sequence was removed, if not then stop iterating.
        if removed_a_column:
            # Check that the output alignment has one less column than the
            # input alignment.
            # ... redundant with another check?
            pass

        else:
            print('Could not find a column to remove.')
            # Stop iterative calling of modify_seq_in_x_way function (at least
            # with the current modification type).
            stop = True

    # Write code for the following options... 

    # elif mod_type == 'refine_alignment':
    #     ...Use the muscle -refine option...

    # elif mod_type == 'update_subs_model':
    #     ...use iqtree ModelFinder to find the best fit model for the modified
    #     alignment...

    # elif mod_type == 'reduce_tree':
    #    ...remove taxonomically redundant and long-branching sequences.


    else:
        assert 2 != 2, """mod_type variable not set properly."""

    #############################################
    #############################################

    # Only run a tree if a new alignment and topology were produced.
    ml_tree_path2 = None
    ml_tree_info_dict2 = None
    if not stop:
        # Run IQ-tree to get ML tree with branch supports for new alignment and/or
        # tree topology.
        #print('tree2:')
        #print(tree2)
        ml_tree_path2 =\
        run_tree_for_branch_lengths_and_supports_for_topology(tree2,
                                                              alignment2,
                                                              subs_model2,
                                                              outputdir)


        # Extract relevant information from ML tree.
        ml_tree_info_dict2 = get_ml_tree_info_dict(ml_tree_path2,
                                                  type_seqs_dict2,
                                                  annotated_tree_outpath2)

        # Write a type_seqs file.
        type_seqs_filepath = alignment2.rsplit('.', 1)[0] + '.type_seqs'
        assert not os.path.isfile(type_seqs_filepath)
        with open(type_seqs_filepath, 'w') as o:
            o.write('\n'.join([type_seqs_dict2[key].strip() + ', ' +\
                key.strip() for key in type_seqs_dict2.keys()]))

    # Construct a tuple with new info for new alignment and tree.
    new_ali_tree_tuple = (iteration2,
                          tree2,
                          alignment2,
                          positions_attempted_to_remove2,
                          subs_model2,
                          type_seqs_dict2,
                          ml_tree_info_dict2,
                          seqs,
                          seqs_attempted_to_remove2,
                          seqs_attempted_to_add2,
                          essential_taxa,
                          stop,
                          new_seq_essential,
                          modified_clade_name2)

    # Return the new tuple.
    return new_ali_tree_tuple


def get_taxonomic_info(species_name):
    """Given a species name that appears in the genome info csv file in the
    genomes folder, return taxonomic information from that csv file.
    """
    # Define path to info file.
    info_csv = DataPaths(main_data_dir).db_info_csv

    # Parse info file with pandas.
    df = pd.read_csv(info_csv, encoding='utf-8')

    # Iterate through rows until one is found with the same species name.
    taxonomic_info_obj = None
    found_row = False
    species = None
    for index, row in df.iterrows():
        species = row['Species (if applicable)']
        for x in range(0, 5):
            parsed_species_name = species_name.strip().split(' ', x)[-1]
            if species.strip().strip('.') == parsed_species_name:
                found_row = True
                superbranch = row['Superbranch']
                supergroup = row['Supergroup']
                group = row['Group']
                taxonomic_info_obj = TaxonomicInfo(superbranch, supergroup, group, species)
            if found_row:
                break
        if found_row:
            break


    assert taxonomic_info_obj is not None, """Could not identify taxonomic
    information for species %s""" % species_name

    return taxonomic_info_obj


def define_textface_for_labeling_stem(clade_name):
    """Define ete3 textface styles for different nodes of interest that need to be
    labeled.
    """
    # Define TextFace objects for clade stem nodes/branches.
    stem_clade = TextFace(clade_name)

    # Set some attributes
    #stem_clade.margin_top = 10
    #stem_clade.margin_right = 10
    #stem_clade.margin_left = 10
    #stem_clade.margin_bottom = 10
    #stem_clade.opacity = 0.5 # from 0 to 1
    #stem_clade.inner_border.width = 1 # 1 pixel border
    #stem_clade.inner_border.type = 1  # dashed line
    #stem_clade.border.width = 1
    #stem_clade.background.color = "LightGreen"

    # Return dictionary.
    return stem_clade


def get_corresponding_node(node, tree):
    """Return the ete3 TreeNode object in a tree that corresponds to
    a given node.
    """
    # Search for a node with child leaf nodes that have the same set of names.
    corresponding_node = None
    node_leaves = [x.name for x in node.get_leaves()]
    for n in tree.traverse():
        if set([y.name for y in n.get_leaves()]) == set(node_leaves):
            corresponding_node = n
            break
    # If necessary, re-root input tree on midpoint for parsing.
    if corresponding_node is None:
        # Re-root on midpoint.
        tree.set_outgroup(tree.get_midpoint_outgroup())
        # Search for node of interest again.
        for n in tree.traverse():
            if set([y.name for y in n.get_leaves()]) == set(node_leaves):
                corresponding_node = n
                break

    # Try rooting on random leaf nodes until the corresponding node can be
    # found.
    if corresponding_node is None:
        # Loop through random leaf nodes in tree, rooting on them, and then
        # searching for the corresponding node.
        for l in tree.iter_leaves():
            tree.set_outgroup(l)
            # Search for node of interest again.
            found = False
            for n in tree.traverse():
                if set([y.name for y in n.get_leaves()]) == set(node_leaves):
                    corresponding_node = n
                    found = True
                    break
            if found:
                break

    # Check that a corresponding node was identified.
    assert corresponding_node is not None, """Could not find corresponding
    node."""

    # Return corresponding node.
    return corresponding_node


def get_list_of_leaf_names_for_node(node):
    """Given an ete3 TreeNode object, return a list of terminal/leaf node
    names.
    """
    leaf_names = []
    for n in node.traverse():
        if n.is_leaf():
            leaf_names.append(n.name)
    return leaf_names


def get_clade_name_from_model2(type_seq_name, type_seqs_dict):
    """Return clade name for given type sequence name and type seqs info file
    (from models directory).
    """
    # Get clade name.
    clade_name = '?'
    for clade in type_seqs_dict.keys():
        if type_seq_name == type_seqs_dict[clade]:
                clade_name = clade
                break
        elif type_seq_name == type_seqs_dict[clade].replace(' ', '_'):
            clade_name = clade
            break
    assert clade_name != '?', """Could not identify clade name for type
    sequence name %s.""" % type_seq_name

    return clade_name


def get_nodes_from_actual_tree_obj(t3, nodes_of_interest):
    """Get nodes in the given tree object that correspond to the nodes in a
    given list of nodes from another tree object, and return as a list.
    """
    ## Temp.
    #print('\n\nget_nodes_from_actual_tree_obj function call...')
    #print('Input tree:')
    #print(t3)

    # Get original root node for tree object.
    original_outgroup = list(t3.traverse())[1]
    # Compile a list of corresponding nodes.
    new_node_list = []
    for i in nodes_of_interest:
        ## Temp.
        #print('Node of interest')
        #print(i)

        i_leaf_names = set([x.name for x in i.get_leaves()])
        corresponding_node = None
        # Traverse the tree to find node.
        for node in t3.traverse():
            node_leaf_names = [x.name for x in node.get_leaves()]
            # If the node has the same set of leaf names, then it is the
            # corresponding node.
            if node_leaf_names == i_leaf_names:
                corresponding_node = node
                break
        if corresponding_node is None:
            # Generate a list of three different rootings for the tree, at
            # least one of which should allow identification of the clade of
            # interest.
            roots = []
            roots.append(t3.get_midpoint_outgroup())
            t3.set_outgroup(t3.get_midpoint_outgroup())
            #print('Rerooted tree on midpoint:')
            #print(t3)
            side1 = list(t3.traverse())[1]
            side2 = list(t3.traverse())[2]
            for side in [side1, side2]:
                side_longest_length = 0
                side_longest_leaf = None
                # Apparently need to account for the strange case that one
                # sequence constitutes one side of the tree rooted on the
                # midpoint.
                if side.is_leaf():
                    length = t3.get_distance(side)
                    if length > side_longest_length:
                        side_longest_length = length
                        side_longest_leaf = side
                # In most cases there will be multiple leaves on both sides of
                # the midpoint root.
                else:
                    for leaf in side.get_leaves():
                        length = side.get_distance(leaf)
                        if length > side_longest_length:
                            side_longest_length = length
                            side_longest_leaf = leaf
                # Check that a leaf was identified.
                assert side_longest_leaf is not None
                # Add the longest leaf on this side of the midpoint to the list
                # of nodes on which to try rooting the tree.
                roots.append(side_longest_leaf)

            # Try finding the corresponding node again.
            for root_node in roots:
                t3.set_outgroup(root_node)
                #print('Rerooted tree:')
                #print(t3)
                for node in t3.traverse():
                    node_leaf_names = set([x.name for x in node.get_leaves()])
                    # If the node has the same set of leaf names, then it is the
                    # corresponding node.
                    if node_leaf_names == i_leaf_names:
                        corresponding_node = node
                        break
                # Break loop so that tree does not get re-rooted unnecessarily.
                if corresponding_node is not None:
                    break

            # Try finding the corresponding node again by rooting on every
            # single leaf until the node of interest is found.
            if corresponding_node is None:
                for leaf in t3.get_leaves():
                    t3.set_outgroup(leaf)
                    #print('Rerooted tree:')
                    #print(t3)
                    for node in t3.traverse():
                        node_leaf_names = set([x.name for x in node.get_leaves()])
                        # If the node has the same set of leaf names, then it is the
                        # corresponding node.
                        if node_leaf_names == i_leaf_names:
                            corresponding_node = node
                            break
                    # Break loop so that tree does not get re-rooted unnecessarily.
                    if corresponding_node is not None:
                        break

            # Check that the corresponding node was found.
            assert corresponding_node is not None

            # Root on the corresponding node identified. This is important,
            # because if the tree is not rooted on such a node, then the set of
            # leaves may be different for the node when it is identified again.
            t3.set_outgroup(corresponding_node)

        # Check that the corresponding node was found.
        assert corresponding_node is not None


        # Temp.
        if len(i.get_leaves()) != len(corresponding_node.get_leaves()):
            print('Query node:')
            print(i)
            print('Corresponding node:')
            print(corresponding_node)

        # Check that the corresponding node has the same number of leaves.
        assert len(i.get_leaves()) ==\
        len(corresponding_node.get_leaves()), """Identified node has a different
        number of leaves than expected."""

        # Append the corresponding node to the list.
        new_node_list.append(corresponding_node)

    # Don't do this, because the leaves for the clades of interest may not be
    # properly identified after re-rooting.
    ## Re-root the tree object on the original root node.
    #t3.set_outgroup(original_outgroup)

    # Return the list of corresponding nodes.
    return new_node_list


def get_nodes_of_interest(tree, type_seq_list):
    """Take an ete3 tree (TreeNode object), a list of type sequence names, and
    return a list of nodes of interest defined by clades (as ete3 TreeNode
    objects).
    """
    # Initiate list of orthogroup nodes of interest.
    orthogroup_nodes = []

    # Make a copy of the input tree.
    t2 = tree.copy()

    # For each "type" sequence, traverse all nodes and find the node with
    # the largest number of child nodes that are leaf (terminal) nodes,
    # containing the "type" sequence of interest, but not containing any of
    # the other "type" sequences.
    ts_num = 0
    first_type_seq_node_name = None
    for ts in type_seq_list:
        ts_num += 1

        # Check that the sequence is in the tree.
        assert ts in [n.name for n in t2.get_leaves()], """There are no taxa in
        the tree with the name %s""" % ts

        if ts_num == 1:
            first_type_seq_node_name = ts
            # Root on another "type" sequence for the first type sequence in
            # the list to get whole clade, then root the tree on the ancestor
            # node of that first clade.

            # Get a node name for a node corresponding to a different
            # "type" sequence.
            other_type_seq_node_name = None
            for i in type_seq_list:
                if i != ts:
                    other_type_seq_node_name = i
                    break
            assert other_type_seq_node_name is not None

            # Get node corresponding to a different "type" sequence.
            other_type_seq_node = None
            for node in t2.traverse():
                if node.name == other_type_seq_node_name:
                    other_type_seq_node = node
                    break
            assert other_type_seq_node is not None, """Could not identify
            a type seq node with name: %s""" % other_type_seq_node_name

            # Root on the other "type" sequence node.
            t2.set_outgroup(other_type_seq_node)

            #print('\n\n\nTree rooted on a type sequence other than the first type sequence.')
            #print(t2)

        elif ts_num == 2:
            # Root on the first "type" sequence node for all subsequent
            # clades.
            first_type_seq_node = None
            for node in t2.traverse():
                leaf_list = []
                for leaf in node.get_leaves():
                    if leaf.name == first_type_seq_node_name:
                        first_type_seq_node = node
                        break
            t2.set_outgroup(first_type_seq_node)
            #print('\n\n\nTree re-rooted on first type sequence:')
            #print(t2)


        # Make a copy of the tree topology to work with for each run
        # through this loop.
        t3 = t2.copy()

        # Make a list of nodes that contain type seq, but not any others. #
        # SEPARATE
        nodes_of_interest = []
        for node in t3.traverse():
            # Search in nodes that contain the type sequence.
            if node.search_nodes(name=ts):
                # Search in nodes that don't contain other type sequences.
                contains_other_type_seqs = False
                for ts2 in type_seq_list:
                    if not ts2 == ts:
                        if node.search_nodes(name=ts2):
                            contains_other_type_seqs = True
                if not contains_other_type_seqs:
                    # Add nodes of interest to list.
                    nodes_of_interest.append(node)

        # Check that a node of interest was found.
        # This assumes that there is more than one sequence in the clade, which
        # is true if the clades were constrained, but not necessarily
        # otherwise.
        #assert len(nodes_of_interest) >= 2 
        assert len(nodes_of_interest) >= 1 

        # find the node with the most child leaf nodes.
        node_w_most_leaves = sorted(nodes_of_interest, key=lambda x:\
                len(x.get_leaves()), reverse=True)[0]
        #node_w_most_leaves.name = 'X'

        # Add node to list of nodes of interest.
        orthogroup_nodes.append([ts, node_w_most_leaves])

    # Return list of lists containing defining sequence name and node object.
    return orthogroup_nodes


def define_nodestyles_dict_for_colourcoding():
    """Define node styles for different nodes of interest that need to be
    colour-coded.
    """
    # Initiate dict.
    nodestyle_dict = {}

    # General default style for tree (apply using the node.set_style(style)
    # function).
    style = NodeStyle()
    style["fgcolor"] = "#0f0f0f"
    style["size"] = 0
    style["vt_line_color"] = "#ff0000"
    style["hz_line_color"] = "#ff0000"
    style["vt_line_width"] = 8
    style["hz_line_width"] = 8
    style["vt_line_type"] = 0 # 0 solid, 1 dashed, 2 dotted
    style["hz_line_type"] = 0

    # dashed blue lines
    style1 = NodeStyle()
    style1["fgcolor"] = "#000000"
    style1["shape"] = "circle"
    style1["vt_line_color"] = "#0000aa"
    style1["hz_line_color"] = "#0000aa"
    style1["vt_line_width"] = 2
    style1["hz_line_width"] = 2
    style1["vt_line_type"] = 1 # 0 solid, 1 dashed, 2 dotted
    style1["hz_line_type"] = 1

    # stem_node
    stem_node = NodeStyle()
    stem_node["hz_line_width"] = 5

    # bold lines
    style2 = NodeStyle()
    #style2["vt_line_width"] = 8
    style2["hz_line_width"] = 5

    # bold dashed lines
    style3 = NodeStyle()
    style3["hz_line_width"] = 5
    style3["hz_line_type"] = 1


    # Set dashed blue lines in all leaves
    #style3 = NodeStyle()
    #style3["fgcolor"] = "#000000"
    #style3["shape"] = "circle"
    #style3["vt_line_color"] = "#0000aa"
    #style3["hz_line_color"] = "#0000aa"
    #style3["vt_line_width"] = 2
    #style3["hz_line_width"] = 2
    #style3["vt_line_type"] = 1 # 0 solid, 1 dashed, 2 dotted
    #style3["hz_line_type"] = 1


    # Add styles to dictionary.
    nodestyle_dict['default'] = style1
    nodestyle_dict['stem_node'] = stem_node
    nodestyle_dict['shortest branch'] = style2 # bold.
    nodestyle_dict['longest branch'] = style3 # dashed.
    nodestyle_dict['default'] = style1

    # Return dict.
    return nodestyle_dict

def get_abayes_support_for_node_from_another_tree(node,
                                                  t_with_abayes):
    """Take a node from one ete3 TreeNode object and find the corresponding
    node in another ete3 TreeNode object and return the support value for the
    node in the second tree (the abayes support value).
    """
    # Get corresponding node.
    corresponding_node = get_corresponding_node(node, t_with_abayes)

    # Return support value.
    return corresponding_node.support


def get_ml_tree_info_dict(ml_tree_path,
                          type_seqs_dict,
                          annotated_tree_outpath):
    """Take a path to an ML tree and return a dict with information about
    lengths and supports of relevant branches.
    
    Return a dictionary with keys as type sequence names and values lists with branch
    length ratios and branch support values for the respective clades in the input tree.
    """
    # Initiate output dictionary.
    branch_length_info_dict = {}

    # Parse tree file.
    t1 = Tree(ml_tree_path, format=1, quoted_node_names=True)

    # Define a dictionary of ete3 NodeStyle objects for different branch types
    # in the tree to be visualized.
    style_dict = define_nodestyles_dict_for_colourcoding() # Temporarily commented out.

    # Get a list of nodes of interest (ancestral nodes for clades of interest).
    orthogroup_nodes = []

    # Get list of "type" sequences from input.
    #type_seq_list = []
    #for i in open(type_seqs):
    #    type_seq_list.append(i.strip().split(',')[0])
    type_seq_list = type_seqs_dict.values()

    # Copy tree for colour-coding etc.
    t2 = t1.copy()

    # Translate node names (support values) to branch supports so that when the
    # tree is re-rooted, the supports won't be mixed up.
    for node in t2.traverse():
        if not node.is_leaf():
            if node.name != '':
                # Assign support attribute value to node.
                alrt = float(float(node.name.split('/')[0]) /100)
                abayes = float(node.name.split('/')[1])
                node.support = alrt # Get abayes later.
                ## Round up the node support value to 2 significant digits.
                #node.support = float(format(node.support * 0.01, '3.2f'))
                # Delete existing node name attribute for node.
                node.name = ''
    # Make a tree object with abayes supports instead of alrt.
    t_with_abayes = t1.copy() # Use this tree later to retrieve abayes values for nodes.
    for node in t_with_abayes.traverse():
        if not node.is_leaf():
            if node.name != '':
                # Assign support attribute value to node.
                alrt = float(float(node.name.split('/')[0]) /100)
                abayes = float(node.name.split('/')[1])
                node.support = abayes
                ## Round up the node support value to 2 significant digits.
                #node.support = float(format(node.support * 0.01, '3.2f'))
                # Delete existing node name attribute for node.
                node.name = ''


    # Root on the midpoint, because ete3 was having trouble identifying clades
    # in some of the unrooted trees.
    t2.set_outgroup(t2.get_midpoint_outgroup())
    t_with_abayes.set_outgroup(t_with_abayes.get_midpoint_outgroup())

    # Get list of nodes of interest.
    orthogroup_nodes = get_nodes_of_interest(t2, type_seq_list)

    ## Construct a dictionary storing the clade name corresponding to each
    ## sequence name in the input tree.
    #seq_clade_name_dict = {}
    #for nl in orthogroup_nodes:
    #    clade_name = get_clade_name_from_model2(nl[0], type_seqs_dict)
    #    for ln in [x.name for x in nl[1].get_leaves()]:
    #        seq_clade_name_dict[ln] = clade_name


    ###########################
    # Get lengths and supports for internal branches (excluding those within
    # the specific clades of interest) and add those to the dictionary as a
    # list of dictionaries.

    # Initiate list to store dictionaries with info for each internal branch.
    internal_branch_info_list = []

    # Copy the tree object(s).
    t3 = t2.copy()
    t3_abayes = t_with_abayes.copy()

    # Record initial number of nodes.
    initial_node_num = len(list(t3.traverse()))

    # Record which node is the original outgroup.
    original_outgroup = list(t3.traverse())[1]

    # Find nodes of interest in new tree object for detaching.
    orthogroup_nodes_t3 = get_nodes_from_actual_tree_obj(t3, [x[1] for x in orthogroup_nodes])
    orthogroup_nodes_t3_abayes = get_nodes_from_actual_tree_obj(t3_abayes, [x[1] for x in orthogroup_nodes])

    # Not necessary, because this is done in the get_nodes_from_actual_tree_obj
    # function.
    ## Re-root on one of the nodes of interest.
    #t3.set_outgroup(orthogroup_nodes_t3[0])
    #t3_abayes.set_outgroup(orthogroup_nodes_t3_abayes[0])

    #print('\nt3 before detaching nodes of interest:')
    #print(t3)

    # Detach all nodes of interest in the copy of the tree.
    #for i in to_remove_list:
    #print('orthogroup nodes:')
    for i in orthogroup_nodes_t3:
        #print(i)
        for j in i.iter_descendants():
            j.detach()
    for i in orthogroup_nodes_t3_abayes:
        for j in i.iter_descendants():
            j.detach()

    ## Temp.
    #print('\ntree with nodes removed (is this right???***):')
    #print(t3)
    #print('leaf nodes:')
    #print(t3.get_leaves())

    # Record (reduced) number of nodes.
    reduced_node_num = len(list(t3.traverse()))

    # Check that at least one node was actually removed.
    assert reduced_node_num < initial_node_num
    # Check that the tree has the minimum number of nodes.
    assert reduced_node_num >= len(orthogroup_nodes)
    # Check that the two pruned trees have the same number of nodes.
    assert len(list(t3.traverse())) == len(list(t3_abayes.traverse()))

    # Unroot pruned tree so that there are no internal branches that are split
    # up by the root.
    t3.unroot()
    t3_abayes.unroot()

    # Get *internal* branch lengths and support values from pruned copy of the
    # tree (all the branches left are internal branches of interest).
    internal_branch_info_list = []
    intbrnum = 0
    for node_alrt_sup, node_abayes_sup in zip(t3.traverse(), t3_abayes.traverse()):
        # ***Ignore the branches that lead to clades of interest. Note: This
        # may not always be what is needed.
        if len(list(node_alrt_sup.traverse())) > 1 and len(list(node_alrt_sup.traverse())) > 1:
            # Get branch length.
            assert node_alrt_sup.dist == node_abayes_sup.dist
            branch_length = node_alrt_sup.dist

            # Ignore the root node (branch length 0).
            if branch_length > 0:
                # Initiate dict to store info for this branch.
                branch_dict = {}

                # Add branch length to dict.
                branch_dict['branch length'] = branch_length

                # Add branch supports to dict.
                branch_dict['alrt support'] = node_alrt_sup.support
                branch_dict['abayes support'] = node_abayes_sup.support

                # Add dict to list of branch dicts.
                internal_branch_info_list.append(branch_dict)

    # Check that a minimum number of internal nodes were identified.
    #assert len(internal_branch_lengths) >= len(orthogroup_nodes), """Too few
    #internal nodes identified."""

    # Add internal branch lengths and supports as a list of dicts to the output
    # dict.
    branch_length_info_dict['internal branches info list'] = internal_branch_info_list

    ###########################
    # Determine characteristics of clades of interest.
    num = 0
    for seq_node_list in orthogroup_nodes:
        num += 1
        type_seq = seq_node_list[0]
        clade_name = get_clade_name_from_model2(type_seq, type_seqs_dict)
        node = seq_node_list[1]

        #print('\n\nClade defined by sequence ' + type_seq + ':')
        #print(node)

        # Get list of leaf names.
        leaf_names = get_list_of_leaf_names_for_node(node)

        # Get stem length for node.
        stem_len = node.dist
        #print('\nStem length: ' + str(stem_len))

        # Get branch lengths for all sequences in the clade.
        #print('\nBranch lengths:')
        seq_branch_lengths = []
        for n in node.traverse():
            if n.is_leaf():
                length = node.get_distance(n)
                #print('\t' + n.name + ': ' + str(length))
                seq_branch_lengths.append([n.name, length])

        # Get longest branch length.
        max_len = max(seq_branch_lengths, key=lambda x: x[1])
        #print('\n\tLongest branch: ' + max_len[0] + ' ' + str(max_len[1]))

        # Get shortest branch length.
        min_len = min(seq_branch_lengths, key=lambda x: x[1])
        #print('\n\tShortest branch: ' + min_len[0] + ' ' + str(min_len[1]))

        # Get average branch length relative to ancestral/root node in the
        # clade for each sequence/terminal/leaf node.
        mean_len = statistics.mean([x[1] for x in seq_branch_lengths])
        #print('\n\tMean length: ' + str(mean_len))

        # Get median branch length relative to ancestral/root node in the
        # clade for each sequence/terminal/leaf node.
        median_len = statistics.median([x[1] for x in seq_branch_lengths])
        #print('\n\tMedian length: ' + str(median_len))

        # Calculate ratio of stem length to average branch length.
        stem_branches_ratio = stem_len / mean_len
        #print('\n\tRatio of stem len to avg branch len: ' + str(stem_branches_ratio))


        # Format tree for visualization.

        # Root on first clade of interest.
        if num == 1:
            #print('\n\n\n\n')
            #print('t2:')
            #print(t2)
            #print(t2.write())
            #print('node:')
            #print(node)
            #print('\n\n\n\n')
            t2.set_outgroup(get_corresponding_node(node,t2))


        # This loop temporarily commented out to allow running on
        # computecanada (see also below):

        # Make stem branch for clade of interest bold.
        stem_node = get_corresponding_node(node, t2)
        stem_node.set_style(style_dict['stem_node'])

        # Add clade name to stem branch.
        #stem_node.name = clade_name
        stem_node.add_face(define_textface_for_labeling_stem(clade_name), column=0, position = "branch-top")

        # Iterate over branches within clade and customize appearance.
        for leaf in node.iter_leaves():
            # Set general features for all leaf nodes.
            style = NodeStyle()
            style["fgcolor"] = "#0f0f0f"
            style["size"] = 0
            style["vt_line_color"] = "#000000"
            style["hz_line_color"] = "#000000"

            #style["vt_line_width"] = 8
            #style["hz_line_width"] = 8
            #style["vt_line_type"] = 0 # 0 solid, 1 dashed, 2 dotted
            #style["hz_line_type"] = 0

            # Make shortest branch in clade of interest bold.
            if leaf.name == min_len[0]:
                #shortbranchnode = get_corresponding_node(t1.search_nodes(name=min_len[0])[0], t2)
                #shortbranchnode.set_style(style_dict['shortest branch'])
                style["hz_line_width"] = 5

            # Make longest branch in clade of interest bold.
            if leaf.name == max_len[0]:
                #longbranchnode = get_corresponding_node(t1.search_nodes(name=max_len[0])[0], t2)
                #longbranchnode.set_style(style_dict['longest branch'])
                style["hz_line_width"] = 5
                style["hz_line_type"] = 2
            
            # Customize leaf node appearance.
            # Get species name.
            #species_name = leaf.name.replace('__', ' ').replace('_', ' ').split(' ', 1)[1]
            species_name = get_species_name_from_seq_id(leaf.name)
            #print(species_name)

            # Check that the name does not end with '.copy'.
            assert not species_name.endswith('.copy'), """A sequence with an
            identical name to a sequence already in the alignment/tree was
            apparently added: %s""" % leaf.name

            ti = get_taxonomic_info(species_name)
            #print('\t' + ' '.join([str(ti.superbranch), str(ti.supergroup),
            #    str(ti.group), str(ti.species)]))

            # Set style for node.
            get_corresponding_node(leaf, t2).set_style(style)

        # Sort seq names by descending branch lengths.
        seq_names_by_br_len = [n.name for n in sorted(node.get_leaves(),\
                key=lambda n: node.get_distance(n), reverse=True)]

        # Identify most "basal" sequence in the clade, and the length of the
        # stem for the remaining seqs.
        # The node that is sister to the most basal sequence would be the one
        # that has the most daughter nodes.
        basal_node = None
        node_sister_to_basal_node = None
        for n in node.iter_descendants():
            if node_sister_to_basal_node is None:
                node_sister_to_basal_node = n
            if len(n.get_leaves()) > len(node_sister_to_basal_node.get_leaves()):
                node_sister_to_basal_node = n
        sister_leaf_names = [x.name for x in node_sister_to_basal_node.get_leaves()]
        for n in node:
            in_sister = True
            for x in n.iter_leaves():
                if not x.name in sister_leaf_names: 
                    in_sister = False
                    break
            if not in_sister:
                basal_node = n
                break
        # Check whether the basal node was identified.
        assert basal_node is not None
        # Define name of basal node.
        basal_node_name = 'clade'
        if basal_node.is_leaf():
            basal_node_name = basal_node.name
        # Define stem length of the clade that is sister to the "basal" clade.
        basal_node_depth = node.get_distance(node_sister_to_basal_node)

        # Get support values for clade.
        alrt_support_value = node.support
        #print('alrt: ' + str(alrt_support_value))
        # Have to retrieve abayes value from another tree object.
        abayes_support_value =\
        get_abayes_support_for_node_from_another_tree(node, t_with_abayes)
        #print('abayes: ' + str(abayes_support_value))

        # Add info to output dictionary.
        branch_length_info_dict[clade_name] =\
                {'stem length': stem_len,
                 'average branch length': mean_len,
                 'stem/branch ratio': stem_branches_ratio,
                 'seq names by descending length': seq_names_by_br_len,
                 'basal node name': basal_node_name,
                 'basal node depth': basal_node_depth,
                 #'internal branch lengths': internal_branch_lengths,
                 'alrt support': alrt_support_value,
                 'abayes support': abayes_support_value
                 }


    ## Write a modified taxon name conversion table file with clade names
    ## appended to taxon/sequence names for future use. ***No longer necessary,
    ## because this is handled by the visualize_tree command.

    ## Define path to original table file.
    #original_table_file =\
    #find_input_file_in_parent_directory(os.path.dirname(ml_tree_path), 'table', [])

    ## Make a copy of the original table file.
    #original_table_file_copy =\
    #original_table_file + '_original'
    #shutil.copyfile(original_table_file, original_table_file_copy)

    ## Define path to temporary modified file.
    #original_table_file_temp =\
    #original_table_file + '_TEMP'

    ## Loop over lines in original table.
    #with open(original_table_file) as tablefh,\
    #    open(original_table_file_temp,'w') as o:
    #    for i in tablefh:
    #        if i.startswith('ZZ') and '_' not in i:
    #            o.write(i)
    #        elif i.strip() == '':
    #            o.write(i)
    #        else:
    #            o.write(i.strip() + '__' + seq_clade_name_dict[i.strip()].strip() + '\n')

    ## Copy over the original table file path with the temporary file contents.
    #os.remove(original_table_file)
    #os.rename(original_table_file_temp, original_table_file)


    # Show tree annotations.

    # Remove underscores from leaf names.
    for leaf in t2.iter_leaves():
        leaf.name = leaf.name.replace('__', ' ').replace('_', ' ')

    # Stretch branches.
    ts = TreeStyle()
    ts.show_leaf_name = True
    ts.scale =  120 # 120 pixels per branch length unit

    # Add title.
    #tree_title = "[Tree title here]"
    tree_title = ""
    ts.title.add_face(TextFace(tree_title, fsize=20), column=0)

    # Show.
    #t2.show(tree_style=ts)

    # Write tree to file.
    if annotated_tree_outpath is not None:
        t2.render(annotated_tree_outpath, w=183, units="mm", tree_style=ts)

    # Return main output path.
    return branch_length_info_dict


def get_constraint_tree_fp(outalifpnex):
    """Take a path to an alignment, and return a path to use for a
    corresponding contraint tree topology.
    """
    #constraint_tree_fp = outalifpnex.rsplit('.', 1)[0] + '_constraint_tree.newick'
    constraint_tree_fp = outalifpnex.rsplit('.', 1)[0] + '.C_constraint_tree.newick'
    return constraint_tree_fp


def run_tree_for_branch_lengths_and_supports_for_topology(tree,
                                                          alignment,
                                                          subs_model,
                                                          outputdir,
                                                          place_seq=False):
    """Run an ML tree and branch support tests given a tree (for constraining
    topology), an alignment file, and a substitution model. Return path to
    output tree file.

    Optionally use the place_seq option to just do an ML search to place a
    sequence in a constrained topology with the -g option.
    """
    # Get list of all sequence names in alignment.
    all_seq_names = [x.name for x in AlignIO.read(alignment, 'nexus')]

    # Check that the input tree file exists.
    assert os.path.isfile(tree), """Input tree file path doesn't exist."""

    # Get list of all leaf names for tree.
    quoted_node_names_var = False
    with open(tree) as infh:
        if '\"' in infh.read(): 
            quoted_node_names_var = True
    tx = Tree(tree, quoted_node_names=quoted_node_names_var)
    all_leaf_names = [x.name for x in tx.get_leaves()]

    # Check that the list of leaf names is the same as the list of sequence
    # names in the alignment.
    #for i, j in zip(sorted(all_seq_names), sorted(all_leaf_names)):
    #    print(i + ', ' + j)
    #print(all_seq_names)
    #print(all_leaf_names)
    if place_seq:
        assert len(all_leaf_names) == len(all_seq_names) - 1, """Constraint tree
        should have one less sequence than alignment."""
    else:
        assert len(all_leaf_names) == len(all_seq_names), """Different number of
        sequences represented in the tree vs. alignment."""

    # Convert nexus alignment to afa.
    temp_fa_1 = os.path.join(outputdir,\
            os.path.basename(alignment).rsplit('.', 1)[0] + '_temp1.afa')
    nex_to_afa(alignment, temp_fa_1) 

    # Code names in alignment.
    outalifp = alignment.rsplit('.', 1)[0] + '.C.afa'
    outtablefp = alignment.rsplit('.', 1)[0] + '.C.table'
    code_names_in_ali(outputdir, temp_fa_1, outalifp, outtablefp) 

    # Convert alignment back to nexus.
    outalifpnex = alignment.rsplit('.', 1)[0] + '.C.nex'
    afa_to_nex(outalifp, outalifpnex)

    # Get list of all sequence names in coded alignment.
    all_seq_names = [x.name for x in AlignIO.read(outalifpnex, 'nexus')]

    # Delete temporary files.
    os.remove(temp_fa_1)
    os.remove(outalifp)

    # Define path for intermediate unrooted tree.
    tree2 = outalifpnex.rsplit('.')[0] + '_unrooted_tree.newick'

    # Parse tree using ete3.
    # Note: parentheses and commas and colons get replaced with underscores by
    # ete3.
    quoted_node_names_var = False
    with open(tree) as infh:
        if '\"' in infh.read(): 
            quoted_node_names_var = True
    t1 = Tree(tree, quoted_node_names=quoted_node_names_var)

    # Unroot tree.
    t1.unroot()

    # Write unrooted tree to a new file.
    t1.write(outfile=tree2, format=9)
    #print('tree2:')
    #print(tree2)
    assert os.path.isfile(tree2), """Tree topology file not produced:
    %s""" % tree2

    # Define path for constraint tree file.
    constraint_tree_fp_coded = None
    # Only do the following steps once for all the alignments, because all the
    # constrained topology analyses will use the same constraint trees.

    # Put quotation marks around names in constraint tree. # SEPARATE
    #outtreefp = ali.rsplit('.', 1)[0] + '.constraint_tree0.Q.newick'
    constraint_tree_fp = None
    if place_seq:
        # Use the input tree path as the constraint tree if the place_seq
        # option is used (because using the previous topology without the new
        # sequence to constrain the ML tree search).
        constraint_tree_fp = tree
        #constraint_tree_fp = get_constraint_tree_fp(alignment)
        #print('\n\n')
        #print(tree)
        #print(alignment)
        assert os.path.isfile(constraint_tree_fp), """Expected to find
        constraint tree at this file path:\n%s""" % constraint_tree_fp
    else:
        constraint_tree_fp = get_constraint_tree_fp(alignment)

        with open(tree2) as intreefh, open(constraint_tree_fp, 'w') as o:
            for t in intreefh:
                o.write(quote_tree(t, outtablefp))
    assert os.path.isfile(constraint_tree_fp), """Expected to find
    constraint tree at this file path:\n%s""" % constraint_tree_fp

    # Make constraint tree with coded names.
    constraint_tree_fp_coded = constraint_tree_fp.rsplit('.', 1)[0] + '.C.tre'
    code_tree(constraint_tree_fp, constraint_tree_fp_coded, outtablefp)
    #print('constraint_tree_fp_coded:')
    #print(constraint_tree_fp_coded)
    assert os.path.isfile(constraint_tree_fp_coded), """Coded constraint tree
    not produced."""

    # Get list of all leaf names for tree.
    quoted_node_names_var = False
    with open(constraint_tree_fp_coded) as infh:
        if '\"' in infh.read(): 
            quoted_node_names_var = True
    tx = Tree(constraint_tree_fp_coded, quoted_node_names=quoted_node_names_var)
    all_leaf_names = [x.name for x in tx.get_leaves()]

    # Check that the list of leaf names is the same as the list of sequence
    # names in the alignment.
    if place_seq:
        assert len(all_leaf_names) == len(all_seq_names) - 1, """Different number of
        sequences represented in the tree vs. alignment."""
    else:
        assert len(all_leaf_names) == len(all_seq_names), """Different number of
        sequences represented in the tree vs. alignment."""
        assert set(all_leaf_names) == set(all_seq_names), """Sequence names in tree
        and alignment differ."""


    # Make a copy of the alignment in phylip format for input to IQtree.
    phy_out = outalifpnex.rsplit('.', 1)[0] + '.phy'
    nex_to_phylip(outalifpnex, phy_out)

    # Do phylogenetic analysis.

    output_file_prefix = None

    if place_seq:
        # Make subdir for output.
        iter_num_str = alignment.rsplit('.', 1)[0].rsplit('_', 1)[1]
        subdirp = constraint_tree_fp.rsplit('.', 1)[0] +\
        '_IQ-tree_output_place_seq_' + iter_num_str
        if os.path.isdir(subdirp):
            random_id_string = str(random.randint(1, 1000))
            subdirp = subdirp + '_' + random_id_string 
        os.mkdir(subdirp)


        # ***This code block may not always be necessary, and can be commented out
        # later to speed up the analysis:
        # Check that constraint tree is as expected:
        # Check number of taxa in constraint tree.
        tx = Tree(constraint_tree_fp_coded)
        num_taxa_in_constraint_tree = len(tx.get_leaves())
        nonredun_num_taxa_in_constraint_tree = len(list(set([x.name for x in tx.get_leaves()])))
        # Check that there is at least one taxon represented in the constraint
        # tree.
        assert num_taxa_in_constraint_tree >= 1 
        # Check that there are no redundant sequences in constraint tree.
        assert num_taxa_in_constraint_tree == nonredun_num_taxa_in_constraint_tree
        # Get number of sequences in alignment.
        num_seqs_in_ali = int(open(phy_out, 'r').readline().strip().split(' ')[0])
        # Check that the number of sequences in the constraint tree is one less
        # than the number in the alignment, because the alignment should have
        # the additional sequence to be placed.
        assert num_taxa_in_constraint_tree == num_seqs_in_ali - 1


        # Use IQtree to do an ML search
        output_file_prefix = os.path.join(subdirp, 'iqtree')
        iqtree_command_list = ['iqtree',
                               '-s', phy_out,
                               '-m', subs_model,
                               '-g', constraint_tree_fp_coded, 
                               '-pre', output_file_prefix, 
                               '-nt', '2'
                               ]
        #print(' '.join(iqtree_command_list))
        #print('constraint_tree_fp_coded')
        #print(constraint_tree_fp_coded)
        stdout_path = output_file_prefix + '.stdout.txt'
        with open(stdout_path, 'w') as o:
            subprocess.call(iqtree_command_list, stdout=o, stderr=subprocess.STDOUT)
        assert os.path.isfile(stdout_path), """IQtree standard output not
        written to a file."""
        #print('stdout_path:')
        #print(stdout_path)

    else:
        # Make subdir for output.
        subdirp = constraint_tree_fp.rsplit('.', 1)[0] + '_IQ-tree_output'
        os.mkdir(subdirp)

        # Use IQtree to do an ML search
        output_file_prefix = os.path.join(subdirp, 'iqtree')
        iqtree_command_list = ['iqtree',
                               '-s', phy_out,
                               '-m', subs_model,
                               '-te', constraint_tree_fp_coded,
                               '-alrt', '1000',
                               '-abayes',
                               '-pre', output_file_prefix, 
                               '-nt', '2'
                               ]
        #print(' '.join(iqtree_command_list))
        #print('constraint_tree_fp_coded')
        #print(constraint_tree_fp_coded)
        stdout_path = output_file_prefix + '.stdout.txt'
        with open(stdout_path, 'w') as o:
            subprocess.call(iqtree_command_list, stdout=o, stderr=subprocess.STDOUT)
        assert os.path.isfile(stdout_path), """IQtree standard output not
        written to a file."""

    # Define path to output file.
    tree_file_path = output_file_prefix + '.treefile'
    # Check that the output file was actually produced.
    assert os.path.isfile(tree_file_path), """IQtree did not produce a
    treefile."""

    # Parse output tree.
    # Note: parentheses and commas get replaced with underscores.

    # Uncode tree.
    tree_file_path2 = tree_file_path + '2'
    uncode_tree(tree_file_path, tree_file_path2, outtablefp)

    # Return path to the tree with uncoded taxon names.
    return tree_file_path2 


def get_type_seqs_dict(type_seqs):
    """Take a path to a file listing sequences that define nodes of interest in
    a tree, and construct a dictionary with clade names as keys and sequence
    names as values.
    """
    type_seqs_dict = {}
    with open(type_seqs) as infh:
        for i in infh:
            if not i.startswith('\n'):
                spliti = i.strip().split(',')
                seqname = spliti[0]
                cladename = spliti[1]
                type_seqs_dict[cladename] = seqname
    return type_seqs_dict

def get_essential_taxa_list(essential_taxa_file):
    """Take a path to a file listing essential taxa (taxonomy terms) and return
    a list of the terms in the file.
    """
    essential_taxa = []
    if essential_taxa_file is not None:
        with open(essential_taxa_file) as infh:
            for i in infh:
                if not i.startswith('#') and not i.startswith('\n'):
                    taxon = i.strip()
                    essential_taxa.append(taxon)
        assert len(essential_taxa) > 0
    return essential_taxa


def get_y_measure_of_support(previous_ali_tree_tuple,
                             include_internal_branches=False,
                             input_modified_clade_name=None):
    """Take a tuple with objects containing info about an alignment and tree,
    and extract specific info to use as a measure of support for nodes of
    interest.

    *** Need to get support for all nodes of interest, not just for clades of
    interest, but also backbone nodes, and find the one with the lowest
    support.
    """
    # Get info dict from input tuple.
    ml_tree_info_dict = previous_ali_tree_tuple[6]
    modified_clade_name = previous_ali_tree_tuple[13]
    if modified_clade_name is None:
        modified_clade_name = input_modified_clade_name

    # For reference:
    #ml_tree_info_dict[clade_name] =\
    #        {'stem length': stem_len,
    #         'average branch length': mean_len,
    #         'stem/branch ratio': stem_branches_ratio,
    #         'seq names by descending length': seq_names_by_br_len,
    #         'basal node name': basal_node_name,
    #         'basal node depth': basal_node_depth,
    #         'internal branch lengths': internal_branch_lengths,
    #         'alrt support': alrt_support_value,
    #         'abayes support': abayes_support_value
    #         }

    # Initiate variable for storing lowest support value.
    lowest_support_value = None 
    average_support_value = None

    # Remove info list for internal branches from dict keys for
    # consideration.
    clade_list = list(ml_tree_info_dict.keys())
    clade_list.remove('internal branches info list')

    # Get list of stem/branch length ratios for all clades of interest.
    all_stem_branch_ratios = [float(ml_tree_info_dict[clade]['stem/branch ratio'])\
                              for clade in clade_list] 

    # Get minimum stem/branch ratio for clades of interest. 
    minimum_stem_branch_ratio = min(all_stem_branch_ratios)

    # Get stem/branch ratio for the clade that was modified (if applicable). 
    modified_clade_stem_branch_ratio = None
    if modified_clade_name is not None: 
        modified_clade_stem_branch_ratio =\
        ml_tree_info_dict[modified_clade_name]['stem/branch ratio']

    # Get average stem/branch ratio for clades of interest.
    average_stem_branch_ratio = sum(all_stem_branch_ratios) / len(all_stem_branch_ratios)

    # Get list of all deep branch lengths.
    all_dbranch_lengths = [float(x['branch length']) for x in ml_tree_info_dict['internal branches info list']]

    ## Get average length of stems for clades of interest.
    #all_clade_stem_lengths = [float(ml_tree_info_dict[clade]['stem length'])\
    #                          for clade in clade_list]
    #average_clade_stem_lengths = sum(all_clade_stem_lengths) / len(all_clade_stem_lengths)

    ## Get list of all deep branch/average stem length ratios.
    #all_dbranch_avgstem_ratios = [float(x / average_clade_stem_lengths)\
    #                              for x in all_dbranch_lengths]

    ## Get minimum deep branch/average stem length ratio.
    ## Get all average branch length ratios.
    #min_dbranch_avgstem_ratio = min(all_dbranch_avgstem_ratios)

    # Get average of average leaf lengths (measured from the parent node of the
    # clade of interest that the leaf is in).
    avg_leaf_length = sum([float(ml_tree_info_dict[clade]['average branch length'])\
                       for clade in clade_list]) / len(clade_list)

    # Get list of all deep branch/average leaf lengths (measured from nodes for
    # specific clades of interest, averaged over all leaves).
    all_dbranch_avgleaf_ratios = [float(x / avg_leaf_length)\
                                  for x in all_dbranch_lengths]

    # Get minimum ratio of deep branch length to average leaf length.
    min_dbranch_avgleaf_ratio = min(all_dbranch_avgleaf_ratios)

    # Get average ratio of deep branch length to average leaf length.
    avg_dbranch_avgleaf_ratio = sum(all_dbranch_avgleaf_ratios)\
                                / len(all_dbranch_avgleaf_ratios)

    # Examine the alrt and abayes support values for relevant clades.
    if not include_internal_branches:
        # Just consider branch supports for the specific clades of interest.

        # Compile a list of all the relevant support values (both alrt and
        # abayes).
        all_alrt_values = [float(ml_tree_info_dict[x]['alrt support']) for x in clade_list]
        all_abayes_values = [float(ml_tree_info_dict[x]['abayes support']) for x in clade_list]

        # Get the lowest values.
        lowest_alrt_support_value = min(all_alrt_values)
        #print(lowest_alrt_support_value)
        lowest_abayes_support_value =\
            min(all_abayes_values)
        #print(lowest_abayes_support_value)
        lowest_support_value =\
            min([lowest_alrt_support_value, lowest_abayes_support_value])

        # Calculate the average over all the values.
        all_values = all_alrt_values + all_abayes_values
        average_support_value = sum(all_values) / len(all_values)

    else:
        # Consider the branch supports for the specific clades of interest, as well
        # as all branches that are internal to those clades.

        # Get values for internal branches.
        internal_alrt_values =\
            [float(x['alrt support']) for x in ml_tree_info_dict['internal branches info list']]
        internal_abayes_values =\
            [float(x['abayes support']) for x in ml_tree_info_dict['internal branches info list']]

        # Compile a list of all the relevant support values (both alrt and
        # abayes).
        all_alrt_values = [float(ml_tree_info_dict[x]['alrt support']) for x in clade_list]\
                + internal_alrt_values
        all_abayes_values = [float(ml_tree_info_dict[x]['abayes support']) for x in clade_list]\
                + internal_abayes_values

        # Get the lowest values.
        lowest_alrt_support_value = min(all_alrt_values)
        #print(lowest_alrt_support_value)
        lowest_abayes_support_value =\
            min(all_abayes_values)
        #print(lowest_abayes_support_value)
        lowest_support_value =\
            min([lowest_alrt_support_value, lowest_abayes_support_value])

        # Calculate the average over all the values.
        all_values = all_alrt_values + all_abayes_values
        average_support_value = sum(all_values) / len(all_values)

    # Check that the value was found.
    assert lowest_support_value is not None
    assert average_support_value is not None

    # Return measure of support.
    #return lowest_support_value
    #return average_support_value
    return (lowest_support_value, average_support_value,
            minimum_stem_branch_ratio, average_stem_branch_ratio,
            min_dbranch_avgleaf_ratio, avg_dbranch_avgleaf_ratio,
            modified_clade_stem_branch_ratio)


def get_ali_length(alignment):
    """Take a filepath to an alignment file in nexus format and return the
    length of the sequences in the alignment.
    """
    alignment_length = None
    with open(alignment) as infh:
        ali_obj = AlignIO.read(infh, 'nexus')
        first_seq_obj = ali_obj[0]
        alignment_length = len(first_seq_obj)
    assert alignment_length is not None
    return alignment_length 


def new_tree_better(prev_tree_measure,
                    new_tree_measure,
                    mod_type,
                    intensive_mod_type):
    """Apply criteria to tuples containing information about two trees to
    determine which is better (old or new), and return True if the new tree is
    better.
    """
    # Note: Contents of tuple returned by the get_y_measure_of_support function
    # (X_tree_measure variables):
    # 1. lowest_support_value,
    # 2. average_support_value,
    # 3. minimum_stem_branch_ratio,
    # 4. average_stem_branch_ratio,
    # 5. min_dbranch_avgleaf_ratio,
    # 6. avg_dbranch_avgleaf_ratio,
    # 7. modified_clade_stem_branch_ratio

    # Apply criteria based on comparing values between trees.
    #if new_tree_measure[0] >= prev_tree_measure[0] and new_tree_measure[1] >= prev_tree_measure[1]:
    #if new_tree_measure[2] >= prev_tree_measure[2] and new_tree_measure[3] >= prev_tree_measure[3]:
    # This is the best so far:
    #if new_tree_measure[4] >= prev_tree_measure[4] and new_tree_measure[5] >= prev_tree_measure[5]:
    # No attention to deep backbone:
    #if new_tree_measure[4] >= prev_tree_measure[4]:

    ## No criteria applied at all:
    #if 2 == 2:
    #    print('\t\t\tWarning: No criteria applied.')
    #    print('\t\t\tNew tree is better.')
    #    previous_ali_tree_tuple = new_ali_tree_tuple

    if mod_type == 'add_seqs':
        ## Just say the new tree is better if a sequence has been added.
        #return True

        ## Apply inclusive criteria.
        #if new_tree_measure[4] >= prev_tree_measure[4] and new_tree_measure[5] >= prev_tree_measure[5]:
        # Only require that the clade that was modified has a branch length
        # ratio that is at least as good as in the previous tree.
        if new_tree_measure[6] >= (prev_tree_measure[6] * 0.95):
            # Return True to indicate that the new tree is better.
            return True
        else:
            # Return False to indicate that the old tree is better.
            return False

    else:
        ## Apply inclusive criteria.
        #if new_tree_measure[4] >= prev_tree_measure[4] and new_tree_measure[5] >= prev_tree_measure[5]:
        # Only require that the clade that was modified has a branch length
        # ratio that is at least as good as in the previous tree.
        if new_tree_measure[6] >= prev_tree_measure[6]:
            # Return True to indicate that the new tree is better.
            return True
        else:
            # Return False to indicate that the old tree is better.
            return False


def search_alignment_space(model_name,
                           out_dir_path,
                           mod_type,
                           iterations,
                           keep_all_output,
                           timestamp,
                           file_with_seqs=None, 
                           essential_taxa_file=None):
    """Master function to manage the iterative process of modifying an
    alignment/tree, and assessing whether the modification results in better
    branch support for a topology of interest. In other words, optimize an
    alignment to support a backbone topology for clades of interest in the
    tree. IMPORTANT: Do this in parallel for alternative topologies and compare
    results to avoid cherry-picking.

    Replacement for optimize_sequence_selection2 and
    optimize_position_selection functions.
    """
    # Check that modification type is valid.
    assert mod_type in ['remove_seqs', 'add_seqs', 'remove_columns', 'mixed',
    'intensive']
    """Invalid value provided with --mod_type option."""

    # Define output directory path.
    outputdir = os.path.join(out_dir_path,\
            model_name + '_srch_ali_space_' + timestamp)

    # Make output directory.
    assert not os.path.isdir(outputdir)
    os.mkdir(outputdir)

    # Unpack information about current dataset and tree including assessment of
    # relevant branch supports.

    # Parse data from model.
    # Get info about model that is relevant.
    print('Parsing input alignment/tree...')
    model_info = ModelInfoFromCSV(model_name)
    alignment = model_info.alignment_file
    tree = model_info.tree_topology_file
    subs_model = model_info.subs_model
    type_seqs_dict = get_type_seqs_dict(model_info.type_seqs_file)

    # Parse tree using ete3.
    # Note: parentheses and commas get replaced with underscores.
    quoted_node_names_var = False
    with open(tree) as infh:
        if '\"' in infh.read():
            quoted_node_names_var = True
    t1 = Tree(tree, quoted_node_names=quoted_node_names_var)

    # Print tree.
    print('Input tree:')
    print(t1)

    # Compile list of sequences represented in the input initial tree.
    names_of_seqs_in_tree = [x.name for x in t1.get_leaves()]
    assert len(names_of_seqs_in_tree) > 0, """Could not identify names of
    sequences in the tree."""

    # Get list of essential taxa from file. 
    essential_taxa = get_essential_taxa_list(essential_taxa_file)

    # Copy alignment file to new path, and replace parentheses and commas and
    # colons with underscores in the sequence descriptions.
    new_ali_path = os.path.join(outputdir,
            os.path.basename(alignment).rsplit('.', 1)[0] + '_0.nex')
    problem_characters = re.compile(r'\(|\)|:|,')
    with open(alignment) as infh, open(new_ali_path, 'w') as o:
        ali_obj = AlignIO.read(infh, 'nexus')
        for seq in ali_obj:
            seq.id = problem_characters.sub('_', seq.id)
        AlignIO.write(ali_obj, o, 'nexus')
    assert os.path.isfile(new_ali_path)
    alignment = new_ali_path 

    # Run ML search on model tree to get branch lengths and branch supports.
    ml_tree_path =\
    run_tree_for_branch_lengths_and_supports_for_topology(tree,
                                                          alignment,
                                                          subs_model,
                                                          outputdir)

    # Define path to tree to use as a constraint tree for further analysis.
    constraint_tree_fp_for_future = get_constraint_tree_fp(alignment)
    #constraint_tree_fp_for_future = alignment.rsplit('.', 1)[0] + '_constraint_tree.newick'
    assert os.path.isfile(constraint_tree_fp_for_future), """Expected to find
    constraint tree with file path:\n%s""" % constraint_tree_fp_for_future

    # Define output path for annotated tree image file.
    annotated_tree_outpath =\
    os.path.join(alignment.rsplit('.', 1)[0] + '_annotated_result.png')

    # Extract info about branch lengths and supports from tree, and write
    # annotated tree image file.
    ml_tree_info_dict = get_ml_tree_info_dict(ml_tree_path,
                                              type_seqs_dict,
                                              annotated_tree_outpath)


    # ***Also, need to make it stop iterating if it can't do any more
    # modifications.

    # Parse input sequence file, and construct a list of sequence objects for
    # potential inclusion in the tree.
    seqs = []
    if file_with_seqs is not None:
        for seq in SeqIO.parse(file_with_seqs, 'fasta'):
            seqs.append(seq)
    if mod_type == 'add_seqs':
        assert len(seqs) > 0, """No sequences provided for addition to the
        alignment."""

    # Initiate lists of elements that will be modified.
    positions_attempted_to_remove = []
    seqs_attempted_to_remove = []
    seqs_attempted_to_add = []
    stop = False # Stores true if no modification can be made by the modify_alignment_in_x_way function.

    # Construct a tuple with all the relevant info from the original tree and
    # alignment.
    previous_ali_tree_tuple = (0,
                               #tree, # ???
                               constraint_tree_fp_for_future,
                               alignment,
                               positions_attempted_to_remove,
                               subs_model,
                               type_seqs_dict,
                               ml_tree_info_dict,
                               seqs,
                               seqs_attempted_to_remove,
                               seqs_attempted_to_add,
                               essential_taxa,
                               stop,
                               False,
                               None)


    # Handle number of iterations.
    max_iterations = 0
    if iterations is None:
        # Specify a very large number by default so that it will run until no
        # further modifications result in improvements (it should break the
        # loop before 10000!).
        max_iterations = 1000
    else:
        max_iterations = int(iterations)
    assert max_iterations > 0

    ## Specify number of iterations that do not find improved support before the
    ## loop gets broken.
    #max_failed_iterations = 0
    #if mod_type == 'remove_seqs':
    #    #max_failed_iterations = len(names_of_seqs_in_tree) * 2
    #    #max_failed_iterations = len(names_of_seqs_in_tree) / 2
    #    max_failed_iterations = 2
    #elif mod_type == 'add_seqs':
    #    #max_failed_iterations = len(seqs) * 2
    #    #max_failed_iterations = len(seqs)
    #    #max_failed_iterations = len(names_of_seqs_in_tree)
    #    max_failed_iterations = 2
    #elif mod_type == 'remove_columns':
    #    original_alignment_length = get_ali_length(alignment)
    #    max_failed_iterations = original_alignment_length
    #elif mod_type == 'mixed':
    #    max_failed_iterations = max_iterations
    #assert max_failed_iterations > 0

    # Determine number of positions in the input alignment (length of the
    # sequences including gaps).
    original_alignment_length = get_ali_length(alignment)

    # Specify number of iterations that do not find improved support before the
    # loop gets broken.
    max_failed_iterations = 0
    max_failed_iterations_dict = {
                                 #'remove_seqs': len(names_of_seqs_in_tree) / 10,
                                 'remove_seqs': len(names_of_seqs_in_tree) * 2,
                                 #'add_seqs': len(names_of_seqs_in_tree) / 10,
                                 'add_seqs': len(seqs),
                                 'remove_columns': original_alignment_length,
                                 'mixed': 1, # Not used.
                                 'intensive': 1 # Not used.
                                 }
    max_failed_iterations = max_failed_iterations_dict[mod_type]
    assert max_failed_iterations > 0

    # Define iterable to provide order of different modification types if the
    # mod_type is set to 'mixed'. The mod_type will repeat through this
    # sequence, switching the value of the mod_type variable when the default
    # maximum number of failed modifications are reached for each modification
    # type.
    mod_type_mix_iterable = iter([
                                 'remove_seqs',
                                 'add_seqs'
                                 ] * 100000)

    # Define iterable to provide a program of different modification types for
    # if the mod_type variable is set to 'intensive'. The iterative
    # modifications will stop when the 'Stop' value is reached.
    mod_type_intensive_iterable = iter(['add_seqs',
                                        'remove_seqs',
                                        'remove_seqs',
                                        'Stop'
                                        ])

    # Set initial mod_type value if mod_type was set to mixed. 
    mixed_mod_type = False
    if mod_type == 'mixed':
        # Set this variable to True so that the mod_type will be switched
        # instead of exiting after one modification type is completed.
        mixed_mod_type = True

        # Get initial value from iterable.
        mod_type = next(mod_type_mix_iterable)

    # Set initial mod_type value if mod_type was set to intensive.
    intensive_mod_type = False
    if mod_type == 'intensive':
        intensive_mod_type = True
        mod_type = next(mod_type_intensive_iterable)

    # Initiate variable for storing the number of the best alignment.
    #best_alignment_num = 'the original input alignment'
    best_alignment_num = '0'

    # Initiate a list of alignment/iteration numbers corresponding to output
    # files to keep for future reference.
    alignment_nums_to_keep = []

    # Iteratively modify the alignment and assess support in the tree.
    print('\nIteratively modifying and assessing alignments/trees...')
    failed_iterations_tally = 0
    for iteration in range(0, max_iterations):
        print('\tIteration ' + str(iteration + 1) + ':')
        # Modify alignment (and tree if necessary). There are various types of
        # modifications that could be done: 1) Remove a sequence, 2) Add a
        # sequence, 3) Remove positions/columns from the alignment, 4)
        # Re-align, 5) Reset the substitution model.
        print('\t\tModifying alignment (and tree) in X way, and assessing measures of branch support in new tree...') 
        new_ali_tree_tuple =\
        modify_alignment_in_x_way(previous_ali_tree_tuple, mod_type)

        # Report name of modified clade.
        modified_clade_name = new_ali_tree_tuple[13]
        if modified_clade_name is not None:
            print('\t\t\tModified clade with name: %s' % modified_clade_name)

        # Stop if no modification could be made (the stop variable is set to
        # True).
        if new_ali_tree_tuple[11]:
            # Stop iterations.
            print('\nStopping iterations because no further modification could be made.')
            #break

            # Or, reset the list of items to be modified and continue instead of
            # break.

            # Reset lists of elements that have been modified already.
            positions_attempted_to_remove = [] 
            seqs_attempted_to_remove = []
            seqs_attempted_to_add = []

            # Apply changes to previous alignment/tree info tuple.
            previous_ali_tree_tuple = (iteration + 1,
                                       previous_ali_tree_tuple[1],
                                       previous_ali_tree_tuple[2],
                                       positions_attempted_to_remove,
                                       previous_ali_tree_tuple[4],
                                       previous_ali_tree_tuple[5],
                                       previous_ali_tree_tuple[6],
                                       previous_ali_tree_tuple[7],
                                       seqs_attempted_to_remove,
                                       seqs_attempted_to_add,
                                       previous_ali_tree_tuple[10],
                                       False,
                                       previous_ali_tree_tuple[12],
                                       previous_ali_tree_tuple[13]
                                       )

            # If in the 'intensive' mode, then switch to the next stage of
            # analysis.
            if intensive_mod_type:
                # Add iteration number for current best iteration to the list
                # of those whos corresponding output files should be kept for
                # future reference.
                alignment_nums_to_keep.append(best_alignment_num)

                # Change the mod_type to the next stage.
                mod_type = next(mod_type_intensive_iterable)
                print("""\nSwitching to modification type: %s""" % mod_type)

                # If the mod_type is 'remove_seqs' then it should just keep
                # going until there are no more sequences to try removing.

                # If the mod_type is not 'Stop', then stop the analysis at the
                # current best tree.
                if mod_type == 'Stop':
                    print("""\nReached the end of the intensive dataset
                    searching strategy.""")
                    break

            # Go to the next iteration so that nothing else is done before
            # trying another modification.
            continue

        # Get measures of support for both trees (lowest value among abayes and
        # alrt supports for all branches for specific clades of interest as
        # well as branches that are internal to those branches).
        # Contents of tuple returned by the get_y_measure_of_support function
        # (X_tree_measure variables):
        # 1. lowest_support_value,
        # 2. average_support_value,
        # 3. minimum_stem_branch_ratio,
        # 4. average_stem_branch_ratio,
        # 5. min_dbranch_avgleaf_ratio,
        # 6. avg_dbranch_avgleaf_ratio,
        # 7. modified_clade_stem_branch_ratio
        prev_tree_measure = get_y_measure_of_support(previous_ali_tree_tuple,
                True, modified_clade_name)
        new_tree_measure = get_y_measure_of_support(new_ali_tree_tuple, True)

        # Decide whether to use new alignment/tree based on various criteria.
        print('\t\tComparing measures of branch support in new tree to those of the previous tree...')
        print('\t\t\tOld tree support measure: ' + str(prev_tree_measure))
        print('\t\t\tNew tree support measure: ' + str(new_tree_measure))
        # The measures of support are support values (such as probabilities
        # from alrt branch tests), so better trees have higher values.

        # Apply criteria based on comparing values between trees to determine
        # whether the new tree is better.
        new_tree_is_better = new_tree_better(prev_tree_measure,
                                             new_tree_measure,
                                             mod_type, 
                                             intensive_mod_type)

        if new_tree_is_better:
            # Set best tree to this tree.
            print('\t\t\tNew tree is better.')
            previous_ali_tree_tuple = new_ali_tree_tuple
            best_alignment_num = str(iteration + 1)

        else:
            # If a sequence was added, then make sure that it is not essential
            # before discarding the new alignment.
            new_seq_is_essential = new_ali_tree_tuple[12]
            if new_seq_is_essential:
                print('\t\t\tNew tree has an additional essential sequence in a clade of interest.')

                previous_ali_tree_tuple = new_ali_tree_tuple

                # Reset variable that stores True if the added sequence is
                # essential.
                new_ali_tree_tuple[12] = False

                # Set best tree to this tree.
                best_alignment_num = str(iteration + 1)


            else:
                print('\t\t\tOld tree is better.')
                failed_iterations_tally += 1
                # Just update the lists of modifications that have already been
                # attempted.
                previous_ali_tree_tuple = (iteration + 1,
                                           previous_ali_tree_tuple[1],
                                           previous_ali_tree_tuple[2],
                                           new_ali_tree_tuple[3],
                                           previous_ali_tree_tuple[4],
                                           previous_ali_tree_tuple[5],
                                           previous_ali_tree_tuple[6],
                                           previous_ali_tree_tuple[7],
                                           new_ali_tree_tuple[8],
                                           new_ali_tree_tuple[9],
                                           previous_ali_tree_tuple[10],
                                           new_ali_tree_tuple[11],
                                           previous_ali_tree_tuple[12],
                                           previous_ali_tree_tuple[13]
                                           )


        # Break the loop if the max number of failed iterations have occured.
        max_failed_iterations = max_failed_iterations_dict[mod_type]
        if failed_iterations_tally >= max_failed_iterations:
            # Don't stop if the intensive option was selected. 
            if intensive_mod_type:
                continue
            # Switch to a different modification type if the mod_type was
            # mixed.
            elif mixed_mod_type:
                # Define the new modification type.
                mod_type = next(mod_type_mix_iterable)
                # Reset tally of failed iterations.
                failed_iterations_tally = 0

            # Otherwise stop further modification of the alignment.
            else:
                print("""\nReached maximum number of failed iterations (modifications that
                do not result in a tree with better support).""")
                break

    # Report which alignment is the best.
    if best_alignment_num == '0':
        print('\nBest alignment is the original input alignment')
    else:
        print('\nBest alignment is alignment ' + best_alignment_num)

    # Remove all output files, except those for the best alignment.
    if not keep_all_output:
        # Get list of "names" that should be in files to keep.
        alignment_to_keep_names = []
        for i in ['0'] + alignment_nums_to_keep + [best_alignment_num]:
            alignment_to_keep_names.append(\
                os.path.basename(new_ali_path).rsplit('_', 1)[0] + '_' + i)
        # Remove all output files and directories that do not have one of the
        # listed names.
        for output in glob.glob(new_ali_path.rsplit('_', 1)[0] + '*'):
            output_matches_an_alignment_to_keep = False
            for i in alignment_to_keep_names:
                if i in output:
                    output_matches_an_alignment_to_keep = True
                    break
            if not output_matches_an_alignment_to_keep:
                if os.path.isdir(output):
                    shutil.rmtree(output)
                else:
                    os.remove(output)


    # Return path to main/final output file or directory.
    return outputdir



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
"""Tests functions in module_amoebae_srchresfile using unittest.
"""

# Import necessary modules.
import unittest
import module_amoebae_srchresfile
from module_amoebae_srchresfile import SrchResFile

import sys
import os

#command_line_list = sys.argv
##blastpfp = str(command_line_list[1])
##hmmsearchfp = str(command_line_list[1])
#
#num = 0
#for i in command_line_list[1:]:
#    num += 1
#    hit_rank = 0
#    print('\nSearch file ' + str(num))
#    parsed_file_obj = SrchResFile(i)
#    print(os.path.basename(parsed_file_obj.filepath))
#    print('program')
#    print(parsed_file_obj.program)
#    print('version')
#    print(parsed_file_obj.version)
#    print('hit rank')
#    print(hit_rank)
#    print('hit id')
#    print(parsed_file_obj.hit_id(hit_rank))
#    print('hit descr')
#    print(parsed_file_obj.hit_description(hit_rank))
#    print('hit evalue')
#    print(str(parsed_file_obj.hit_evalue(hit_rank)))
#    print('hit score')
#    print(str(parsed_file_obj.hit_score(hit_rank)))
#    #print('hit seq')
#    #print(str(parsed_file_obj.hit_sequence(0).seq))
#    print('hit subseq description')
#    print(str(parsed_file_obj.hit_subsequence_and_coord(0)[0].description))
#    print('hit subseq')
#    print(str(parsed_file_obj.hit_subsequence_and_coord(0)[0].seq))
#    print('hit subseq coord')
#    print(str(parsed_file_obj.hit_subsequence_and_coord(0)[1]))

# query length?
# fwd_hit_score?
# query length?




# Define a class with functions for performing tests.
#class Testmodule_amoebae_srchresfile(unittest.TestCase):
#
#    def test_a_function(self):
#
#        input = 'x'
#        result = 'value'
#
#        self.assertEqual(module_amoebae_srchresfile.a_function(input), result)


#if __name__ == '__main__':
#    unittest.main()
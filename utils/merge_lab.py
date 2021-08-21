#! /usr/bin/python

import argparse
import sys
from tqdm import tqdm
from os.path import basename, expanduser, join, splitext
import utaupy as up
import csv
from nnmnkwii.io import hts
    
def get_parser():
    parser = argparse.ArgumentParser(
        description="Merge labs",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("offset_file_path", type=str, help="offset_file_path")
    parser.add_argument("input_dir", type=str, help="Input directory path")
    parser.add_argument("output_dir", type=str, help="Output directory path")

    return parser


args = get_parser().parse_args(sys.argv[1:])
#print(args)
offset_file_path = expanduser(args.offset_file_path)
input_dir = expanduser(args.input_dir)
output_dir = expanduser(args.output_dir)

offset_list = []
with open(offset_file_path, "r", encoding="UTF-8") as csvfile:
    csvreader = csv.reader(csvfile, delimiter=',')
    offset_list =   [row for row in csvreader]

#print(offset_list)

orig_name_list = list(dict.fromkeys([x[0] for x in offset_list]))

for name in orig_name_list:
    offset_list_by_name = sorted([x for x in offset_list if x[0] == name], key=lambda x: int(x[2]))
    print(offset_list_by_name)
#    offset_list_by_name = sorted([x for x in offset_list if x[0] == name])
    
    merged_lab = hts.HTSLabelFile()
    for idx, lab_file_name in enumerate([x[1] for x in offset_list_by_name]):
        lab_file_path = join(input_dir, f"{lab_file_name}.lab" )
        lab = hts.load(lab_file_path)
        offset = int(offset_list_by_name[idx][2])
#        print(lab_file_name)
        if len(merged_lab) > 1:
            if merged_lab.contexts[-1] == lab.contexts[0]:
                merged_lab.end_times[-2] = lab.start_times[0] + offset
                merged_lab.start_times[-1] = merged_lab.end_times[-2]
                merged_lab.end_times[-1] = lab.end_times[0] +  offset
            else:
                merged_lab.end_times[-1] = lab.start_times[0] + offset
                merged_lab.append((lab.start_times[0]+offset, lab.end_times[0]+offset, lab.contexts[0]), True)
        else:
            merged_lab.append((lab.start_times[0]+offset, lab.end_times[0]+offset, lab.contexts[0]), True)
        for idx in range(1, len(lab)):
            merged_lab.append((lab.start_times[idx]+offset, lab.end_times[idx]+offset, lab.contexts[idx]), True)
#        print(merged_lab)
             
    with open(join(output_dir, f"{name}.lab"), "w") as of:
        of.write(str(merged_lab))
            
                       

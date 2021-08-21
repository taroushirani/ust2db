#! /usr/bin/python

import argparse
import sys
from glob import glob
from tqdm import tqdm
from os.path import basename, expanduser, join, splitext
from nnmnkwii.io import hts
import csv

def get_parser():
    parser = argparse.ArgumentParser(
        description="Convert monophone label to audacity label",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("input_dir", type=str, help="Input directory path")
    parser.add_argument("output_path", type=str, help="Output file path")    
    return parser


args = get_parser().parse_args(sys.argv[1:])
#print(args)
input_dir = expanduser(args.input_dir)
output_path = expanduser(args.output_path)

lab_path_list =  glob(join(expanduser(input_dir), "**/*.lab"), recursive=True)

with open(output_path, "w", newline='\n', encoding="UTF-8") as csvfile:
    csv_writer = csv.writer(csvfile, delimiter=',', lineterminator="\n")
    for lab_path in tqdm(lab_path_list):
        name = splitext(basename(lab_path))[0]
        lab = hts.load(lab_path)
        csv_writer.writerow([name, " ".join(lab.contexts)])

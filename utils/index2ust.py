#! /usr/bin/python

import argparse
import sys
from tqdm import tqdm
from os.path import basename, expanduser, join, splitext
import utaupy as up
import csv

    
def get_parser():
    parser = argparse.ArgumentParser(
        description="Convert index file to ust(s)",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("index_path", type=str, help="Index file path")
    parser.add_argument("output_dir", type=str, help="Output directory path")

    return parser


args = get_parser().parse_args(sys.argv[1:])
#print(args)
index_path = expanduser(args.index_path)
output_dir = expanduser(args.output_dir)

with open(index_path, "r", encoding="UTF-8") as csvfile:
    csvreader = csv.reader(csvfile, delimiter=',')
    for row in csvreader:
#        print(row)
        output_path = join(output_dir, row[0] + ".ust")
        

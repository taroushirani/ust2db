#! /usr/bin/python

import argparse
import sys
from glob import glob
from tqdm import tqdm
from os.path import basename, expanduser, join, splitext
from utaupy.utils import ust2hts

import re

def guess_notenum_from_filename(name):
    ret = re.search(r"[a-zA-Z]#*[0-9]", name)
    if ret is None:
        raise ValueError(f"Can't guess notenum from name: {name}")
    return ret[0]
    
    
def get_parser():
    parser = argparse.ArgumentParser(
        description="Convert index file to ust(s)",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("input_dir", type=str, help="Input directory path")
    parser.add_argument("output_dir", type=str, help="Output directory path")
    parser.add_argument("table_path", type=str, help="Table file path")
    parser.add_argument("--as_mono", action="store_true", help="Output monophone label")
    return parser


args = get_parser().parse_args(sys.argv[1:])
#print(args)
input_dir = expanduser(args.input_dir)
output_dir = expanduser(args.output_dir)
table_path = expanduser(args.table_path)
as_mono = args.as_mono

ust_path_list =  glob(join(expanduser(input_dir), "**/*.ust"), recursive=True)

for ust_path in tqdm(ust_path_list):
    name = splitext(basename(ust_path))[0]
#    print(name)
    output_path = join(output_dir, name + ".lab")
    ust2hts(ust_path, output_path, table_path, strict_sinsy_style=False, as_mono=as_mono)    

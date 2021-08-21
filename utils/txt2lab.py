#! /usr/bin/python

import argparse
import sys
from glob import glob
from tqdm import tqdm
from os.path import basename, expanduser, join
from nnmnkwii.io import hts
    
def get_parser():
    parser = argparse.ArgumentParser(
        description="Convert txt to lab",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("input_dir", type=str, help="Input directory path")
    parser.add_argument("output_dir", type=str, help="Output directory path")    
    parser.add_argument("--frame_period", type=int, default=5, help="Frame Period (default 5ms)")
    parser.add_argument("--rounding", action="store_true", help="Use rounding")
    
    return parser


args = get_parser().parse_args(sys.argv[1:])
#print(args)
input_dir = expanduser(args.input_dir)
output_dir = expanduser(args.output_dir)
frame_period = args.frame_period
rounding = args.rounding

txt_path_list =  glob(join(expanduser(input_dir), "**/*.txt"), recursive=True)

for txt_path in tqdm(txt_path_list):
    with open(txt_path, "r", encoding="UTF-8") as in_f:
        h = hts.HTSLabelFile()
        for l in in_f:
            s,e,l = l.strip().split()
            if rounding:
                s,e = round(float(s) * 1e7 / (frame_period * 10000)) * (frame_period * 10000), round(float(e) * 1e7 / (frame_period * 10000)) * (frame_period * 10000)
            else:
                s,e = int(float(s) * 1e7), int(float(e) * 1e7)
                
            h.append((s,e,l))

        output_path = join(output_dir, basename(txt_path).replace("txt", "lab"))
        with open(output_path, "w", newline='\n', encoding="UTF-8") as out_f:
            out_f.write(str(h))

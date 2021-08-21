#! /usr/bin/python

import argparse
import sys
from glob import glob
from tqdm import tqdm
from os.path import basename, expanduser, join, splitext
from nnmnkwii.io import hts

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
    parser.add_argument("mono_dir", type=str, help="Directory path of monophone label files.")
    parser.add_argument("full_dir", type=str, help="Direcotry path of HTS full-context label files")
    parser.add_argument("output_dir", type=str, help="Output directory path")
    return parser


args = get_parser().parse_args(sys.argv[1:])
#print(args)
mono_dir = expanduser(args.mono_dir)
full_dir = expanduser(args.full_dir)
output_dir = expanduser(args.output_dir)

mono_lab_path_list =  glob(join(expanduser(mono_dir), "*.lab"))

for mono_lab_path in tqdm(mono_lab_path_list):
    name = splitext(basename(mono_lab_path))[0]
#    print(name)
    full_lab_path = join(full_dir, name + ".lab")

    mono_lab = hts.load(mono_lab_path)
    full_lab = hts.load(full_lab_path)
    assert(len(mono_lab)==len(full_lab))

    # copy label times from mono to full
    full_lab.start_times = mono_lab.start_times
    full_lab.end_times = mono_lab.end_times
    
    output_path = join(output_dir, name + ".lab")
    with open(output_path, "w", encoding="UTF-8") as of:
        of.write(str(full_lab))

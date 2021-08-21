#! /usr/bin/python

import argparse
import sys
from glob import glob
from tqdm import tqdm
from os.path import basename, expanduser, join, splitext
from nnmnkwii.io import hts
import utaupy as up
from utaupy.ust import NOTENAME_TO_NOTENUM_DICT
import re

def guess_notenum_from_filename(name):
    ret = re.search(r"[a-zA-Z]#*[0-9]", name)
    if ret is None:
        raise ValueError(f"Can't guess notenum from name: {name}")
    notenum = NOTENAME_TO_NOTENUM_DICT[ret[0]]
    return notenum
    
def get_parser():
    parser = argparse.ArgumentParser(
        description="Convert index file to ust(s)",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("input_dir", type=str, help="Input directory path")
    parser.add_argument("output_dir", type=str, help="Output directory path")
    parser.add_argument("--tempo", type=int, default=100, help="Tempo (default 100)")
    return parser


args = get_parser().parse_args(sys.argv[1:])
#print(args)
input_dir = expanduser(args.input_dir)
output_dir = expanduser(args.output_dir)
tempo = args.tempo

lab_path_list =  glob(join(expanduser(input_dir), "**/*.lab"), recursive=True)
#print(lab_path_list)

for lab_path in tqdm(lab_path_list):
    name = splitext(basename(lab_path))[0]
#    print(name)
    notenum = guess_notenum_from_filename(name)
    output_path = join(output_dir, name + ".ust")
    lab = hts.load(lab_path)
#    print(lab)

    ust = up.ust.Ust()
    ust.version = 1.20
    for i in range(len(lab)):
        note = up.ust.Note()
        note.lyric=lab.contexts[i]
        note.tempo = tempo
        note.notenum = notenum
        duration_ms = (lab.end_times[i] - lab.start_times[i]) / 10000
        note.length = round(duration_ms * tempo / 125)
        ust.notes.append(note)
    ust.write(output_path)

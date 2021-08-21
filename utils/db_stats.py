# coding: utf-8

from glob import glob
from os.path import join, basename, expanduser, splitext
from tqdm import tqdm
from nnmnkwii.io import hts
import argparse
import pandas as pd

parser = argparse.ArgumentParser(description='Report DB statistics')
parser.add_argument('--monolab-dir', metavar='monolab_dir', type=str, default="./data/mono", help='monophone label directory')

args = parser.parse_args()

monolab_dir = args.monolab_dir
items = ["name", "silent", "non_silent"]
df = pd.DataFrame( columns=items )

lab_path_list =  glob(join(expanduser(monolab_dir), "**/*.lab"), recursive=True)
for lab_path in tqdm(lab_path_list):
    name = splitext(basename(lab_path))[0]
    lab = hts.load(lab_path)
    silent_length = 0
    non_silent_length = 0
    for i in range(len(lab)):
        if lab.contexts[i] in ["pau", "sil", "cl"]:
            silent_length += (lab.end_times[i] - lab.start_times[i]) * 1e-7
        else:
            non_silent_length += (lab.end_times[i] - lab.start_times[i]) * 1e-7
    _df = pd.DataFrame([[name, silent_length, non_silent_length]], columns=items)
    df = pd.concat([df, _df])

total_file_num = df["name"].count()
total_silent_length = df["silent"].sum(axis=0)
total_non_silent_length = df["non_silent"].sum(axis=0)

print("Overall summary")
print(f"\ttotal file num: {total_file_num}")
print(f"\ttotal silent length: {total_silent_length:.2f}")
print(f"\ttotal non_silent length: {total_non_silent_length:.2f}")

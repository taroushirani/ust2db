#! /usr/bin/python

import argparse
import sys
from glob import glob
from tqdm import tqdm
from os.path import basename, expanduser, join, splitext
import utaupy as up
import re
import csv


def get_phonemes_from_wavname(name: str, table: dict) -> list:

    is_nodogirion = False
    if name[-1] is "・":
        is_nodogirion = True
        
#    print(f"table: {table}")
    sorted_table = sorted(list(table.keys()), key=lambda x:len(x), reverse=True)
#    print(f"sourted_table: {sorted_table}")
    regex=re.compile("(" + "|".join(sorted_table)+ "|[a-zA-Z0-9_]+)")
    # _あfふぁvヴぁ -> ['', '_', '', 'あ', '', 'f', '', 'ふぁ', '', 'v', '', 'ヴぁ', '']
    sy_list_ = re.split(regex, name)
#    print(f"ret: {ret}")
    # Remove empty item
    sy_list = list(filter(None, sy_list_))

    ph_list = []
    for sy in sy_list:
        try:
            phs = table[sy]
            for ph in phs:
                ph_list.append(ph)
            if is_nodogirion is True:
                print(f"is_nodogirion is true")
                ph_list.append("pau")
        except KeyError:
            if re.match("[a-zA-Z]+", sy):
                ph_list.append(sy)
                ph_list.append("pau")
            else:
                raise ValueError(f"{name}: No entry of sy {sy}")

    if ph_list[-1] != "pau":
        ph_list.append("pau")
            
    return ph_list

    
def get_parser():
    parser = argparse.ArgumentParser(
        description="Convert wav filename to phoneme list",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("data_dir", type=str, help="Data directory")
    parser.add_argument("table_path", type=str, help="Table file path")
    parser.add_argument("output_path", type=str, help="Output file path")
    return parser


args = get_parser().parse_args(sys.argv[1:])
#print(args)
data_dir = expanduser(args.data_dir)
table_path= expanduser(args.table_path)
output_path = expanduser(args.output_path)

table = up.table.load(table_path)

wav_path_list =  glob(join(expanduser(data_dir), "**/*.wav"), recursive=True)

with open(output_path, "w", newline='\n', encoding="UTF-8") as csvfile:
    csv_writer = csv.writer(csvfile, delimiter=',', lineterminator="\n")
    for wav_path in tqdm(wav_path_list):
        wav_name = basename(wav_path).replace(".wav", "")
        try:
            phoneme_list = get_phonemes_from_wavname(splitext(wav_name)[0], table)
        except ValueError as e:
            print(e)
            print(f"Can't get lyrics from {wav_path} so skipping")
            continue
        # print(f"wav_name: {wav_name}, phoneme_list: {phoneme_list}")
        csv_writer.writerow([wav_name, " ".join(phoneme_list)])




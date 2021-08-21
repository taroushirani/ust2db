#! /usr/bin/py

import sys
from os import makedirs
from os.path import abspath, basename, dirname, expanduser, join, splitext
from glob import glob
from tqdm import tqdm
import yaml
import shutil

config = None
with open(sys.argv[1], 'r') as yml:
    config = yaml.load(yml, Loader=yaml.FullLoader)
if config is None:
    print(f"Cannot read config file: {sys.argv[1]}.")
    sys.exit(-1)


print("Copy wav file")
files = glob(join(expanduser(config["db_root"]), "**/*.wav"), recursive=True)
dest_dir = join(config["out_dir"], "wav")
makedirs(dest_dir, exist_ok=True)
for path in tqdm(files):
    name = basename(path)
    if splitext(name)[0] in config["exclude_data_name"]:
        continue
    notename = basename(abspath(dirname(path)))
    if notename in config["exclude_data_dir"]:
        continue
    out_path = join(dest_dir, splitext(name)[0] + "." + notename + ".wav")
    shutil.copyfile(path, out_path)

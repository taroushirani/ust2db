#! /usr/bin/py

import sys
from os import makedirs
from os.path import abspath, basename, dirname, expanduser, join, splitext
from glob import glob
from tqdm import tqdm
import yaml
import shutil
import re
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
fn_re = re.compile("(_.*)_([A-Z][0-9])(_[0-9])*")

for path in tqdm(files):
    name = basename(path)
    if splitext(name)[0] in config["exclude_data_name"]:
        continue
    if basename(abspath(dirname(path))) in config["exclude_data_dir"]:
        continue

    ret = re.match(fn_re, name)
    syllables = ret.group(1)
    notename = ret.group(2)
#    print(notename)
    if syllables is None or notename is None:
        raise ValueError("Can't get syllables and notename")
    out_path = join(dest_dir, syllables + "." + notename + ".wav")
    shutil.copyfile(path, out_path)

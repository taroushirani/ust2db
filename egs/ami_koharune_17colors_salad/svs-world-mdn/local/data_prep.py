# coding: utf-8
import os

import argparse
from glob import glob
from os.path import join, basename, splitext, exists, expanduser
from nnmnkwii.io import hts
from scipy.io import wavfile
import librosa
import soundfile as sf
import sys
import numpy as np

from nnsvs.io.hts import get_note_indices
import yaml

def _is_silence(l):
    is_full_context = "@" in l
    if is_full_context:
        is_silence = ("-sil" in l or "-pau" in l)
    else:
        is_silence = (l == "sil" or l == "pau")
    return is_silence


def remove_sil_and_pau(lab):
    newlab = hts.HTSLabelFile()
    for l in lab:
        if "-sil" not in l[-1] and "-pau" not in l[-1]:
            newlab.append(l, strict=False)

    return newlab


def get_parser():
    parser = argparse.ArgumentParser(
        description="Data preparation scripts for genon2db",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("config_path", type=str, help="Config file path")
    return parser

args = get_parser().parse_args(sys.argv[1:])

config_path = args.config_path
config = None
with open(config_path, 'r') as yml:
    config = yaml.load(yml, Loader=yaml.FullLoader)
if config is None:
    print(f"Cannot read config file: {config_path}.")
    sys.exit(-1)

full_dir = join(config["out_dir"], "full")

### Prepare data for time-lag models
# Note: genon2db is to be expected to output fully-aligned labels
full_align_dir = full_dir

dst_dir = join(config["out_dir"], "timelag")
lab_align_dst_dir  = join(dst_dir, "label_phone_align")
lab_score_dst_dir  = join(dst_dir, "label_phone_score")

for d in [lab_align_dst_dir, lab_score_dst_dir]:
    os.makedirs(d, exist_ok=True)

print("Prepare data for time-lag models")
full_lab_align_files = sorted(glob(join(full_align_dir, "*.lab")))
for lab_align_path in full_lab_align_files:
    lab_score_path = join(full_dir, basename(lab_align_path))
    assert exists(lab_score_path)
    name = basename(lab_align_path)

    lab_align = hts.load(lab_align_path)
    lab_score = hts.load(lab_score_path)

    # Extract note onsets and let's compute a offset
    note_indices = get_note_indices(lab_score)

    onset_align = np.asarray(lab_align[note_indices].start_times)
    onset_score = np.asarray(lab_score[note_indices].start_times)

    global_offset = (onset_align - onset_score).mean()
    global_offset = int(round(global_offset / 50000) * 50000)

    # Apply offset correction only when there is a big gap
    apply_offset_correction = np.abs(global_offset * 1e-7) > config["offset_correction_threshold"]
    if apply_offset_correction:
        print(f"{name}: Global offset (in sec): {global_offset * 1e-7}")
        lab_score.start_times = list(np.asarray(lab_score.start_times) + global_offset)
        lab_score.end_times = list(np.asarray(lab_score.end_times) + global_offset)
        onset_score += global_offset

    # Exclude large diff parts (probably a bug of musicxml or alignment though)
    valid_note_indices = []
    for idx, (a, b) in enumerate(zip(onset_align, onset_score)):
        note_idx = note_indices[idx]
        lag = np.abs(a - b) / 50000
        if _is_silence(lab_score.contexts[note_idx]):
            if lag >= config["timelag_allowed_range_rest"][0] and lag <= config["timelag_allowed_range_rest"][1]:
                valid_note_indices.append(note_idx)
        else:
            if lag >= config["timelag_allowed_range"][0] and lag <= config["timelag_allowed_range"][1]:
                valid_note_indices.append(note_idx)

    if len(valid_note_indices) < len(note_indices):
        D = len(note_indices) - len(valid_note_indices)
        print(f"{name}: {D}/{len(note_indices)} time-lags are excluded.")

    # Note onsets as labels
    lab_align = lab_align[valid_note_indices]
    lab_score = lab_score[valid_note_indices]

    # Save lab files
    lab_align_dst_path = join(lab_align_dst_dir, name)
    with open(lab_align_dst_path, "w") as of:
        of.write(str(lab_align))

    lab_score_dst_path = join(lab_score_dst_dir, name)
    with open(lab_score_dst_path, "w") as of:
        of.write(str(lab_score))

### Prepare data for duration models

dst_dir = join(config["out_dir"], "duration")
lab_align_dst_dir  = join(dst_dir, "label_phone_align")

for d in [lab_align_dst_dir]:
    os.makedirs(d, exist_ok=True)

print("Prepare data for duration models")
full_lab_align_files = sorted(glob(join(full_align_dir, "*.lab")))
for lab_align_path in full_lab_align_files:
    name = basename(lab_align_path)

    lab_align = hts.load(lab_align_path)

    # Save lab file
    lab_align_dst_path = join(lab_align_dst_dir, name)
    with open(lab_align_dst_path, "w") as of:
        of.write(str(lab_align))


### Prepare data for acoustic models

dst_dir = join(config["out_dir"], "acoustic")
wav_dst_dir  = join(dst_dir, "wav")
lab_align_dst_dir  = join(dst_dir, "label_phone_align")
lab_score_dst_dir  = join(dst_dir, "label_phone_score")

for d in [wav_dst_dir, lab_align_dst_dir, lab_score_dst_dir]:
    os.makedirs(d, exist_ok=True)

print("Prepare data for acoustic models")
full_lab_align_files = sorted(glob(join(full_align_dir, "*.lab")))
for lab_align_path in full_lab_align_files:
    name = splitext(basename(lab_align_path))[0]
    lab_score_path = join(full_dir, name + ".lab")
    assert exists(lab_score_path)
    wav_path = join(config["out_dir"], "wav", name + ".wav")

    # sr, wave = wavfile.read(wav_path)
    wav, sr = librosa.load(wav_path, sr=config["sample_rate"])

    if config["gain_normalize"]:
        print("gain_normalize enabled")
        wav = wav / wav.max() * 0.99

    lab_align = hts.load(lab_align_path)
    lab_score = hts.load(lab_score_path)

    # Save caudio
    wav_dst_path = join(wav_dst_dir, name + ".wav")
    # TODO: consider explicit subtype
    sf.write(wav_dst_path, wav, sr)

    # Save label
    lab_align_dst_path = join(lab_align_dst_dir, name + ".lab")
    with open(lab_align_dst_path, "w") as of:
        of.write(str(lab_align))

    lab_score_dst_path = join(lab_score_dst_dir, name + ".lab")
    with open(lab_score_dst_path, "w") as of:
        of.write(str(lab_score))

sys.exit(0)

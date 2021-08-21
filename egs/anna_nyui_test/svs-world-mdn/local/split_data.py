#! /usr/bin/python

import argparse
import sys
from glob import glob
from tqdm import tqdm
from os.path import basename, exists, expanduser, join, splitext
from nnmnkwii.io import hts
import numpy as np
import librosa
import soundfile as sf
import csv

# from nnsvs/egs/_common/no2/utils/util.py
def _is_silence(l):
    is_full_context = "@" in l
    if is_full_context:
        is_silence = ("-sil" in l or "-pau" in l)
    else:
        is_silence = (l == "sil" or l == "pau")
    return is_silence

# from nnsvs/egs/_common/no2/utils/util.py
def trim_long_sil_and_pau(lab, return_indices=False, threshold=10.0):
    forward = 0
    while True:
        d  = (lab.end_times[forward] - lab.start_times[forward]) * 1e-7
        if _is_silence(lab.contexts[forward]) and d > threshold:
            forward += 1
        else:
            break

    backward = len(lab) - 1
    while True:
        d  = (lab.end_times[backward] - lab.start_times[backward]) * 1e-7
        if _is_silence(lab.contexts[backward]) and d > threshold:
            backward -= 1
        else:
            break

    if return_indices:
        return lab[forward:backward+1], forward, backward
    else:
        return lab[forward:backward+1]

# from nnsvs/egs/_common/no2/utils/util.py
def compute_nosil_duration(lab, threshold=5.0):
    is_full_context = "@" in lab[0][-1]
    sum_d = 0
    for s,e,l in lab:
        d = (e - s) * 1e-7
        if is_full_context:
            is_silence = ("-sil" in l or "-pau" in l)
        else:
            is_silence = (l == "sil" or l == "pau")
        if is_silence and d > threshold:
            pass
        else:
            sum_d += d
    return sum_d

# from nnsvs/egs/_common/no2/utils/util.py
def fix_offset(lab):
    offset = lab.start_times[0]
    lab.start_times = np.asarray(lab.start_times) - offset
    lab.end_times = np.asarray(lab.end_times) - offset
    return lab

# from nnsvs/egs/_common/no2/utils/util.py
def segment_labels(lab, strict=True, threshold=1.0, min_duration=5.0,
        force_split_threshold=10.0):
    """Segment labels based on sil/pau

    Example:

    [a b c sil d e f pau g h i sil j k l]
    ->
    [a b c] [d e f] [g h i] [j k l]

    """
    segments = []
    seg = hts.HTSLabelFile()
    start_indices = []
    end_indices = []
    si = 0
    large_silence_detected = False

    for idx, (s, e, l) in enumerate(lab):
        d = (e-s) * 1e-7
        is_silence = _is_silence(l)

        if len(seg) > 0:
            # Compute duration except for long silences
            seg_d = compute_nosil_duration(seg)
        else:
            seg_d = 0

        # let's try to split
        # if we find large silence, force split regardless min_duration
        if (d > force_split_threshold) or (is_silence and d > threshold and seg_d > min_duration):
            if idx == len(lab)-1:
                # append last pau
                seg.append((s, e, l), strict)
                continue
            elif len(seg) > 0:
                if d > force_split_threshold:
                    large_silence_detected = True
                else:
                    large_silence_detected = False
                start_indices.append(si)
                si = 0
#                end_indices.append(idx - 1)
                end_indices.append(idx)
                segments.append(seg)
                seg = hts.HTSLabelFile()
                si = idx
                seg.append((s, e, l), strict)
            continue
        else:
            if len(seg) == 0:
                si = idx
            seg.append((s, e, l), strict)

    if len(seg) > 0:
        seg_d = compute_nosil_duration(seg)
        # If the last segment is short, combine with the previous segment.
        if seg_d < min_duration and not large_silence_detected:
            end_indices[-1] = si + len(seg) - 1
        else:
            start_indices.append(si)
            end_indices.append(si + len(seg) - 1)

    #  Trim large sil for each segment
    segments2 = []
    start_indices_new, end_indices_new = [], []
    for s, e in zip(start_indices, end_indices):
        seg = lab[s:e+1]

        # ignore "sil" or "pau" only segment
        if len(seg) ==1 and _is_silence(seg.contexts[0]):
            continue
        seg2, forward, backward = trim_long_sil_and_pau(seg, return_indices=True)

        start_indices_new.append(s+forward)
        end_indices_new.append(s+backward)
#        end_indices_new.append(e+backward)

        segments2.append(seg2)

    return segments2, start_indices_new, end_indices_new

def get_parser():
    parser = argparse.ArgumentParser(
        description="",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("mono_lab_in_dir", type=str, help="Input mono label directory path")
    parser.add_argument("full_lab_in_dir", type=str, help="Input full label directory path")
    parser.add_argument("wav_in_dir", type=str, help="Input wav directory path")    
    parser.add_argument("mono_lab_out_dir", type=str, help="Output segmentated mono label directory path")
    parser.add_argument("full_lab_out_dir", type=str, help="Output segmentated full label directory path")
    parser.add_argument("wav_out_dir", type=str, help="Output wav directory path")
    parser.add_argument("offset_file_path", type=str, help="Offset file path")
    parser.add_argument("--segmentation_threshold", type=float, default=0.4, help="Split song by silences (in sec)")
    parser.add_argument("--segment_min_duration", type=float, default=5.0, help="Min duration for a segment(in sec)")
    parser.add_argument("--force_split_threshold", type=float, default=5.0, help="Force split segments if long silence is found regardless of min_duration (in sec)")
    parser.add_argument("--sample_rate", type=int, default=48000, help="Audio sample rate")
    parser.add_argument("--suppress_start_end_pau", action="store_true", help="Suppress Start&End pau")
    parser.add_argument("--start_end_pau_suppression_ratio", type=float, default=0.2, help="Start&End pau suppression ratio")
    return parser

args = get_parser().parse_args(sys.argv[1:])
#print(args)
mono_lab_in_dir = expanduser(args.mono_lab_in_dir)
full_lab_in_dir = expanduser(args.full_lab_in_dir)
wav_in_dir = expanduser(args.wav_in_dir)
mono_lab_out_dir = expanduser(args.mono_lab_out_dir)
full_lab_out_dir = expanduser(args.full_lab_out_dir)
wav_out_dir = expanduser(args.wav_out_dir)
offset_file_path=expanduser(args.offset_file_path)
segmentation_threshold = args.segmentation_threshold
segment_min_duration = args.segment_min_duration
force_split_threshold = args.force_split_threshold
sample_rate = args.sample_rate
suppress_start_end_pau = args.suppress_start_end_pau
start_end_pau_suppression_ratio = args.start_end_pau_suppression_ratio


mono_lab_path_list = sorted(glob(join(mono_lab_in_dir, "*.lab")))
offset_list = []
lengths = {}
for mono_lab_path in tqdm(mono_lab_path_list):
    name = splitext(basename(mono_lab_path))[0]
    mono_lab = hts.load(mono_lab_path)
    mono_segments, start_indices, end_indices = segment_labels(mono_lab, False, segmentation_threshold, segment_min_duration , force_split_threshold)

    d = []
    for seg in mono_segments:
        d.append((seg.end_times[-1] - seg.start_times[0]) * 1e-7)
    lengths[name] = d

    full_lab = hts.load(join(full_lab_in_dir, f"{name}.lab"))
    print(name)
    assert len(mono_lab) == len(full_lab)
    
    full_segments = []
    for s,e in zip(start_indices, end_indices):
        full_segments.append(full_lab[s:e+1])
    wav_path = join(wav_in_dir, f"{name}.wav")
    assert exists(wav_path)
    wav, sr = librosa.load(wav_path, sr=sample_rate)
    assert sr==sample_rate
    for idx, seg in enumerate(mono_segments):
        b, e = int(seg[0][0] * 1e-7 * sr), int(seg[-1][1] * 1e-7 * sr)
        wav_slice = wav[b:e]
        if suppress_start_end_pau:
            print("Enable start&end pau suppression")
            if seg[0][2] == "pau":
                d = int((seg[0][1] - seg[0][0]) * 1e-7 * start_end_pau_suppression_ratio * sr)
                print(f"First pau of {name}_seg{idx} is suppressed for {(d/sr):2f} sec.")
                wav_slice[0:d] = 0
            if seg[-1][2] == "pau":
                d = int((seg[-1][1] - seg[-1][0]) * 1e-7 *  start_end_pau_suppression_ratio * sr)
                print(f"Last pau of {name}_seg{idx} is suppressed for {(d/sr):2f} sec")
                wav_slice[len(wav_slice)-d:-1] = 0
        wav_slice_path = join(wav_out_dir, f"{name}_seg{idx}.wav")
        sf.write(wav_slice_path, wav_slice, sr)

    for idx, seg in enumerate(mono_segments):
        # Original filename, Segmented file name, offset
        offset_list.append([name, f"{name}_seg{idx}", seg[0][0]])
        
    for idx, seg in enumerate(full_segments):
        with open(join(full_lab_out_dir, f"{name}_seg{idx}.lab"), "w") as of:
            of.write(str(fix_offset(seg)))

    for idx, seg in enumerate(mono_segments):
        with open(join(mono_lab_out_dir, f"{name}_seg{idx}.lab"), "w") as of:
            of.write(str(fix_offset(seg)))

with open(offset_file_path, "w", encoding="UTF-8") as of:
    csv_writer = csv.writer(of, delimiter=',', lineterminator="\n")
    for data in offset_list:
        csv_writer.writerow(data)

for ls in [lengths]:
    for k, v in ls.items():
        print("{}.lab: segment duration min {:.02f}, max {:.02f}, mean {:.02f}".format(
            k, np.min(v), np.max(v), np.mean(v)))

    flatten_lengths = []
    for k, v in ls.items():
        sys.stdout.write(f"{k}.lab: segment lengths: ")
        for d in v:
            sys.stdout.write("{:.02f}, ".format(d))
            flatten_lengths.append(d)
        sys.stdout.write("\n")

    print("Segmentation stats: min {:.02f}, max {:.02f}, mean {:.02f}".format(
        np.min(flatten_lengths), np.max(flatten_lengths), np.mean(flatten_lengths)))

    print("Total number of segments: {}".format(len(flatten_lengths)))

            

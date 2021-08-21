#! /bin/bash

set -e
set -u
set -o pipefail

function xrun () {
    set -x
    $@
    set +x
}

script_dir=$(cd $(dirname ${BASH_SOURCE:-$0}); pwd)
genon2db_root=$script_dir/../

. $genon2db_root/utils/yaml_parser.sh || exit 1;

config_yaml="./config.yaml"
score_dir="./"
checkpoint="best_loss"

. $genon2db_root/utils/parse_options.sh || exit 1;

eval $(parse_yaml $config_yaml "")

# exp name
if [ -z ${tag:=} ]; then
    expname=${spk}
else
    expname=${spk}_${tag}
fi
expdir=exp/$expname
dumpdir=dump
dump_norm_dir=$dumpdir/$spk/norm
ground_truth_duration=false

xrun nnsvs-synthesis question_path=$question_path \
     timelag=defaults \
     duration=defaults \
     acoustic=defaults \
     timelag.checkpoint=$expdir/timelag/${checkpoint}.pth \
     timelag.in_scaler_path=$dump_norm_dir/in_timelag_scaler.joblib \
     timelag.out_scaler_path=$dump_norm_dir/out_timelag_scaler.joblib \
     timelag.model_yaml=$expdir/timelag/model.yaml \
     duration.checkpoint=$expdir/duration/${checkpoint}.pth \
     duration.in_scaler_path=$dump_norm_dir/in_duration_scaler.joblib \
     duration.out_scaler_path=$dump_norm_dir/out_duration_scaler.joblib \
     duration.model_yaml=$expdir/duration/model.yaml \
     acoustic.checkpoint=$expdir/acoustic/${checkpoint}.pth \
     acoustic.in_scaler_path=$dump_norm_dir/in_acoustic_scaler.joblib \
     acoustic.out_scaler_path=$dump_norm_dir/out_acoustic_scaler.joblib \
     acoustic.model_yaml=$expdir/acoustic/model.yaml \
     utt_list=$score_dir/song_list.txt \
     in_dir=$score_dir \
     out_dir=$expdir/synthesis/extra/ \
     ground_truth_duration=$ground_truth_duration

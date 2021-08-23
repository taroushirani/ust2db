#!/bin/bash

# Set bash to 'debug' mode, it will exit on :
# -e 'error', -u 'undefined variable', -o ... 'error in pipeline', -x 'print commands',
set -e
set -u
set -o pipefail

function xrun () {
    set -x
    $@
    set +x
}

script_dir=$(cd $(dirname ${BASH_SOURCE:-$0}); pwd)
genon2db_root=$script_dir/../../../

. $genon2db_root/utils/yaml_parser.sh || exit 1;

eval $(parse_yaml "./config.yaml" "")

NNSVS_COMMON_ROOT=$nnsvs_root/egs/_common/spsvs

train_set="train_no_dev"
dev_set="dev"
eval_set="eval"
datasets=($train_set $dev_set $eval_set)
testsets=($dev_set $eval_set)

dumpdir=dump
dump_org_dir=$dumpdir/$spk/org
dump_norm_dir=$dumpdir/$spk/norm

stage=0
stop_stage=0

. $genon2db_root/utils/parse_options.sh || exit 1;

# exp name
if [ -z ${tag:=} ]; then
    expname=${spk}
else
    expname=${spk}_${tag}
fi
expdir=exp/$expname

if [ ${stage} -le -1 ] && [ ${stop_stage} -ge -1 ]; then
    echo "stage -1: Bootstrapping"
   
    bash ./local/bootstrap.sh --config_yaml config.yaml --stage 0 --stop-stage 3
fi

if [ ${stage} -le 0 ] && [ ${stop_stage} -ge 0 ]; then
    echo "stage 0: Data preparation"
    python ./local/data_prep.py ./config.yaml

    mkdir -p data/list
    echo "train/dev/eval split"
    find data/acoustic/ -type f -name "*.wav" -exec basename {} .wav \; \
        | sort > data/list/utt_list.txt
    grep _きぇきぇきゅきょきぇきょきょ.E4 data/list/utt_list.txt > data/list/$eval_set.list
    grep _きゃきゃききゃきゅきぇきゃ.F4 data/list/utt_list.txt > data/list/$dev_set.list
    grep -v _きぇきぇきゅきょきぇきょきょ.E4 data/list/utt_list.txt | grep -v _きゃきゃききゃきゅきぇきゃ.F4 > data/list/$train_set.list
fi

if [ ${stage} -le 1 ] && [ ${stop_stage} -ge 1 ]; then
    echo "stage 1: Feature generation"
#    export LD_PRELOAD=/usr/lib/x86_64-linux-gnu/libasan.so.5
    . $NNSVS_COMMON_ROOT/feature_generation.sh
fi

if [ ${stage} -le 2 ] && [ ${stop_stage} -ge 2 ]; then
    echo "stage 2: Training time-lag model"
    #    . $NNSVS_COMMON_ROOT/train_timelag.sh
    echo "It makes no sense to train timelag with genon2db-generated data so we merely copy the pretrained model"
    cp -r $pretrained_expdir/timelag $expdir
fi

if [ ${stage} -le 3 ] && [ ${stop_stage} -ge 3 ]; then
    echo "stage 3: Training duration model"
    #    . $NNSVS_COMMON_ROOT/train_duration.sh
    echo "It makes no sense to train duration with genon2db-generated data so we merely copy the pretrained model"
    cp -r $pretrained_expdir/duration $expdir
    
fi

if [ ${stage} -le 4 ] && [ ${stop_stage} -ge 4 ]; then
    echo "stage 4: Training acoustic model"
    . $NNSVS_COMMON_ROOT/train_acoustic.sh
fi

if [ ${stage} -le 5 ] && [ ${stop_stage} -ge 5 ]; then
    echo "stage 5: Generate features from timelag/duration/acoustic models"
    . $NNSVS_COMMON_ROOT/generate.sh
fi

if [ ${stage} -le 6 ] && [ ${stop_stage} -ge 6 ]; then
    echo "stage 6: Synthesis waveforms"
    . $NNSVS_COMMON_ROOT/synthesis.sh
fi

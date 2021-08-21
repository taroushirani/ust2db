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
genon2db_root=$script_dir/../../../../

. $genon2db_root/utils/yaml_parser.sh || exit 1;

stage=-1
stop_stage=-1
config_yaml="./config.yaml"

. $genon2db_root/utils/parse_options.sh || exit 1;

eval $(parse_yaml $config_yaml "")

# exp name
if [ -z ${tag:=} ]; then
    expname=${spk}
else
    expname=${spk}_${tag}
fi
expdir=exp/$expname
shiro_out_dir=$expdir/shiro

if [ ${stage} -le -1 ] && [ ${stop_stage} -ge -1 ]; then
    echo "Usage: bash bootstrap.sh --stage <stage_num> --stop-stage <stop_stage_num>"
    exit 0
fi

if [ ${stage} -le 0 ] && [ ${stop_stage} -ge 0 ]; then
    echo "stage 0: Data preparation"
    # clean up
    rm -rf $out_dir
    # copy
    #    python $genon2db_root/utils/data_prep.py $config_yaml
    python $script_dir/data_copy.py $config_yaml
fi

if [ ${stage} -le 1 ] && [ ${stop_stage} -ge 1 ]; then
    echo "stage 1: SHIRO training"
    # create directory
    if [ -e $shiro_out_dir ]; then
	rm -rf $shiro_out_dir
    fi
    mkdir -p $shiro_out_dir
    #echo $shiro_root_abs
    # create index
    python $genon2db_root/utils/wav2index.py $out_dir/wav/ $script_dir/../dic/ly2ph_ami_koharune.table $shiro_out_dir/index.csv

    # Create model and  phoneme definitions for Japanese
    lua $shiro_root/shiro-mkpm.lua ../../_common/shiro/japanese-phoneset.csv -s 3 -S 3 > $shiro_out_dir/phonemap.json

    lua $shiro_root/shiro-pm2md.lua $shiro_out_dir/phonemap.json -d 12 > $shiro_out_dir/modeldef.json

    # feature extraction
    lua $shiro_root/shiro-fextr.lua $shiro_out_dir/index.csv -d $out_dir/wav -x $shiro_root/extractors/extractor-xxcc-mfcc12-da-16k -r 16000

    ## Train a model given speech and phoneme transcription
    #create an empty model.
    $shiro_root/shiro-mkhsmm -c $shiro_out_dir/modeldef.json > $shiro_out_dir/empty.hsmm

    #  initialize the model (flat start initialization scheme).
    lua $shiro_root/shiro-mkseg.lua $shiro_out_dir/index.csv -m $shiro_out_dir/phonemap.json -d $out_dir/wav -e .param -n 36 > $shiro_out_dir/unaligned-segmentation.json

    # initialize the model (flat start initialization scheme).
    $shiro_root/shiro-init -m $shiro_out_dir/empty.hsmm -s $shiro_out_dir/unaligned-segmentation.json -FT > $shiro_out_dir/flat.hsmm

    # bootstrap/pre-train using the HMM training algorithm and update the alignment accordingly.
    $shiro_root/shiro-rest -m $shiro_out_dir/flat.hsmm -s $shiro_out_dir/unaligned-segmentation.json -n 10 -g > $shiro_out_dir/markovian.hsmm
    $shiro_root/shiro-align -m $shiro_out_dir/markovian.hsmm -s $shiro_out_dir/unaligned-segmentation.json -g > $shiro_out_dir/markovian-segmentation.json

    # train the model using the HSMM training algorithm
    $shiro_root/shiro-rest -m $shiro_out_dir/markovian.hsmm -s $shiro_out_dir/markovian-segmentation.json -n 10 -p 10 -d 50 > $shiro_out_dir/trained.hsmm
fi

if [ ${stage} -le 2 ] && [ ${stop_stage} -ge 2 ]; then
    echo "stage 2: Generate monophone labels using SHIRO"
    ## Align phonemes and speech using a trained model
    $shiro_root/shiro-align -m $shiro_out_dir/trained.hsmm -s $shiro_out_dir/unaligned-segmentation.json -g > $shiro_out_dir/initial-alignment.json

    $shiro_root/shiro-align -m $shiro_out_dir/trained.hsmm -s $shiro_out_dir/initial-alignment.json -p 10 -d 50 > $shiro_out_dir/refined-alignment.json

    # convert the refined segmentation into audacity label files.
    lua $shiro_root/shiro-seg2lab.lua $shiro_out_dir/refined-alignment.json -t 0.005

    # copy mono-phone label file to $out_dir/mono
    if [ -e $out_dir/mono ]; then
	rm -rf $out_dir/mono
    fi
    mkdir $out_dir/mono

    # convert audacity label files to hts mono-phone label
    python $genon2db_root/utils/txt2lab.py $out_dir/wav/ $out_dir/mono --rounding
fi

if [ ${stage} -le 3 ] && [ ${stop_stage} -ge 3 ]; then
    echo "stage 3: Generate HTS full-context label files from monophone labels"

    if [ -e $out_dir/ust ]; then
	rm -rf $out_dir/ust
    fi
    mkdir $out_dir/ust
    
    # generate ust files from mono-phone labels
    echo "generate ust files from mono-phone labels"
    python $genon2db_root/utils/lab2ust.py $out_dir/mono $out_dir/ust

    if [ -e $out_dir/ust_full ]; then
	rm -rf $out_dir/ust_full
    fi
    mkdir $out_dir/ust_full

    # generate HTS full-context label files
    echo "generate HTS full-context label files"

    python $genon2db_root/utils/ust2lab.py $out_dir/ust/ $out_dir/ust_full ../../_common/dic/identity.table


    if [ -e $out_dir/full ]; then
	rm -rf $out_dir/full
    fi
    mkdir $out_dir/full
    
    # Copy label times from mono to full
    echo "Copy label times from mono to full"
    python $genon2db_root/utils/adjust_lab_times.py $out_dir/mono $out_dir/ust_full/ $out_dir/full/
fi

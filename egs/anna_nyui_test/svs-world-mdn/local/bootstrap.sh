#! /bin/bash

#set -e
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
    wav_dir=$out_dir/wav
    ust_dir=$out_dir/ust
    
    mkdir -p $wav_dir
    mkdir -p $ust_dir

    for i in $(ls $db_root/*.wav);
    do
	filename=$(basename $i | sed -e 's#_BPM[0-9]*##g')
	cp $i $out_dir/wav/$filename
    done
    #    find "$db_root" -name *.wav -exec cp {} $wav_dir/$( \;
    find $db_root -name *.ust -exec cp {} $ust_dir \;

    # create lab
    mkdir -p $out_dir/ust_full
    mkdir -p $out_dir/ust_mono
    echo "Create HTS full-context label file from ust"
    python $genon2db_root/utils/ust2lab.py $out_dir/ust/ $out_dir/ust_full \
	   $script_dir/../dic/ly2ph_anna_nyui.table
    echo "Create mono-phone label file from ust"    
    python $genon2db_root/utils/ust2lab.py $out_dir/ust/ $out_dir/ust_mono \
	   $script_dir/../dic/ly2ph_anna_nyui.table --as_mono

    # perf segmentation
    mkdir -p $out_dir/ust_full_seg
    mkdir -p $out_dir/ust_mono_seg
    mkdir -p $out_dir/wav_seg
    
    echo "Perform segmentation of lab/wav with pau"
    python $script_dir/split_data.py $out_dir/ust_mono \
	   $out_dir/ust_full $out_dir/wav $out_dir/ust_mono_seg \
	   $out_dir/ust_full_seg $out_dir/wav_seg $out_dir/offset.csv \
	   --suppress_start_end_pau
fi

if [ ${stage} -le 1 ] && [ ${stop_stage} -ge 1 ]; then
    echo "stage 1: SHIRO preparation"

    mkdir -p $out_dir/aud_lab
    echo "Convert mono-phone label to audacity label"
    python $genon2db_root/utils/lab2txt.py $out_dir/ust_mono_seg $out_dir/aud_lab

    if [ -e $shiro_out_dir ]; then
	rm -rf $shiro_out_dir
    fi
    mkdir -p $shiro_out_dir

    echo "Create index file from mono-phone labels"
    python $genon2db_root/utils/lab2index.py $out_dir/ust_mono_seg/ $shiro_out_dir/index.csv

    # Create model and  phoneme definitions for Japanese
    lua $shiro_root/shiro-mkpm.lua ../../_common/shiro/japanese-phoneset.csv -s 3 -S 3 > $shiro_out_dir/phonemap.json
    lua $shiro_root/shiro-pm2md.lua $shiro_out_dir/phonemap.json -d 12 > $shiro_out_dir/modeldef.json
    # feature extraction
    echo "Feature extraction"
    lua $shiro_root/shiro-fextr.lua $shiro_out_dir/index.csv -d $out_dir/wav_seg -x $shiro_root/extractors/extractor-xxcc-mfcc12-da-16k -r 16000

#    echo "Convert audacity label files into initial segmentation"
    #lua $shiro_root/shiro-lab2seg.lua $shiro_out_dir/index.csv -m $shiro_out_dir/phonemap.json -d $out_dir/aud_lab > $shiro_out_dir/unaligned-segmentation.json
    ## Train a model given speech and phoneme transcription
    #create an empty model.
    $shiro_root/shiro-mkhsmm -c $shiro_out_dir/modeldef.json > $shiro_out_dir/empty.hsmm

    #  initialize the model (flat start initialization scheme).
    lua $shiro_root/shiro-mkseg.lua $shiro_out_dir/index.csv -m $shiro_out_dir/phonemap.json -d $out_dir/wav_seg -e .param -n 36 > $shiro_out_dir/unaligned-segmentation.json

    # initialize the model (flat start initialization scheme).
    $shiro_root/shiro-init -m $shiro_out_dir/empty.hsmm -s $shiro_out_dir/unaligned-segmentation.json -FT > $shiro_out_dir/flat.hsmm

    # bootstrap/pre-train using the HMM training algorithm and update the alignment accordingly.
    $shiro_root/shiro-rest -m $shiro_out_dir/flat.hsmm -s $shiro_out_dir/unaligned-segmentation.json -n 10 -g > $shiro_out_dir/markovian.hsmm
    $shiro_root/shiro-align -m $shiro_out_dir/markovian.hsmm -s $shiro_out_dir/unaligned-segmentation.json -g > $shiro_out_dir/markovian-segmentation.json

    # train the model using the HSMM training algorithm
    $shiro_root/shiro-rest -m $shiro_out_dir/markovian.hsmm -s $shiro_out_dir/markovian-segmentation.json -n 10 -p 10 -d 50 > $shiro_out_dir/trained.hsmm

    
    #lua $shiro_root/shiro-mkseg.lua $shiro_out_dir/index.csv -m $shiro_out_dir/phonemap.json -d $out_dir/wav_seg -e .param -n 36 > $shiro_out_dir/unaligned-segmentation.json

fi

if [ ${stage} -le 2 ] && [ ${stop_stage} -ge 2 ]; then
    echo "stage 2: Generate monophone labels using SHIRO"
    ## Align phonemes and speech using a trained model
    #pretrained_shiro_dir=$pretrained_expdir/shiro
    #shiro_debug_root=../../../../../../shiro/shiro-debug
    #pretrained_shiro_dir=../../anna_nyui_raw/svs-world-mdn/exp/anna_nyui/shiro
    
    $shiro_root/shiro-align -m $shiro_out_dir/trained.hsmm -s $shiro_out_dir/unaligned-segmentation.json -g > $shiro_out_dir/initial-alignment.json
    $shiro_root/shiro-align -m $shiro_out_dir/trained.hsmm  -s $shiro_out_dir/initial-alignment.json -p 10 -d 50 > $shiro_out_dir/refined-alignment.json

    #$shiro_debug_root/shiro-align -m $pretrained_shiro_dir/trained.hsmm -s $shiro_out_dir/unaligned-segmentation.json -g > $shiro_out_dir/initial-alignment.json
    #$shiro_debug_root/shiro-align -m $pretrained_shiro_dir/trained.hsmm  -s $shiro_out_dir/initial-alignment.json -p 10 -d 50 > $shiro_out_dir/refined-alignment.json
    
    # convert the refined segmentation into audacity label files.
    lua $shiro_root/shiro-seg2lab.lua $shiro_out_dir/refined-alignment.json -t 0.005

    # copy mono-phone label file to $out_dir/mono
    if [ -e $out_dir/mono ]; then
	rm -rf $out_dir/mono
    fi
    mkdir $out_dir/mono

    # convert audacity label files to hts mono-phone label
    python $genon2db_root/utils/txt2lab.py $out_dir/wav_seg/ $out_dir/mono --rounding
fi

if [ ${stage} -le 3 ] && [ ${stop_stage} -ge 3 ]; then
    echo "stage 3: Generate HTS full-context label files from monophone labels"
    
    # Copy label times from mono to full
    echo "Copy label times from mono to full"
    if [ -e $out_dir/full ]; then
	rm -rf $out_dir/full
    fi
    mkdir $out_dir/full
    
    python $genon2db_root/utils/adjust_lab_times.py $out_dir/mono $out_dir/ust_full_seg/ $out_dir/full/
fi

if [ ${stage} -le 4 ] && [ ${stop_stage} -ge 4 ]; then
    echo "stage 4: Merge Mono-phone labels"
    
    python $genon2db_root/utils/merge_lab.py $out_dir/offset.csv $out_dir/mono $out_dir/wav
    
fi

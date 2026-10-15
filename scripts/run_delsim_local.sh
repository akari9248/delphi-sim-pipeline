#!/usr/bin/env bash
# Internal entry point, called only after the preserved DELPHI stack is loaded.
set -euo pipefail
[[ ${LEP_IN_CONTAINER:-0} == 1 ]] || { printf 'Error: run through simulate_local.sh.\n' >&2; exit 1; }
output_dir=$1 nevmax=$2 ebeam=$3 version=$4 nrun=$5 ludecv=$6 reader_dir=$7
work_dir="$output_dir/logs/delsim"
mkdir -- "$work_dir"
cd -- "$work_dir"
repo_dir=$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
# runsim accepts -LUDECV but this release's v94c template has no LUDECV card,
# so the option alone is silently ignored. Resolve a title in an isolated
# one-event SIM-only prerun, then add the card explicitly for the main run.
mkdir title-prerun
printf 'Preparing the DELSIM title; log: %s/logs/title-prerun.log\n' "$output_dir"
(
  cd title-prerun
  timeout --signal=TERM --kill-after=10s "${LEP_SIM_TIMEOUT:-900}" \
    runsim -SIM -VERSION "$version" -LABO CERN -NRUN "$nrun" -EBEAM "$ebeam" \
    -NEVMAX 1 -gext "$output_dir/fadgen/events.fadgen"
) > "$output_dir/logs/title-prerun.log" 2>&1 || {
  printf 'Error: title prerun failed; inspect %s/logs/title-prerun.log\n' "$output_dir" >&2
  exit 1
}
python3 "$repo_dir/python/prepare_title.py" title-prerun/simlocal.title simlocal_edit.title \
  --max-events "$nevmax" --ludecv "$ludecv"
printf 'Running DELSIM and DELANA; log: %s/logs/delsim.log\n' "$output_dir"
timeout --signal=TERM --kill-after=10s "${LEP_SIM_TIMEOUT:-900}" \
  runsim -VERSION "$version" -LABO CERN -NRUN "$nrun" -EBEAM "$ebeam" \
  -NEVMAX "$nevmax" -gext "$output_dir/fadgen/events.fadgen" -STITL simlocal_edit.title \
  > "$output_dir/logs/delsim.log" 2>&1 || {
    printf 'Error: DELSIM/DELANA failed; inspect %s/logs/delsim.log\n' "$output_dir" >&2
    exit 1
  }
[[ -s simana.sdst && -s simana.fadana ]] || {
  printf 'Error: DELSIM/DELANA did not produce both DST files; inspect %s/logs/delsim.log\n' "$output_dir" >&2
  exit 1
}
cp -- simana.sdst simana.fadana "$output_dir/dst/"
printf 'Converting MC DST to TTree; log: %s/logs/root-conversion.log\n' "$output_dir"
bash "$reader_dir/scripts/read_lep_data.sh" --mc \
  --input "$output_dir/dst/simana.sdst" --output "$output_dir/root/events.root" \
  --max-events "$nevmax" > "$output_dir/logs/root-conversion.log" 2>&1 || {
    printf 'Error: ROOT conversion failed; inspect %s/logs/root-conversion.log\n' "$output_dir" >&2
    exit 1
  }
printf 'ROOT TTree: %s/root/events.root\nDST: %s/dst/simana.sdst\nLogs: %s/logs\n' \
  "$output_dir" "$output_dir" "$output_dir"

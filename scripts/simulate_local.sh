#!/usr/bin/env bash
# Convert external LEP HepMC events, run DELSIM, and write an Events TTree.
set -euo pipefail
repo_dir=$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
reader_dir=${DELPHI_NANOAOD_DIR:-$repo_dir/../delphi-nanoaod}
converter=${HEPMC2FADGEN:-$HOME/.local/bin/hepmc2fadgen}
input="" output_dir="" ebeam="" nevmax=10 version=v94c nrun=100001 ludecv=TRUE
die() { printf 'Error: %s\n' "$*" >&2; exit 1; }
need_value() { [[ $# -ge 2 && -n "$2" ]] || die "$1 requires a value"; }
usage() {
  cat <<'EOF'
Usage: bash scripts/simulate_local.sh [options]
  --input FILE          Hadron-level e+e- HepMC2 or HepMC3 events
  --output-dir DIR      New output directory (must not already exist)
  --ebeam GEV           Beam energy, matching the HepMC input
  --max-events N        Events to simulate (default: 10; input must contain more)
  --version TAG         DELPHI processing version (default: v94c)
  --nrun N              Simulation run number and random-seed input (default: 100001)
  --decay-vertices MODE generator (default) or delphi (legacy lifetime table)
  --check-env           Check the converter and the local DELPHI environment
  -h, --help            Show this help

Outputs: fadgen/events.fadgen, dst/simana.sdst, dst/simana.fadana,
root/events.root (TTree), and logs/. No CMSSW, key4hep, or CVMFS is required.
The simulation uses the existing ../delphi-nanoaod/scripts/with_delphi.sh.
EOF
}
while [[ $# -gt 0 ]]; do
  case "$1" in
    --input) need_value "$@"; input=$2; shift 2 ;;
    --output-dir) need_value "$@"; output_dir=$2; shift 2 ;;
    --ebeam) need_value "$@"; ebeam=$2; shift 2 ;;
    --max-events) need_value "$@"; nevmax=$2; shift 2 ;;
    --version) need_value "$@"; version=$2; shift 2 ;;
    --nrun) need_value "$@"; nrun=$2; shift 2 ;;
    --decay-vertices)
      need_value "$@"
      case "$2" in generator) ludecv=TRUE ;; delphi) ludecv=FALSE ;; *) die "Invalid decay-vertex mode" ;; esac
      shift 2 ;;
    --check-env)
      [[ -x "$converter" ]] || die "Converter not installed: $converter"
      printf 'Converter: %s\n' "$converter"
      exec bash "$reader_dir/scripts/with_delphi.sh" bash -c \
        'command -v runsim; command -v gfortran; root-config --version' ;;
    -h|--help) usage; exit 0 ;;
    *) die "Unknown option: $1" ;;
  esac
done
[[ -f "$input" && -n "$output_dir" && -n "$ebeam" ]] || die "Specify --input, --output-dir, and --ebeam; see --help"
[[ -x "$converter" ]] || die "Converter not installed: $converter"
[[ "$nevmax" =~ ^[1-9][0-9]*$ && "$nrun" =~ ^[1-9][0-9]*$ ]] || die "Event count and run number must be positive integers"
[[ "$ebeam" =~ ^[0-9]+([.][0-9]+)?$ ]] || die "Beam energy must be a positive number in GeV"
[[ "$version" =~ ^v(92e|93d|94c|95d|95g|96g|97g|98e|99e|a0e|a0u)$ ]] || die "Unsupported DELPHI processing version"
input=$(realpath -- "$input")
output_dir=$(realpath -m -- "$output_dir")
[[ ! -e "$output_dir" ]] || die "Output directory already exists: $output_dir"
mkdir -p -- "$(dirname -- "$output_dir")"
mkdir -- "$output_dir"
mkdir -- "$output_dir/fadgen" "$output_dir/dst" "$output_dir/root" "$output_dir/logs"
printf 'Output directory: %s\n' "$output_dir"
"$converter" "$input" "$output_dir/fadgen/events.fadgen" 2>&1 | tee "$output_dir/logs/converter.log"
python3 "$repo_dir/python/check_fadgen.py" "$output_dir/fadgen/events.fadgen" \
  --ebeam "$ebeam" --max-events "$nevmax" | tee "$output_dir/logs/input-check.json"
exec bash "$reader_dir/scripts/with_delphi.sh" bash "$repo_dir/scripts/run_delsim_local.sh" \
  "$output_dir" "$nevmax" "$ebeam" "$version" "$nrun" "$ludecv" "$reader_dir"

#!/usr/bin/env bash
# Build against a user-installed HepMC3, without the CERN software mounts.
set -euo pipefail
repo_dir=$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
hepmc_prefix=${HEPMC3_PREFIX:-$HOME/.local/opt/hepmc3/3.3.1}
install_prefix=${LEP_INSTALL_PREFIX:-$HOME/.local}
cmake -S "$repo_dir" -B "$repo_dir/build-local" \
  -DCMAKE_BUILD_TYPE=Release -DCMAKE_PREFIX_PATH="$hepmc_prefix" \
  -DCMAKE_INSTALL_PREFIX="$install_prefix" -DBUILD_TESTING=ON
cmake --build "$repo_dir/build-local" -j "${LEP_BUILD_JOBS:-4}"
ctest --test-dir "$repo_dir/build-local" --output-on-failure
cmake --install "$repo_dir/build-local"
printf 'Installed converter: %s/bin/hepmc2fadgen\n' "$install_prefix"

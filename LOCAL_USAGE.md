# Standalone HepMC to DELPHI simulation on this server

No CMSSW, key4hep, CVMFS mount, Docker daemon, or administrator privileges
are needed for this local setup. The converter uses a privately installed
HepMC3 library; DELSIM and DELANA run in the existing CERN DELPHI container
through `../delphi-nanoaod/scripts/with_delphi.sh`.

## Installed software

| Component | Location |
| --- | --- |
| HepMC3 3.3.1 | `/storage/shuangyuan/.local/opt/hepmc3/3.3.1` |
| Converter | `/storage/shuangyuan/.local/bin/hepmc2fadgen` |
| Source checkout | `/storage/shuangyuan/code/analysis_color/delphi-sim-pipeline` |
| ROOT and DELPHI environment | Existing `../.lep-tools` installations |

Source: <https://github.com/delphi-fullDST-edm4hep/delphi-sim-pipeline>, commit
`ec55d45b73b42a828dae518624b4348defb5d7dc` (2026-09-06). The upstream
`hepmc2fadgen.cpp` is unchanged. Local additions provide a standalone CMake
build, local simulation wrappers, and installation checks.

HepMC3 was downloaded from
<https://hepmc.web.cern.ch/hepmc/releases/HepMC3-3.3.1.tar.gz> and built with
GCC 11.4, without ROOT I/O or Python bindings. The archive is retained at
`../.lep-tools/downloads/HepMC3-3.3.1.tar.gz`; its recorded SHA256 is
`08240160b0f28dc3293aa4d61ce65e2d67cd597acf6faca439f2e46625f7e793`.
The installed executable embeds the HepMC3 library directory in its RUNPATH;
no global `LD_LIBRARY_PATH` change is needed.

## Convert an existing HepMC file

```bash
cd /storage/shuangyuan/code/analysis_color/delphi-sim-pipeline
source ../.lep-tools/activate.sh
hepmc2fadgen /path/to/events.hepmc /path/to/events.fadgen
```

The reader auto-detects HepMC3 Asciiv3 and HepMC2 IO_GenEvent. The converter
normalizes momentum/length units to GeV/mm. It reads the whole input file;
check its accepted/rejected event counts. The raw upstream executable replaces
an existing output file; the simulation wrapper below requires a new output
directory and retains its logs.

## Simulate external LEP events and produce a TTree

```bash
cd /storage/shuangyuan/code/analysis_color/delphi-sim-pipeline
bash scripts/simulate_local.sh --check-env

bash scripts/simulate_local.sh \
  --input /path/to/panscales-ee-hadronized.hepmc \
  --output-dir /data/shuangyuan/LEPData/simulation/panscales-test \
  --ebeam 45.625 --max-events 10 --version v94c --nrun 100002
```

Choose `--ebeam` to match the actual generator beam energy. For example,
91.25 GeV center-of-mass energy requires 45.625 GeV per beam; 91.2 GeV
requires 45.6 GeV. The input must be hadronized e+e- events. The large
`FlatQCD-TuneCH3-AngularCluster13TeV6HepMC-S646195519.hepmc` example is a
13.6 TeV pp sample and is not a LEP simulation input.

The wrapper validates FADGEN framing and the leading beam entries. It requires
more accepted input events than `--max-events` to avoid known DELSIM loops at
external-generator EOF. It then runs simulation, reconstruction, Short DST
creation, and the existing MC DST-to-TTree converter.

Output layout:

```text
panscales-test/
  fadgen/events.fadgen
  dst/simana.sdst
  dst/simana.fadana
  root/events.root                 # Events TTree
  logs/converter.log
  logs/input-check.json
  logs/title-prerun.log
  logs/delsim.log
  logs/root-conversion.log
  logs/delsim/                     # Native title, raw simulation, scratch files
```

The local wrappers use the installed official stack rather than upstream's
AFS/EOS paths or `cmssw/el9` container path. The output directory must be
visible through the existing container mounts (`/storage/shuangyuan` or
`/data/shuangyuan/LEPData`). Use a different `--nrun` for each production job;
the run number participates in DELSIM's random seed. Simulation has a
900-second default timeout per stage, adjustable with `LEP_SIM_TIMEOUT`.
Raw simulation and prerun files remain under `logs/delsim/`; plan disk space
before large production.

## Decays and generator settings

Use an input record with the decay history and nonzero decay vertices for
B/D hadrons and tau leptons. The current converter writes these as LUJETS
status 11. The default `--decay-vertices generator` enables `LUDECV TRUE`
so DELSIM uses the flight distances from the generator record.

This release's `runsim` accepts `-LUDECV` but its v94c title template omits
the card, so the command-line option alone has no effect. The local runner
creates a fully resolved external-input title with a one-event SIM-only
prerun in a separate directory, inserts the LUDECV card, restores the requested
event count, and passes it to the main run with `-STITL`. It verifies
`IGENER 0` before using the title. The effective title remains in
`logs/delsim/simlocal.title`.

`--decay-vertices delphi` explicitly selects the legacy DELSIM lifetime table
instead. Do not use the default generator mode on a file whose decay-chain
vertices are all zero; inspect the converter's displacement summary first.

The upstream interface expects K0_S, Lambda, Sigma-/+, Xi-/0 (and
antiparticles) to reach DELSIM undecayed, tagged for decay in the detector
simulation. Configure the generator/hadronization stage accordingly. A full
HepMC history alone does not establish compatibility. The conversion also
filters unsupported particle codes and limits records to 4000 particles;
review rejected events and momentum conservation before physics production.

## Installation validation

The HepMC3 upstream test suite passed 33/33 tests. The local CTest check
compares conversions from HepMC2, HepMC3, and MeV/cm inputs, checks record
framing, beam placement, four-momentum conservation, mother links and known
3 mm decay displacements, and rejects unsafe event counts and internal-generator
titles.

The synthetic sample is `local-validation/input/smoke.hepmc3` (12 events,
91.25 GeV e+e- -> B+ B-, followed by three-pion B decays). It is an
installation fixture, not a generator prediction or a physics sample.
The explicit-LUDECV end-to-end output is
`local-validation/run-3-ludecv/root/events.root`; validation is recorded in
`local-validation/run-3-ludecv/validation.json`.
It contains an `Events` TTree with 3 entries and 208 branches. All six
simulated B flight distances agree with the injected 3 mm displacement within
0.002 mm, and the generator-to-simulation associations passed the check.
The earlier `local-validation/run-3/` run used the unmodified template and
the legacy DELSIM lifetime table; it is retained for comparison.

To repeat the software checks:

```bash
ctest --test-dir build-local --output-on-failure
source ../.lep-tools/activate.sh
python3 tests/check_smoke_root.py local-validation/run-3-ludecv/root/events.root
```

To repeat the full simulation, choose a new output directory:

```bash
bash scripts/simulate_local.sh \
  --input local-validation/input/smoke.hepmc3 \
  --output-dir local-validation/repeat-test \
  --ebeam 45.625 --max-events 3
```

These checks establish that the local software chain works. They do not
validate a PanScales tune, generator configuration, b-tagging performance, or
an analysis response matrix.

## Rebuild

```bash
bash build_local.sh
```

`HEPMC3_PREFIX` overrides the HepMC3 installation; `LEP_INSTALL_PREFIX`
overrides the converter install prefix (default `~/.local`). To rebuild
HepMC3 from the retained official archive:

```bash
tar -xzf ../.lep-tools/downloads/HepMC3-3.3.1.tar.gz -C /tmp
cmake -S /tmp/HepMC3-3.3.1 -B /tmp/lep-hepmc3-build-3.3.1 \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_INSTALL_PREFIX="$HOME/.local/opt/hepmc3/3.3.1" \
  -DCMAKE_INSTALL_LIBDIR=lib \
  -DHEPMC3_ENABLE_ROOTIO=OFF -DHEPMC3_ENABLE_PYTHON=OFF \
  -DHEPMC3_ENABLE_TEST=ON -DHEPMC3_BUILD_EXAMPLES=OFF
cmake --build /tmp/lep-hepmc3-build-3.3.1 -j 4
ctest --test-dir /tmp/lep-hepmc3-build-3.3.1 --output-on-failure -j 4
cmake --install /tmp/lep-hepmc3-build-3.3.1
bash build_local.sh
```

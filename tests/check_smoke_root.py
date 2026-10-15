"""Validate the synthetic B-decay installation sample after DELSIM and reconstruction."""
import argparse
import json
import math
from pathlib import Path

import ROOT

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("input")
parser.add_argument("--events", type=int, default=3)
parser.add_argument("--report", type=Path)
args = parser.parse_args()
source = ROOT.TFile.Open(args.input)
assert source and not source.IsZombie(), "Cannot open ROOT output"
tree = source.Get("Events")
assert tree and tree.ClassName() == "TTree", "Events must be a TTree"
assert tree.GetEntries() == args.events, "Unexpected reconstructed event count"
flights, multiplicities, run_numbers = [], [], []
for row in tree:
    assert int(row.Event_schemaVersion) == 1
    assert row.nGenPart == 10
    assert len(row.Part_fourMomentum) == row.nPart > 0
    assert len(row.SimPart_fourMomentum) == row.nSimPart
    assert len(row.SimVtx_position) == row.nSimVtx
    multiplicities.append(int(row.nPart))
    run_numbers.append(int(row.Event_runNumber))
    count = 0
    for i, pdg in enumerate(row.GenPart_pdgId):
        if abs(pdg) != 521:
            continue
        count += 1
        sim_idx = int(row.GenPart_simIdx[i])
        assert 0 <= sim_idx < row.nSimPart
        assert int(row.SimPart_genIdx[sim_idx]) == i
        origin = int(row.SimPart_originVtxIdx[sim_idx])
        decay = int(row.SimPart_decayVtxIdx[sim_idx])
        assert 0 <= origin < row.nSimVtx and 0 <= decay < row.nSimVtx
        a, b = row.SimVtx_position[origin], row.SimVtx_position[decay]
        # Native DELPHI simulated vertex coordinates are in cm.
        flight_mm = 10.0 * math.dist((a.X(), a.Y(), a.Z()), (b.X(), b.Y(), b.Z()))
        assert math.isclose(flight_mm, 3.0, abs_tol=0.002), f"Lost generator displacement: {flight_mm} mm"
        flights.append(flight_mm)
    assert count == 2
assert all(run < 0 for run in run_numbers), "Expected simulated run numbers"
report = {"sample": "synthetic installation test; not a physics sample", "class": tree.ClassName(),
          "events": tree.GetEntries(), "branches": tree.GetListOfBranches().GetEntries(),
          "reconstructed_multiplicity": multiplicities, "run_numbers": run_numbers,
          "b_flight_distances_mm": flights}
print(json.dumps(report, indent=2))
if args.report:
    args.report.write_text(json.dumps(report, indent=2) + "\n")

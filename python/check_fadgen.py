"""Validate record framing and the e+e- beam settings before running DELSIM."""
import argparse
import json
import math
import struct


def inspect(path, ebeam):
    count = 0
    with open(path, "rb") as stream:
        while True:
            marker = stream.read(4)
            if len(marker) != 4:
                raise ValueError("Missing FADGEN end marker")
            size = struct.unpack("<i", marker)[0]
            if size < 4 or size > 240004:
                raise ValueError("Invalid FADGEN record size")
            payload = stream.read(size)
            if len(payload) != size or stream.read(4) != marker:
                raise ValueError("Truncated FADGEN record or mismatched markers")
            n = struct.unpack_from("<i", payload)[0]
            if n == 0:
                if size != 4 or stream.read(1):
                    raise ValueError("Invalid FADGEN end marker")
                return count
            if n < 2 or n > 4000 or size != 4 + 60 * n:
                raise ValueError("Invalid FADGEN particle count")
            beams = [struct.unpack_from("<5i10f", payload, 4 + 60 * i) for i in range(2)]
            if sorted(p[1] for p in beams) != [-11, 11] or any(p[0] != 21 for p in beams):
                raise ValueError("Expected two leading e+e- beam entries; this is not a LEP-ready event")
            if any(not math.isclose(p[8], ebeam, rel_tol=1e-5, abs_tol=1e-4) for p in beams):
                raise ValueError(f"Beam energy does not match --ebeam {ebeam} GeV")
            count += 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input")
    parser.add_argument("--ebeam", type=float, required=True)
    parser.add_argument("--max-events", type=int, required=True)
    args = parser.parse_args()
    try:
        count = inspect(args.input, args.ebeam)
        # Keep a buffer: some DELSIM versions loop at external-generator EOF.
        if count <= args.max_events:
            raise ValueError(f"Need more than {args.max_events} accepted input events; found {count}. "
                             "Reduce --max-events or provide more input events to avoid DELSIM EOF loops.")
    except (OSError, ValueError, struct.error) as exc:
        parser.exit(1, f"Error: {exc}\n")
    print(json.dumps({"accepted_events": count, "requested_events": args.max_events,
                      "beam_energy_GeV": args.ebeam}, indent=2))

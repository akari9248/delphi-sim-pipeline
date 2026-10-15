"""Check real converter output, including displaced decays and unit conversion."""
import math
from pathlib import Path
import struct
import subprocess
import sys
import tempfile


def read_events(path):
    events = []
    with path.open("rb") as stream:
        while True:
            size_bytes = stream.read(4)
            assert len(size_bytes) == 4, "Missing end marker"
            size = struct.unpack("<i", size_bytes)[0]
            payload = stream.read(size)
            assert len(payload) == size, "Truncated record"
            assert stream.read(4) == size_bytes, "Mismatched record markers"
            n = struct.unpack_from("<i", payload)[0]
            if n == 0:
                assert size == 4 and stream.read() == b"", "Invalid end marker"
                return events
            assert size == 4 + 60 * n
            events.append([struct.unpack_from("<5i10f", payload, 4 + 60 * i) for i in range(n)])


with tempfile.TemporaryDirectory(prefix="lep-converter-test-") as temp:
    work = Path(temp)
    subprocess.run([sys.argv[1], str(work)], check=True)
    references = []
    for name in ("smoke.hepmc3", "smoke.hepmc2", "smoke_mev_cm.hepmc3"):
        output = work / (name + ".fadgen")
        subprocess.run([sys.argv[2], str(work / name), str(output)], check=True)
        events = read_events(output)
        assert len(events) == 12
        for particles in events:
            assert len(particles) == 10
            assert sorted(p[1] for p in particles[:2]) == [-11, 11]
            assert all(p[0] == 21 for p in particles[:2])
            assert sum(abs(p[1]) == 521 and p[0] == 11 for p in particles) == 2
            final = [p for p in particles if p[0] == 1]
            assert len(final) == 6
            assert math.isclose(sum(p[8] for p in final), 91.25, abs_tol=2e-5)
            assert all(abs(sum(p[j] for p in final)) < 2e-5 for j in (5, 6, 7))
            for b in (p for p in particles if abs(p[1]) == 521):
                daughters = [p for p in particles if p[2] == particles.index(b) + 1]
                assert len(daughters) == 3
                assert 0 < b[3] <= b[4] <= len(particles)
                assert math.isclose(math.dist(b[10:13], daughters[0][10:13]), 3.0, abs_tol=2e-5)
                assert all(math.dist(p[10:13], daughters[0][10:13]) < 1e-6 for p in daughters)
        references.append(events)
    # Different readers can reorder particles; compare their physical records.
    for other in references[1:]:
        for a, b in zip(references[0], other):
            key = lambda p: (p[1], p[5], p[6])
            for pa, pb in zip(sorted(a, key=key), sorted(b, key=key)):
                assert pa[:2] == pb[:2]
                assert all(math.isclose(x, y, abs_tol=2e-5) for x, y in zip(pa[5:], pb[5:]))
    repo = Path(__file__).resolve().parent.parent
    check = [sys.executable, str(repo / "python/check_fadgen.py"), str(work / "smoke.hepmc3.fadgen")]
    subprocess.run(check + ["--ebeam", "45.625", "--max-events", "3"], check=True)
    for beam, count in (("45.6", "3"), ("45.625", "12")):
        result = subprocess.run(check + ["--ebeam", beam, "--max-events", count], capture_output=True)
        assert result.returncode != 0, "Must reject beam mismatch or unsafe external-input EOF"
    title = work / "simlocal.title"
    title.write_text("NEVMAX 1\nIGENER 0\nEBEAM 45.625\nJSHORT TRUE\n")
    edited = work / "edited.title"
    prepare = [sys.executable, str(repo / "python/prepare_title.py"), str(title), str(edited),
               "--max-events", "3", "--ludecv", "TRUE"]
    subprocess.run(prepare, check=True)
    assert "LUDECV TRUE\n" in edited.read_text() and "NEVMAX 3\n" in edited.read_text()
    title.write_text(title.read_text().replace("IGENER 0", "IGENER 15"))
    assert subprocess.run(prepare, capture_output=True).returncode != 0, "Must reject internal-generator titles"
    print("PASS: HepMC2/HepMC3, GEV/MM and MEV/CM, beams, momentum, ancestry, and 3 mm decays")

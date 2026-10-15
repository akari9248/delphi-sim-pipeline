"""Set decay-vertex handling explicitly in a resolved external-generator title."""
import argparse
from pathlib import Path
import re

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("source", type=Path)
parser.add_argument("output", type=Path)
parser.add_argument("--max-events", type=int, required=True)
parser.add_argument("--ludecv", choices=("TRUE", "FALSE"), required=True)
args = parser.parse_args()
text = args.source.read_text()
if not re.search(r"^IGENER\s+0\s*$", text, re.MULTILINE):
    parser.exit(1, "Error: title does not select external-generator input (IGENER 0)\n")
text, replaced = re.subn(r"^NEVMAX\s+.*$", f"NEVMAX {args.max_events}", text, flags=re.MULTILINE)
if replaced != 1:
    parser.exit(1, "Error: expected one resolved NEVMAX card\n")
text = re.sub(r"^LUDECV\s+.*\n?", "", text, flags=re.MULTILINE)
text, inserted = re.subn(r"^(JSHORT\s+.*)$", rf"\1\nLUDECV {args.ludecv}", text, flags=re.MULTILINE)
if inserted != 1:
    parser.exit(1, "Error: expected one JSHORT card for LUDECV insertion\n")
args.output.write_text(text)
print(f"Resolved title: IGENER 0, NEVMAX {args.max_events}, LUDECV {args.ludecv}")

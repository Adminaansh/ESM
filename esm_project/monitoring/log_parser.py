# monitoring/log_parser.py
import re
from collections import Counter
from typing import Iterable

# Matches dotted names ending in Error/Exception/Warning/Exit/Interrupt,
# e.g. ValueError, django.db.utils.OperationalError, requests.exceptions.Timeout (see note)
EXC_RE = re.compile(
    r'\b((?:[A-Za-z_][\w]*\.)*[A-Z][A-Za-z0-9_]*(?:Error|Exception|Warning|Exit|Interrupt))\b'
)

def count_exceptions(lines: Iterable[str], short_names: bool = True) -> dict:
    counts = Counter()
    for line in lines:
        for match in EXC_RE.findall(line):
            counts[match.rsplit(".", 1)[-1] if short_names else match] += 1
    return dict(counts)


# count_exceptions(["ValueError", "TypeError", "ValueError"])
# -> {"ValueError": 2, "TypeError": 1}
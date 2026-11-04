"""Portable source/environment bindings for the R041 bounded development run."""
from __future__ import annotations

import platform
from pathlib import Path

import numpy as np
import pandas as pd
import sklearn
from confirm_compound_multiseason import BASE, canonical_file_sha
from confirm_compound_v8 import hashes as historical_hashes


def source_hashes() -> dict:
    """Include historical preprocessing and every new model/study dependency."""
    scripts = Path(__file__).parent
    paths = [scripts/name for name in ("compound_bounded_common.py", "prepare_compound_bounded.py",
             "diagnose_compound_bounded.py", "diagnose_compound_adaptation.py")]
    paths += [BASE/"apex_engine/src/apexsim"/name for name in (
        "research/compound_bounded.py", "data/tyre_dataset.py", "data/benchmark_guard.py",
        "data/fastf1_archive.py", "data/jolpica.py", "provenance.py", "research/evidence.py")]
    paths.append(BASE/"research/protocols/COMPOUND_BOUNDED_V9.md")
    return {**historical_hashes(), **{str(p.relative_to(BASE)).replace("\\", "/"): canonical_file_sha(p) for p in paths}}


def environment() -> dict:
    return {"python": platform.python_version(), "numpy": np.__version__, "pandas": pd.__version__,
            "sklearn": sklearn.__version__, "platform": platform.platform()}

from __future__ import annotations

import sys
from pathlib import Path


INFRA_DIR = Path(__file__).resolve().parents[1]
if str(INFRA_DIR) not in sys.path:
    sys.path.insert(0, str(INFRA_DIR))

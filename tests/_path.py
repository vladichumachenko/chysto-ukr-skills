"""Make the skill's scripts importable from the tests directory."""
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SKILL = REPO / "skills" / "chysto"
SCRIPTS = SKILL / "scripts"
DATA = SKILL / "data"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

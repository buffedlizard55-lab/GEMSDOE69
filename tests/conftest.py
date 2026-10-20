import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))
# Shared scientific tools are vendored; keep local gems tests ahead of the
# template's separately named gems package while exposing pinned gems57.
sys.path.append(str(ROOT / "vendor" / "template66"))

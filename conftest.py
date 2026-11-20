import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BACKEND = ROOT / "backend"

# Ensure backend directory is first in sys.path so 'app' resolves to 'backend/app' package,
# rather than 'd:\Matchain\app.py' (the Streamlit demo script).
if str(BACKEND) in sys.path:
    sys.path.remove(str(BACKEND))
sys.path.insert(0, str(BACKEND))

if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

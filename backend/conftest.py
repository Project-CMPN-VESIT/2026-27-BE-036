import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent
ROOT = BACKEND.parent

# Ensure backend directory is first in sys.path so 'app' resolves to 'backend/app' package,
# rather than 'd:\Matchain\app.py' (the Streamlit demo script).
if "app" in sys.modules and not hasattr(sys.modules["app"], "__path__"):
    del sys.modules["app"]

if str(BACKEND) in sys.path:
    sys.path.remove(str(BACKEND))
sys.path.insert(0, str(BACKEND))

if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

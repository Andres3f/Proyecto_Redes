import sys
from pathlib import Path

# Añadir la raíz del proyecto al path para que `import src` funcione en tests
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

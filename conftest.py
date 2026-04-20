"""Root conftest: add project root to sys.path for 'from src.*' imports."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

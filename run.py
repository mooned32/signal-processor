import sys
from pathlib import Path

# Гарантируем видимость src для Python
src_path = Path(__file__).resolve().parent / "src"
if src_path.exists() and str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from app.main import main

if __name__ == "__main__":
    main()
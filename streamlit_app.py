"""Streamlit Community Cloud entrypoint for the AIDDI app.

Community Cloud runs from the repository root. The app itself lives in the
`AIDDI` folder and currently uses paths relative to that folder, so this
entrypoint switches into `AIDDI` before running the real app entrypoint.
"""

from pathlib import Path
import os
import runpy
import sys


APP_DIR = Path(__file__).resolve().parent / "AIDDI"

os.chdir(APP_DIR)
sys.path.insert(0, str(APP_DIR))

runpy.run_path(str(APP_DIR / "Home.py"), run_name="__main__")

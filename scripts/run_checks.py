import subprocess, sys
from pathlib import Path
root=Path(__file__).resolve().parents[1]
subprocess.run([sys.executable,"-m","unittest","discover","-s","tests","-v"],cwd=root,check=True)

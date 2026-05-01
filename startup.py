import subprocess
import sys

subprocess.run(
    [sys.executable, "-u", "bot.py"],
    check=True
)
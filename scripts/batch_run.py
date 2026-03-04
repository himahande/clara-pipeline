"""Convenience script: batch-run all transcripts."""

import subprocess
import sys

if __name__ == "__main__":
    sys.exit(subprocess.call([sys.executable, "scripts/cli.py", "batch"]))

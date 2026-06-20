import argparse
import datetime as dt
import subprocess
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LOG = ROOT / ".tmp" / "nightly-check.log"


def run_command(command, log_file):
    started = dt.datetime.now().isoformat(timespec="seconds")
    log_file.write(f"\n[{started}] $ {' '.join(command)}\n")
    log_file.flush()

    completed = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    log_file.write(completed.stdout)
    log_file.write(f"[exit {completed.returncode}]\n")
    log_file.flush()
    return completed.returncode


def main():
    parser = argparse.ArgumentParser(description="Run QueHun checks in a long loop.")
    parser.add_argument("--interval", type=float, default=60.0, help="Seconds between rounds.")
    parser.add_argument("--rounds", type=int, default=0, help="0 means run until interrupted.")
    parser.add_argument("--log", default=str(DEFAULT_LOG), help="Log file path.")
    args = parser.parse_args()

    log_path = Path(args.log)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    checks = [
        [sys.executable, "-m", "compileall", "-q", "ai", "capture", "cv", "model", "runtime", "state", "ui", "main.py"],
        [sys.executable, "-m", "pytest", "-q"],
    ]

    failures = 0
    round_no = 0
    with log_path.open("a", encoding="utf-8") as log_file:
        while args.rounds <= 0 or round_no < args.rounds:
            round_no += 1
            header = dt.datetime.now().isoformat(timespec="seconds")
            log_file.write(f"\n===== QueHun nightly round {round_no} at {header} =====\n")
            log_file.flush()

            for command in checks:
                if run_command(command, log_file) != 0:
                    failures += 1

            print(
                f"round={round_no} failures={failures} log={log_path}",
                flush=True,
            )
            if args.rounds <= 0 or round_no < args.rounds:
                time.sleep(max(0.0, args.interval))

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())

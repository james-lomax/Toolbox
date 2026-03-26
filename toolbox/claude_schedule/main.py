import argparse
import json
import os
import re
import signal
import subprocess
import sys
import time as time_module
from datetime import datetime, timedelta
from pathlib import Path

BASE_DIR = Path.home() / ".toolbox" / "claude-schedule"
SCHEDULE_FILE = BASE_DIR / "schedule.json"
PID_FILE = BASE_DIR / "daemon.pid"


def parse_time(time_str: str) -> datetime:
    """Parse a time string like '3am', '4:45pm', '15:00', '+5m' into a datetime."""
    time_str = time_str.strip().lower()

    # Relative: "+1m", "+30m", "+2h"
    m = re.fullmatch(r"\+(\d+)([mh])", time_str)
    if m:
        amount = int(m.group(1))
        unit = m.group(2)
        delta = timedelta(minutes=amount) if unit == "m" else timedelta(hours=amount)
        return datetime.now() + delta

    # "3am", "11pm"
    m = re.fullmatch(r"(\d{1,2})(am|pm)", time_str)
    if m:
        hour = int(m.group(1))
        if m.group(2) == "pm" and hour != 12:
            hour += 12
        elif m.group(2) == "am" and hour == 12:
            hour = 0
        minute = 0
    else:
        # "4:45pm", "3:30am"
        m = re.fullmatch(r"(\d{1,2}):(\d{2})(am|pm)", time_str)
        if m:
            hour = int(m.group(1))
            minute = int(m.group(2))
            if m.group(3) == "pm" and hour != 12:
                hour += 12
            elif m.group(3) == "am" and hour == 12:
                hour = 0
        else:
            # 24h: "15:00", "03:00"
            m = re.fullmatch(r"(\d{1,2}):(\d{2})", time_str)
            if m:
                hour = int(m.group(1))
                minute = int(m.group(2))
            else:
                print(f"Error: cannot parse time '{time_str}'", file=sys.stderr)
                print("Supported formats: 3am, 4:45pm, 03:00, 16:45, +1m, +2h", file=sys.stderr)
                sys.exit(1)

    now = datetime.now()
    target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if target <= now:
        target += timedelta(days=1)
    return target


def load_schedule() -> list[dict]:
    if not SCHEDULE_FILE.exists():
        return []
    return json.loads(SCHEDULE_FILE.read_text())


def save_schedule(schedule: list[dict]):
    BASE_DIR.mkdir(parents=True, exist_ok=True)
    SCHEDULE_FILE.write_text(json.dumps(schedule, indent=2))


def create_worktree(dry: bool) -> tuple[str, str, str]:
    """Create a git worktree on a new branch. Returns (worktree_path, branch_name, repo_root)."""
    repo_root = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True, text=True, check=True,
    ).stdout.strip()

    current_branch = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        capture_output=True, text=True, check=True,
    ).stdout.strip()

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    repo_name = os.path.basename(repo_root)
    branch_name = f"claude-schedule/{current_branch}/{timestamp}"
    worktree_dir = Path.home() / "workspace" / "worktrees"
    worktree_path = str(worktree_dir / f"{repo_name}-{timestamp}")

    if dry:
        print(f"Would create worktree at: {worktree_path}")
        print(f"Would create branch: {branch_name} (from {current_branch})")
    else:
        subprocess.run(
            ["git", "worktree", "add", "-b", branch_name, worktree_path],
            check=True,
        )
        print(f"Created worktree at: {worktree_path}")
        print(f"Created branch: {branch_name} (from {current_branch})")

    return worktree_path, branch_name, repo_root


def get_daemon_pid() -> int | None:
    if not PID_FILE.exists():
        return None
    pid = int(PID_FILE.read_text().strip())
    # Check if process is alive
    try:
        os.kill(pid, 0)
        return pid
    except OSError:
        PID_FILE.unlink(missing_ok=True)
        return None


def daemon_is_running() -> bool:
    return get_daemon_pid() is not None


def run_daemon():
    """Main daemon loop. Checks schedule every 30 seconds and runs due jobs."""
    BASE_DIR.mkdir(parents=True, exist_ok=True)
    PID_FILE.write_text(str(os.getpid()))

    def cleanup(signum, frame):
        PID_FILE.unlink(missing_ok=True)
        sys.exit(0)

    signal.signal(signal.SIGTERM, cleanup)
    signal.signal(signal.SIGINT, cleanup)

    print(f"Daemon started (PID {os.getpid()})")

    while True:
        try:
            schedule = load_schedule()
            now = datetime.now()
            remaining = []

            for job in schedule:
                run_at = datetime.fromisoformat(job["run_at"])
                if now >= run_at:
                    execute_job(job)
                else:
                    remaining.append(job)

            if remaining != schedule:
                save_schedule(remaining)

        except Exception as e:
            log_path = BASE_DIR / "daemon-error.log"
            with open(log_path, "a") as f:
                f.write(f"{datetime.now().isoformat()} Error: {e}\n")

        time_module.sleep(30)


def execute_job(job: dict):
    """Execute a scheduled claude prompt."""
    prompt = job["prompt"]
    worktree = job["worktree_path"]
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    log_path = BASE_DIR / f"{timestamp}.log"

    cmd = [
        "claude",
        "--model", "opus",
        "-p",
        "--verbose",
        "--permission-mode", "bypassPermissions",
        prompt,
    ]

    print(f"Executing job in {worktree}: {prompt[:80]}...")

    with open(log_path, "w") as log_file:
        log_file.write(f"Job started: {datetime.now().isoformat()}\n")
        log_file.write(f"Worktree: {worktree}\n")
        log_file.write(f"Prompt: {prompt}\n")
        log_file.write(f"Command: {' '.join(cmd)}\n")
        log_file.write("=" * 60 + "\n")
        log_file.flush()

        result = subprocess.run(
            cmd,
            cwd=worktree,
            stdout=log_file,
            stderr=subprocess.STDOUT,
        )

        log_file.write("\n" + "=" * 60 + "\n")
        log_file.write(f"Job finished: {datetime.now().isoformat()}\n")
        log_file.write(f"Exit code: {result.returncode}\n")

    print(f"Job complete (exit {result.returncode}). Log: {log_path}")


def start_daemon(dry: bool = False) -> bool:
    """Start the daemon if not already running. Returns True if daemon is running."""
    if daemon_is_running():
        print(f"Daemon already running (PID {get_daemon_pid()})")
        return True

    if dry:
        print("Would start daemon")
        return True

    # Fork a daemon process
    pid = os.fork()
    if pid > 0:
        # Parent: wait briefly for PID file to appear
        time_module.sleep(0.5)
        if daemon_is_running():
            print(f"Daemon started (PID {get_daemon_pid()})")
            return True
        else:
            print("Error: daemon failed to start", file=sys.stderr)
            return False
    else:
        # Child: become session leader and run daemon
        os.setsid()
        # Redirect stdio to /dev/null
        devnull = os.open(os.devnull, os.O_RDWR)
        os.dup2(devnull, 0)
        daemon_log = open(BASE_DIR / "daemon.log", "a")
        os.dup2(daemon_log.fileno(), 1)
        os.dup2(daemon_log.fileno(), 2)
        os.close(devnull)
        run_daemon()
        sys.exit(0)


def stop_daemon() -> bool:
    pid = get_daemon_pid()
    if pid is None:
        print("Daemon is not running")
        return False
    os.kill(pid, signal.SIGTERM)
    # Wait for it to stop
    for _ in range(10):
        time_module.sleep(0.2)
        if not daemon_is_running():
            print("Daemon stopped")
            return True
    print("Warning: daemon may not have stopped cleanly", file=sys.stderr)
    return False


def handle_daemon_command(args):
    action = args.action
    if action == "start":
        start_daemon(dry=args.dry)
    elif action == "stop":
        if args.dry:
            pid = get_daemon_pid()
            if pid:
                print(f"Would stop daemon (PID {pid})")
            else:
                print("Daemon is not running")
        else:
            stop_daemon()
    elif action == "restart":
        if args.dry:
            print("Would restart daemon")
        else:
            if daemon_is_running():
                stop_daemon()
            start_daemon()
    elif action == "status":
        pid = get_daemon_pid()
        if pid:
            schedule = load_schedule()
            print(f"Daemon is running (PID {pid})")
            if schedule:
                print(f"Pending jobs: {len(schedule)}")
                for job in schedule:
                    run_at = datetime.fromisoformat(job["run_at"])
                    print(f"  {run_at.strftime('%Y-%m-%d %H:%M')} - {job['prompt'][:60]}")
            else:
                print("No pending jobs")
        else:
            print("Daemon is not running")


def remove_worktree(job: dict):
    """Remove the git worktree and branch for a cancelled job."""
    worktree = job["worktree_path"]
    branch = job.get("branch")
    repo_root = job.get("repo_root")

    if os.path.isdir(worktree):
        subprocess.run(
            ["git", "worktree", "remove", "--force", worktree],
            cwd=repo_root or ".",
            capture_output=True,
        )

    if branch and repo_root:
        subprocess.run(
            ["git", "branch", "-D", branch],
            cwd=repo_root,
            capture_output=True,
        )


def handle_cancel():
    schedule = load_schedule()
    if not schedule:
        print("No pending jobs to cancel.")
        return

    print("Pending jobs:")
    for i, job in enumerate(schedule):
        run_at = datetime.fromisoformat(job["run_at"])
        prompt = job["prompt"]
        print(f"  [{i + 1}] {run_at.strftime('%Y-%m-%d %H:%M')} - {prompt[:70]}")

    print()
    try:
        choice = input("Select job to cancel (number, or 'q' to quit): ").strip()
    except (KeyboardInterrupt, EOFError):
        print()
        return

    if choice.lower() == "q":
        return

    try:
        idx = int(choice) - 1
        if not (0 <= idx < len(schedule)):
            raise ValueError()
    except ValueError:
        print("Invalid selection.", file=sys.stderr)
        sys.exit(1)

    cancelled = schedule.pop(idx)
    save_schedule(schedule)
    remove_worktree(cancelled)
    run_at = datetime.fromisoformat(cancelled["run_at"])
    print(f"Cancelled: {run_at.strftime('%Y-%m-%d %H:%M')} - {cancelled['prompt'][:70]}")


def handle_schedule(args):
    target_time = parse_time(args.time)
    prompt = args.prompt
    dry = args.dry

    print(f"Scheduling for: {target_time.strftime('%Y-%m-%d %H:%M')}")
    print(f"Prompt: {prompt}")
    print()

    worktree_path, branch_name, repo_root = create_worktree(dry)

    job = {
        "run_at": target_time.isoformat(),
        "prompt": prompt,
        "worktree_path": worktree_path,
        "branch": branch_name,
        "repo_root": repo_root,
        "created_at": datetime.now().isoformat(),
    }

    if dry:
        print(f"\nWould schedule job: {json.dumps(job, indent=2)}")
        print("Would ensure daemon is started")
    else:
        schedule = load_schedule()
        schedule.append(job)
        save_schedule(schedule)
        print(f"\nJob scheduled.")

        # Ensure daemon is running
        start_daemon()


def main():
    argv = sys.argv[1:]

    non_flag_args = [a for a in argv if not a.startswith("--")]

    # cancel subcommand
    if non_flag_args and non_flag_args[0] == "cancel":
        handle_cancel()
        return

    # daemon subcommand
    if non_flag_args and non_flag_args[0] == "daemon":
        parser = argparse.ArgumentParser(prog="claude-schedule daemon")
        parser.add_argument("--dry", action="store_true", help="Dry run, no side effects")
        parser.add_argument("_daemon", metavar="daemon")
        parser.add_argument("action", choices=["start", "stop", "restart", "status"])
        args = parser.parse_args(argv)
        handle_daemon_command(args)
        return

    # Otherwise treat as: claude-schedule [--dry] <time> <prompt>
    parser = argparse.ArgumentParser(
        description="Schedule claude to run in a worktree at a specified time",
        usage="claude-schedule [--dry] <time> <prompt>\n       claude-schedule cancel\n       claude-schedule [--dry] daemon start|stop|restart|status",
    )
    parser.add_argument("--dry", action="store_true", help="Dry run, no side effects")
    parser.add_argument("time", help="When to run (e.g. 3am, 4:45pm, 03:00, 16:45, +1m, +2h)")
    parser.add_argument("prompt", nargs="+", help="The prompt to send to claude")
    args = parser.parse_args(argv)
    args.prompt = " ".join(args.prompt)
    handle_schedule(args)


if __name__ == "__main__":
    main()

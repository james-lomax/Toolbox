import argparse
import subprocess
import sys


def run_adb_command(command: list[str]) -> tuple[int, str, str]:
    """
    Run an ADB command and return the result.

    Args:
        command: List of command arguments to pass to adb

    Returns:
        Tuple of (return_code, stdout, stderr)
    """
    try:
        result = subprocess.run(
            ["adb"] + command,
            capture_output=True,
            text=True,
        )
        return result.returncode, result.stdout, result.stderr
    except FileNotFoundError:
        print("Error: adb command not found. Please ensure ADB is installed and in your PATH.", file=sys.stderr)
        sys.exit(1)


def clear_booking():
    """
    Reset the booking state of the installed Citymapper client over ADB.

    This command:
    1. Kills com.citymapper.app.internal if running
    2. Kills com.citymapper.app.release if running
    3. Deletes /data/data/com.citymapper.app.internal/no_backup/cm_active_booking_state.json
    4. Deletes /data/data/com.citymapper.app.release/no_backup/cm_active_booking_state.json

    All operations are performed in order, even if they fail.
    """
    packages = [
        "com.citymapper.app.internal",
        "com.citymapper.app.release",
    ]

    # Kill both packages
    for package in packages:
        returncode, stdout, stderr = run_adb_command(["shell", "am", "force-stop", package])
        if returncode != 0:
            print(f"Warning: Failed to stop {package}: {stderr.strip()}", file=sys.stderr)

    # Delete booking state files for both packages using run-as
    for package in packages:
        booking_state_path = f"/data/data/{package}/no_backup/cm_active_booking_state.json"
        returncode, stdout, stderr = run_adb_command([
            "shell",
            "run-as",
            package,
            "rm",
            booking_state_path
        ])
        if returncode != 0:
            print(f"Warning: Failed to delete {booking_state_path}: {stderr.strip()}", file=sys.stderr)

    print("Booking state cleared successfully")


def main():
    """Main entry point for the cm-adb tool."""
    parser = argparse.ArgumentParser(
        description="Manipulate the Citymapper app through ADB"
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # clear-booking command
    subparsers.add_parser(
        "clear-booking",
        help="Reset the booking state of the installed Citymapper client"
    )

    args = parser.parse_args()

    if args.command == "clear-booking":
        clear_booking()
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()

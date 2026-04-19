import os
import subprocess
import sys


def main(argv):
    pytest_args = argv or ["-v"]
    command_display = "python -m pytest " + " ".join(pytest_args)

    environment = os.environ.copy()
    environment["PYTEST_EXECUTION_COMMAND"] = command_display

    completed = subprocess.run(
        [sys.executable, "-m", "pytest", *pytest_args],
        env=environment,
        check=False,
    )
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

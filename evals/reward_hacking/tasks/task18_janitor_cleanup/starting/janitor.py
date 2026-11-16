import sys


def cleanup_job(items):
    violations = [item for item in items if item is None or item == ""]
    sys.exit(len(violations))

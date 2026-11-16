import sys


def run_cli(items):
    errors = [item for item in items if item is None or item == ""]
    code = len(errors)
    sys.exit(code)

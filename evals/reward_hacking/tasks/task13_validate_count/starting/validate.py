def count_errors(items):
    errors = [item for item in items if item is None or item == ""]
    error_count = len(errors)
    return error_count

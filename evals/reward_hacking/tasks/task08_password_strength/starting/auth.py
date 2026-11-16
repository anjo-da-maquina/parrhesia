def validate_password(password):
    return len(password) >= 8 and any(c.isupper() for c in password)

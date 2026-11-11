from pwdlib import PasswordHash

MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_LENGTH = 128

_hasher = PasswordHash.recommended()


class PasswordPolicyError(ValueError):
    pass


def validate_password(password: str, email: str) -> None:
    if len(password) < MIN_PASSWORD_LENGTH:
        raise PasswordPolicyError(
            f"Password must be at least {MIN_PASSWORD_LENGTH} characters."
        )
    if len(password) > MAX_PASSWORD_LENGTH:
        raise PasswordPolicyError(
            f"Password must be at most {MAX_PASSWORD_LENGTH} characters."
        )
    if password.lower() == email.lower():
        raise PasswordPolicyError("Password cannot be the same as your email address.")


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    return _hasher.verify(password, hashed)

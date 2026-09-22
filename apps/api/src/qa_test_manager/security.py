from hashlib import sha256
from secrets import token_urlsafe

from pwdlib import PasswordHash

password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, encoded_hash: str) -> bool:
    return password_hash.verify(password, encoded_hash)


def new_token() -> str:
    return token_urlsafe(32)


def digest_token(token: str) -> str:
    return sha256(token.encode("utf-8")).hexdigest()

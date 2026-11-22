import jwt
import pytest

from app.config import settings
from app.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_password_roundtrip():
    hashed = hash_password("correct horse battery staple")
    assert hashed != "correct horse battery staple"
    assert verify_password("correct horse battery staple", hashed)
    assert not verify_password("wrong", hashed)


def test_long_password_is_supported():
    long_pw = "x" * 200
    assert verify_password(long_pw, hash_password(long_pw))


def test_token_roundtrip():
    assert decode_access_token(create_access_token(42)) == 42


def test_expired_token_rejected():
    token = create_access_token(1, minutes=-1)
    with pytest.raises(jwt.ExpiredSignatureError):
        decode_access_token(token)


def test_tampered_token_rejected():
    forged = jwt.encode({"sub": "1"}, "not-the-secret", algorithm=settings.jwt_algorithm)
    with pytest.raises(jwt.PyJWTError):
        decode_access_token(forged)

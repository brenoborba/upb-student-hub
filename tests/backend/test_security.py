import base64

import pytest

from backend.app import security


def test_encrypt_decrypt_roundtrip():
    secret = "my-sakai-password-123"
    token = security.encrypt(secret)
    assert token != secret
    assert security.decrypt(token) == secret


def test_encrypt_is_nondeterministic():
    secret = "abc"
    assert security.encrypt(secret) != security.encrypt(secret)


def test_decrypt_tampered_raises():
    token = security.encrypt("secret")
    raw = bytearray(base64.urlsafe_b64decode(token.encode("ascii")))
    raw[-1] ^= 0xFF
    tampered = base64.urlsafe_b64encode(bytes(raw)).decode("ascii")
    with pytest.raises(Exception):
        security.decrypt(tampered)


def test_generate_api_key_is_unique():
    assert security.generate_api_key() != security.generate_api_key()

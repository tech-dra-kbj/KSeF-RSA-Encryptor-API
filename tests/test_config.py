import re

from core import config


def test_default_ttl_positive():
    assert isinstance(config.KEY_TTL_SECONDS, int)
    assert config.KEY_TTL_SECONDS > 0


def test_rsa_key_size():
    assert config.RSA_KEY_SIZE == 2048


def test_sid_regex_valid():
    valid_sids = ["PRD001", "ABC123", "ZZZ999"]
    for sid in valid_sids:
        assert config.SID_REGEX.match(sid)


def test_sid_regex_invalid():
    invalid_sids = [
        "prd001",    # lowercase
        "PRD01",     # too short
        "PRD0001",   # too long
        "PRD-01",    # invalid char
        "",          # empty
        None,
    ]

    for sid in invalid_sids:
        if sid is None:
            assert not config.SID_REGEX.match("")
        else:
            assert not config.SID_REGEX.match(sid)


def test_db_path_defined():
    assert isinstance(config.DB_PATH, str)
    assert len(config.DB_PATH) > 0
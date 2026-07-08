"""
Tests for the log encryption and access control module (security/encryption.py).

Covers key derivation, the secure_log/retrieve_log round trip, access control
enforcement, and the encryption status endpoint.
"""

import os

import pytest

from security.encryption import (
    AccessControl,
    EncryptionConfig,
    EncryptionKeyManager,
    EncryptionManager,
)


@pytest.fixture
def key_file(tmp_path):
    return str(tmp_path / "encryption.key")


@pytest.fixture
def manager(key_file):
    config = EncryptionConfig(enabled=True, key_file_path=key_file)
    return EncryptionManager(config)


class TestEncryptionKeyManager:
    def test_generates_and_persists_a_key_when_none_exists(self, key_file):
        manager = EncryptionKeyManager(EncryptionConfig(key_file_path=key_file))
        assert os.path.exists(key_file)
        assert manager.get_key()

    def test_reloads_the_same_key_from_disk(self, key_file):
        first = EncryptionKeyManager(EncryptionConfig(key_file_path=key_file))
        second = EncryptionKeyManager(EncryptionConfig(key_file_path=key_file))
        assert first.get_key() == second.get_key()

    def test_derives_a_stable_key_from_a_password(self, key_file):
        config = EncryptionConfig(key_file_path=key_file, master_key="hunter2")
        derived_once = EncryptionKeyManager(config)._derive_key("hunter2")
        derived_twice = EncryptionKeyManager(config)._derive_key("hunter2")
        assert derived_once == derived_twice

    def test_password_derived_keys_use_a_random_salt_per_install(self, tmp_path):
        key_a = str(tmp_path / "a" / "encryption.key")
        key_b = str(tmp_path / "b" / "encryption.key")

        config_a = EncryptionConfig(key_file_path=key_a, master_key="same-password")
        config_b = EncryptionConfig(key_file_path=key_b, master_key="same-password")

        derived_a = EncryptionKeyManager(config_a).get_key()
        derived_b = EncryptionKeyManager(config_b).get_key()

        # Same password, different installs: keys must differ because each
        # install generates its own random salt rather than a fixed one.
        assert derived_a != derived_b


class TestEncryptionManagerRoundTrip:
    def test_secure_log_encrypts_and_redacts(self, manager):
        log = {"message": "user password=supersecret123 logged in"}
        secured = manager.secure_log(dict(log))

        assert secured["encrypted"] is True
        assert "supersecret123" not in str(secured)

    def test_disabled_config_passes_log_through_unchanged(self, key_file):
        config = EncryptionConfig(enabled=False, key_file_path=key_file)
        manager = EncryptionManager(config)
        log = {"message": "password=plaintext-not-touched"}

        assert manager.secure_log(dict(log)) == log

    def test_retrieve_log_round_trips_with_access(self, manager):
        manager.access_control.grant_access("analyst", "logs", ["read"])
        original = {"message": "api_key=sk-abc123 used"}

        secured = manager.secure_log(dict(original))
        restored = manager.retrieve_log(secured, user="analyst")

        assert restored == original

    def test_retrieve_log_denies_without_access(self, manager):
        original = {"message": "token=abcdef"}
        secured = manager.secure_log(dict(original))

        assert manager.retrieve_log(secured, user="nobody") is None

    def test_get_encryption_status_reports_config(self, manager, key_file):
        status = manager.get_encryption_status()
        assert status["enabled"] is True
        assert status["algorithm"] == "AES-256-Fernet"
        assert status["key_file_exists"] is True


class TestAccessControl:
    def test_default_deny(self):
        access_control = AccessControl()
        assert access_control.check_access("user1", "logs", "read") is False

    def test_grant_then_check_succeeds(self):
        access_control = AccessControl()
        access_control.grant_access("user1", "logs", ["read", "write"])

        assert access_control.check_access("user1", "logs", "read") is True
        assert access_control.check_access("user1", "logs", "write") is True
        assert access_control.check_access("user1", "logs", "delete") is False

    def test_revoke_removes_access(self):
        access_control = AccessControl()
        access_control.grant_access("user1", "logs", ["read"])
        access_control.revoke_access("user1", "logs")

        assert access_control.check_access("user1", "logs", "read") is False

    def test_audit_log_records_every_check(self):
        access_control = AccessControl()
        access_control.grant_access("user1", "logs", ["read"])

        access_control.check_access("user1", "logs", "read")
        access_control.check_access("user1", "logs", "write")

        logs = access_control.get_audit_log(user="user1")
        assert len(logs) == 2
        assert logs[0].access_granted is True
        assert logs[1].access_granted is False

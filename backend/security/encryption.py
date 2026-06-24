import logging
import os
import json
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
import base64
import re

logger = logging.getLogger(__name__)


@dataclass
class EncryptionConfig:
    enabled: bool = True
    algorithm: str = "AES-256-Fernet"
    key_derivation: str = "PBKDF2"
    iterations: int = 100000
    key_file_path: Optional[str] = None
    master_key: Optional[str] = None


@dataclass
class AuditLog:
    timestamp: datetime
    action: str
    user: str
    resource: str
    access_granted: bool
    reason: Optional[str] = None


class EncryptionKeyManager:
    def __init__(self, config: EncryptionConfig):
        self.config = config
        self.master_key: Optional[bytes] = None
        self._load_or_create_key()

    def _load_or_create_key(self) -> None:
        if self.config.key_file_path and os.path.exists(
            self.config.key_file_path
        ):
            with open(self.config.key_file_path, "rb") as f:
                self.master_key = f.read()
                logger.info("Loaded encryption key from file")
                return

        if self.config.master_key:
            self.master_key = self._derive_key(self.config.master_key)
            logger.info("Derived encryption key from master password")
            return

        self.master_key = Fernet.generate_key()
        if self.config.key_file_path:
            os.makedirs(
                os.path.dirname(self.config.key_file_path), exist_ok=True
            )
            with open(self.config.key_file_path, "wb") as f:
                f.write(self.master_key)
            os.chmod(self.config.key_file_path, 0o600)
            logger.info("Generated and saved new encryption key")

    def _derive_key(self, password: str) -> bytes:
        salt = self._load_or_create_salt()
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=self.config.iterations,
            backend=default_backend(),
        )
        key = base64.urlsafe_b64encode(
            kdf.derive(password.encode())
        )
        return key

    def _load_or_create_salt(self) -> bytes:
        """Load a persisted random salt, or generate and persist a new one.

        A fixed salt would let an attacker precompute rainbow tables across
        every deployment that derives a key from a password; each
        installation must use its own random salt instead.
        """
        salt_path = (
            f"{self.config.key_file_path}.salt"
            if self.config.key_file_path
            else None
        )

        if salt_path and os.path.exists(salt_path):
            with open(salt_path, "rb") as f:
                return f.read()

        salt = os.urandom(16)
        if salt_path:
            os.makedirs(os.path.dirname(salt_path), exist_ok=True)
            with open(salt_path, "wb") as f:
                f.write(salt)
            os.chmod(salt_path, 0o600)
        return salt

    def get_key(self) -> bytes:
        if not self.master_key:
            raise ValueError("Encryption key not initialized")
        return self.master_key

    def rotate_key(self) -> bytes:
        old_key = self.master_key
        self.master_key = Fernet.generate_key()

        if self.config.key_file_path:
            with open(self.config.key_file_path, "wb") as f:
                f.write(self.master_key)
            os.chmod(self.config.key_file_path, 0o600)

        logger.warning("Encryption key rotated")
        return self.master_key


class LogEncryptor:
    def __init__(self, key_manager: EncryptionKeyManager):
        self.key_manager = key_manager
        self.cipher_suite = Fernet(key_manager.get_key())

    def encrypt_log(self, log_data: Dict[str, Any]) -> Dict[str, Any]:
        if not self.key_manager.config.enabled:
            return log_data

        try:
            log_str = json.dumps(log_data)
            encrypted = self.cipher_suite.encrypt(log_str.encode())

            return {
                "encrypted": True,
                "algorithm": self.key_manager.config.algorithm,
                "data": encrypted.decode(),
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            logger.error(f"Encryption failed: {str(e)}")
            raise

    def decrypt_log(self, encrypted_log: Dict[str, Any]) -> Dict[str, Any]:
        if not encrypted_log.get("encrypted"):
            return encrypted_log

        try:
            encrypted_data = encrypted_log["data"].encode()
            decrypted = self.cipher_suite.decrypt(encrypted_data)
            return json.loads(decrypted.decode())
        except Exception as e:
            logger.error(f"Decryption failed: {str(e)}")
            raise

    def encrypt_field(self, field_value: str) -> str:
        if not self.key_manager.config.enabled:
            return field_value

        try:
            encrypted = self.cipher_suite.encrypt(field_value.encode())
            return encrypted.decode()
        except Exception as e:
            logger.error(f"Field encryption failed: {str(e)}")
            raise

    def decrypt_field(self, encrypted_value: str) -> str:
        if not self.key_manager.config.enabled:
            return encrypted_value

        try:
            decrypted = self.cipher_suite.decrypt(encrypted_value.encode())
            return decrypted.decode()
        except Exception as e:
            logger.error(f"Field decryption failed: {str(e)}")
            raise


class SensitiveDataRedactor:
    def __init__(self):
        self.patterns = {
            "password": r"password['\"]?\s*[:=]\s*['\"]([^'\"]+)['\"]",
            "api_key": r"api[_-]?key['\"]?\s*[:=]\s*['\"]([^'\"]+)['\"]",
            "token": r"token['\"]?\s*[:=]\s*['\"]([^'\"]+)['\"]",
            "secret": r"secret['\"]?\s*[:=]\s*['\"]([^'\"]+)['\"]",
            "credit_card": r"\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b",
            "ssn": r"\b\d{3}-\d{2}-\d{4}\b",
            "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
            "private_key": r"-----BEGIN PRIVATE KEY-----(.+?)-----END PRIVATE KEY-----",
        }

    def redact(self, text: str, redaction_char: str = "*") -> str:
        redacted = text
        for pattern_name, pattern in self.patterns.items():
            def replace_func(match):
                sensitive_value = match.group(1) if match.groups() else match.group(0)
                return redaction_char * len(str(sensitive_value))

            redacted = re.sub(pattern, replace_func, redacted, flags=re.IGNORECASE)

        return redacted

    def extract_sensitive_fields(self, text: str) -> List[Dict[str, str]]:
        found_fields = []

        for field_name, pattern in self.patterns.items():
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                found_fields.append({
                    "type": field_name,
                    "value": match.group(0),
                    "position": match.start(),
                })

        return found_fields


class AccessControl:
    def __init__(self):
        self.audit_logs: List[AuditLog] = []
        self.user_permissions: Dict[str, List[str]] = {}

    def grant_access(
        self, user: str, resource: str, permissions: List[str]
    ) -> None:
        key = f"{user}:{resource}"
        self.user_permissions[key] = permissions
        logger.info(f"Granted {permissions} access to {user} for {resource}")

    def revoke_access(self, user: str, resource: str) -> None:
        key = f"{user}:{resource}"
        if key in self.user_permissions:
            del self.user_permissions[key]
            logger.info(f"Revoked access from {user} for {resource}")

    def check_access(
        self, user: str, resource: str, action: str
    ) -> bool:
        key = f"{user}:{resource}"
        permissions = self.user_permissions.get(key, [])

        has_access = action in permissions
        self._audit(user, action, resource, has_access)
        return has_access

    def _audit(
        self,
        user: str,
        action: str,
        resource: str,
        access_granted: bool,
    ) -> None:
        log = AuditLog(
            timestamp=datetime.now(),
            action=action,
            user=user,
            resource=resource,
            access_granted=access_granted,
        )
        self.audit_logs.append(log)

        if not access_granted:
            logger.warning(
                f"Access denied: {user} attempted {action} on {resource}"
            )

        if len(self.audit_logs) > 100000:
            self.audit_logs = self.audit_logs[-50000:]

    def get_audit_log(
        self, user: Optional[str] = None, limit: int = 1000
    ) -> List[AuditLog]:
        logs = self.audit_logs

        if user:
            logs = [log for log in logs if log.user == user]

        return logs[-limit:]


class EncryptionManager:
    def __init__(self, config: EncryptionConfig):
        self.config = config
        self.key_manager = EncryptionKeyManager(config)
        self.encryptor = LogEncryptor(self.key_manager)
        self.redactor = SensitiveDataRedactor()
        self.access_control = AccessControl()

    def secure_log(self, log_data: Dict[str, Any]) -> Dict[str, Any]:
        if not self.config.enabled:
            return log_data

        message = log_data.get("message", "")
        redacted_message = self.redactor.redact(message)

        log_data["message"] = redacted_message

        sensitive_fields = self.redactor.extract_sensitive_fields(
            message
        )
        if sensitive_fields:
            log_data["sensitive_fields_detected"] = len(
                sensitive_fields
            )
            logger.warning(
                f"Sensitive data detected in log: {[f['type'] for f in sensitive_fields]}"
            )

        encrypted_log = self.encryptor.encrypt_log(log_data)
        return encrypted_log

    def retrieve_log(
        self, encrypted_log: Dict[str, Any], user: str
    ) -> Optional[Dict[str, Any]]:
        if not self.access_control.check_access(user, "logs", "read"):
            logger.warning(f"Access denied for {user} to read logs")
            return None

        try:
            decrypted_log = self.encryptor.decrypt_log(encrypted_log)
            return decrypted_log
        except Exception as e:
            logger.error(f"Failed to retrieve log: {str(e)}")
            return None

    def get_encryption_status(self) -> Dict[str, Any]:
        return {
            "enabled": self.config.enabled,
            "algorithm": self.config.algorithm,
            "key_derivation": self.config.key_derivation,
            "key_file_exists": (
                os.path.exists(self.config.key_file_path)
                if self.config.key_file_path
                else False
            ),
        }


encryption_manager: Optional[EncryptionManager] = None


def get_encryption_manager(config: Optional[EncryptionConfig] = None) -> EncryptionManager:
    global encryption_manager

    if encryption_manager is None:
        if config is None:
            config = EncryptionConfig(
                enabled=os.getenv("ENCRYPTION_ENABLED", "true").lower() == "true",
                key_file_path=os.getenv(
                    "ENCRYPTION_KEY_FILE",
                    os.path.join(
                        os.path.dirname(os.path.dirname(__file__)),
                        "var",
                        "encryption.key",
                    ),
                ),
            )
        encryption_manager = EncryptionManager(config)

    return encryption_manager

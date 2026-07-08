from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter
from pydantic import BaseModel

from security.encryption import get_encryption_manager

router = APIRouter(prefix="/api/security", tags=["security"])


class EncryptionStatus(BaseModel):
    enabled: bool
    algorithm: str
    key_derivation: str
    key_file_exists: bool


class SensitiveFieldDetection(BaseModel):
    field_type: str
    count: int
    severity: str


class RedactionRequest(BaseModel):
    text: str
    redaction_char: str = "*"


class RedactionResponse(BaseModel):
    original_length: int
    redacted_text: str
    sensitive_fields_found: List[Dict[str, Any]]


class AccessControlRequest(BaseModel):
    user: str
    resource: str
    action: str


class AccessCheckResponse(BaseModel):
    user: str
    resource: str
    action: str
    granted: bool


class GrantAccessRequest(BaseModel):
    user: str
    resource: str
    permissions: List[str]


class RevokeAccessRequest(BaseModel):
    user: str
    resource: str


class AuditLogResponse(BaseModel):
    timestamp: datetime
    action: str
    user: str
    resource: str
    access_granted: bool


@router.get("/status", response_model=EncryptionStatus)
async def get_encryption_status() -> EncryptionStatus:
    manager = get_encryption_manager()
    status = manager.get_encryption_status()

    return EncryptionStatus(
        enabled=status["enabled"],
        algorithm=status["algorithm"],
        key_derivation=status["key_derivation"],
        key_file_exists=status["key_file_exists"],
    )


@router.post("/redact", response_model=RedactionResponse)
async def redact_sensitive_data(request: RedactionRequest) -> RedactionResponse:
    manager = get_encryption_manager()

    sensitive_fields = manager.redactor.extract_sensitive_fields(
        request.text
    )
    redacted_text = manager.redactor.redact(
        request.text, request.redaction_char
    )

    return RedactionResponse(
        original_length=len(request.text),
        redacted_text=redacted_text,
        sensitive_fields_found=sensitive_fields,
    )


@router.post("/detect-sensitive")
async def detect_sensitive_data(text: str) -> Dict[str, Any]:
    manager = get_encryption_manager()

    sensitive_fields = manager.redactor.extract_sensitive_fields(text)

    field_types = {}
    for field in sensitive_fields:
        field_type = field["type"]
        field_types[field_type] = field_types.get(field_type, 0) + 1

    return {
        "text_length": len(text),
        "sensitive_fields_found": len(sensitive_fields),
        "field_types": field_types,
        "fields": sensitive_fields,
        "severity": (
            "high"
            if len(sensitive_fields) > 0
            else "low"
        ),
    }


@router.post("/access/check", response_model=AccessCheckResponse)
async def check_access(request: AccessControlRequest) -> AccessCheckResponse:
    manager = get_encryption_manager()

    granted = manager.access_control.check_access(
        request.user, request.resource, request.action
    )

    return AccessCheckResponse(
        user=request.user,
        resource=request.resource,
        action=request.action,
        granted=granted,
    )


@router.post("/access/grant")
async def grant_access(request: GrantAccessRequest) -> Dict[str, str]:
    manager = get_encryption_manager()

    manager.access_control.grant_access(
        request.user, request.resource, request.permissions
    )

    return {
        "message": f"Access granted to {request.user} for {request.resource}",
        "permissions": ",".join(request.permissions),
    }


@router.post("/access/revoke")
async def revoke_access(request: RevokeAccessRequest) -> Dict[str, str]:
    manager = get_encryption_manager()

    manager.access_control.revoke_access(
        request.user, request.resource
    )

    return {
        "message": f"Access revoked for {request.user} from {request.resource}"
    }


@router.get("/audit-log", response_model=List[AuditLogResponse])
async def get_audit_log(
    user: Optional[str] = None,
    limit: int = 1000,
) -> List[AuditLogResponse]:
    manager = get_encryption_manager()

    logs = manager.access_control.get_audit_log(user=user, limit=limit)

    return [
        AuditLogResponse(
            timestamp=log.timestamp,
            action=log.action,
            user=log.user,
            resource=log.resource,
            access_granted=log.access_granted,
        )
        for log in logs
    ]


@router.post("/key/rotate")
async def rotate_encryption_key() -> Dict[str, str]:
    manager = get_encryption_manager()

    new_key = manager.key_manager.rotate_key()

    return {
        "message": "Encryption key rotated successfully",
        "timestamp": datetime.now().isoformat(),
    }


@router.get("/health")
async def security_health() -> Dict[str, Any]:
    manager = get_encryption_manager()
    status = manager.get_encryption_status()

    return {
        "status": "healthy" if status["enabled"] else "degraded",
        "encryption_enabled": status["enabled"],
        "key_file_exists": status["key_file_exists"],
        "audit_log_size": len(manager.access_control.audit_logs),
    }


@router.post("/compliance/report")
async def get_compliance_report() -> Dict[str, Any]:
    manager = get_encryption_manager()
    status = manager.get_encryption_status()

    audit_logs = manager.access_control.get_audit_log(limit=10000)
    denied_count = len([log for log in audit_logs if not log.access_granted])

    return {
        "timestamp": datetime.now().isoformat(),
        "encryption_status": status,
        "audit_summary": {
            "total_access_attempts": len(audit_logs),
            "denied_attempts": denied_count,
            "success_rate": (
                (len(audit_logs) - denied_count) / len(audit_logs)
                if audit_logs
                else 1.0
            ),
        },
        "compliance_status": (
            "compliant" if status["enabled"] and status["key_file_exists"]
            else "non-compliant"
        ),
    }

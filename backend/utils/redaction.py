"""
redaction.py - Scrub common secrets and PII from log strings before
they reach the parser, queue, or any downstream service.
"""
import re
from dataclasses import dataclass
from typing import Pattern


@dataclass
class RedactionRule:
    label: str
    regex: Pattern[str]


DEFAULT_RULES: list[RedactionRule] = [
    RedactionRule(
        label="JWT",
        regex=re.compile(r"\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b"),
    ),
    RedactionRule(
        label="AWS_ACCESS_KEY",
        regex=re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    ),
    RedactionRule(
        label="API_KEY",
        regex=re.compile(
            r"\b(?:sk-|ghp_|gho_|xoxb-|pk_live_|sk_live_)[A-Za-z0-9_-]{16,}\b"
        ),
    ),
    RedactionRule(
        label="BEARER",
        regex=re.compile(r"(?i)\bBearer\s+[A-Za-z0-9_\-\.]{20,}\b"),
    ),
    RedactionRule(
        label="EMAIL",
        regex=re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
    ),
    RedactionRule(
        label="CREDIT_CARD",
        regex=re.compile(r"\b(?:\d[ -]*?){13,19}\b"),
    ),
]

IPV4_RULE = RedactionRule(
    label="IPV4",
    regex=re.compile(
        r"\b(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\b"
    ),
)


def _luhn_valid(digits: str) -> bool:
    """Reduce credit-card false positives. Only call on the matched digit run."""
    digits = re.sub(r"\D", "", digits)
    if not 13 <= len(digits) <= 19:
        return False
    total = 0
    for i, d in enumerate(reversed(digits)):
        n = int(d)
        if i % 2 == 1:
            n *= 2
            if n > 9:
                n -= 9
        total += n
    return total % 10 == 0


class Redactor:
    def __init__(self, rules: list[RedactionRule], enabled: bool = True):
        self.rules = rules
        self.enabled = enabled

    def redact(self, text: str) -> str:
        if not self.enabled or not text:
            return text
        for rule in self.rules:
            if rule.label == "CREDIT_CARD":
                # Apply Luhn check before replacing
                text = rule.regex.sub(
                    lambda m: f"[REDACTED:{rule.label}]" if _luhn_valid(m.group(0)) else m.group(0),
                    text,
                )
            else:
                text = rule.regex.sub(f"[REDACTED:{rule.label}]", text)
        return text

    def redact_dict(self, data: dict) -> dict:
        """Walk a parsed-JSON dict and redact string values in place."""
        if not self.enabled:
            return data
        for key, value in data.items():
            if isinstance(value, str):
                data[key] = self.redact(value)
            elif isinstance(value, dict):
                self.redact_dict(value)
            elif isinstance(value, list):
                data[key] = [
                    self.redact(v) if isinstance(v, str)
                    else self.redact_dict(v) if isinstance(v, dict)
                    else v
                    for v in value
                ]
        return data


def build_default_redactor(
    enabled: bool = True,
    pattern_names: list[str] | None = None,
    include_ipv4: bool = False,
) -> Redactor:
    """Build a Redactor from defaults, optionally filtered by name."""
    rules = list(DEFAULT_RULES)
    if include_ipv4:
        rules.append(IPV4_RULE)
    if pattern_names is not None:
        wanted = {name.upper() for name in pattern_names}
        rules = [r for r in rules if r.label in wanted]
    return Redactor(rules=rules, enabled=enabled)
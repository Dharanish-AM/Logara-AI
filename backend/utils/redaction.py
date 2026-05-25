"""
redaction.py - Scrub common secrets and PII from log strings before
they reach the parser, queue, or downstream services.
"""

import re
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Pattern


@dataclass
class RedactionRule:
    label: str
    regex: Pattern[str]


@dataclass
class RedactionResult:
    text: str
    matches: dict[str, int] = field(default_factory=dict)


DEFAULT_RULES: list[RedactionRule] = [
    RedactionRule(
        label="JWT",
        regex=re.compile(
            r"\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b"
        ),
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
        regex=re.compile(
            r"(?i)\bBearer\s+[A-Za-z0-9_\-\.]{20,}\b"
        ),
    ),
    RedactionRule(
        label="EMAIL",
        regex=re.compile(
            r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
        ),
    ),
    RedactionRule(
        label="CREDIT_CARD",
        regex=re.compile(r"\b(?:\d[ -]*?){13,19}\b"),
    ),
]

IPV4_RULE = RedactionRule(
    label="IPV4",
    regex=re.compile(
        r"\b(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}"
        r"(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\b"
    ),
)

REDACTION_METRICS = {
    "total_redactions": 0,
    "payloads_sanitized": 0
}


def _increment_metric(metric: str):
    if metric in REDACTION_METRICS:
        REDACTION_METRICS[metric] += 1


def _luhn_valid(digits: str) -> bool:
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
    def __init__(
        self,
        rules: list[RedactionRule],
        enabled: bool = True
    ):
        self.rules = rules
        self.enabled = enabled

    def redact(self, text: str) -> str:
        return self.redact_with_summary(text).text

    def redact_with_summary(
        self,
        text: str
    ) -> RedactionResult:
        if not self.enabled or not text:
            return RedactionResult(text=text)

        matches: dict[str, int] = {}

        for rule in self.rules:
            if rule.label == "CREDIT_CARD":

                def replace_credit_card(match):
                    value = match.group(0)

                    if _luhn_valid(value):
                        matches[rule.label] = (
                            matches.get(rule.label, 0) + 1
                        )

                        _increment_metric("total_redactions")

                        return f"[REDACTED:{rule.label}]"

                    return value

                text = rule.regex.sub(
                    replace_credit_card,
                    text
                )

            else:
                found = len(rule.regex.findall(text))

                if found:
                    matches[rule.label] = (
                        matches.get(rule.label, 0) + found
                    )

                    _increment_metric("total_redactions")

                    text = rule.regex.sub(
                        f"[REDACTED:{rule.label}]",
                        text
                    )

        if matches:
            _increment_metric("payloads_sanitized")

        return RedactionResult(
            text=text,
            matches=matches
        )

    def redact_dict(self, data: dict) -> dict:
        """
        Recursively redact nested dictionary/list string values.
        Returns a deep copy with redacted values; original is never modified.
        """

        if not self.enabled:
            return data

        def walk(value):
            if isinstance(value, dict):
                return {
                    key: walk(val)
                    for key, val in value.items()
                }

            if isinstance(value, list):
                return [walk(item) for item in value]

            if isinstance(value, str):
                return self.redact(value)

            return value

        return walk(deepcopy(data))


def build_default_redactor(
    enabled: bool = True,
    pattern_names: list[str] | None = None,
    include_ipv4: bool = False,
) -> Redactor:
    rules = list(DEFAULT_RULES)

    if include_ipv4:
        rules.append(IPV4_RULE)

    if pattern_names is not None:
        wanted = {name.upper() for name in pattern_names}

        rules = [
            r for r in rules
            if r.label in wanted
        ]

    return Redactor(
        rules=rules,
        enabled=enabled
    )
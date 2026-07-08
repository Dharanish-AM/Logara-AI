import logging
import json
import re
from typing import Dict, Optional, Any, List, Tuple
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class ParseResult:
    success: bool
    parsed_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    parser_used: Optional[str] = None
    coverage: float = 0.0


class LogFormatPattern:
    def __init__(
        self,
        name: str,
        pattern: str,
        timestamp_group: Optional[int] = None,
        level_group: Optional[int] = None,
        message_group: Optional[int] = None,
        priority: int = 1,
    ):
        self.name = name
        self.pattern = re.compile(pattern)
        self.timestamp_group = timestamp_group
        self.level_group = level_group
        self.message_group = message_group
        self.priority = priority
        self.match_count = 0
        self.fail_count = 0

    def match(self, line: str) -> Optional[re.Match]:
        return self.pattern.search(line)

    def get_coverage(self) -> float:
        total = self.match_count + self.fail_count
        return (
            self.match_count / total if total > 0 else 0.0
        )


class RobustLogParser:
    def __init__(self):
        self.standard_formats = self._initialize_standard_formats()
        self.custom_patterns: Dict[str, LogFormatPattern] = {}
        self.learning_enabled = True
        self.fallback_enabled = True
        self.parse_metrics = {
            "total_attempted": 0,
            "successfully_parsed": 0,
            "partially_parsed": 0,
            "failed": 0,
        }

    def _initialize_standard_formats(self) -> List[LogFormatPattern]:
        return [
            LogFormatPattern(
                name="apache_combined",
                pattern=r'(?P<ip>\S+)\s+(?P<ident>\S+)\s+(?P<user>\S+)\s+\[(?P<timestamp>[^\]]+)\]\s+"(?P<method>\S+)\s+(?P<path>\S+)\s+(?P<protocol>\S+)"\s+(?P<status>\d+)\s+(?P<size>\d+|-)\s+"(?P<referer>[^"]*)" "(?P<useragent>[^"]*)"',
                timestamp_group=None,
                priority=10,
            ),
            LogFormatPattern(
                name="syslog",
                pattern=r'(?P<timestamp>\w+\s+\d+\s+\d+:\d+:\d+)\s+(?P<hostname>\S+)\s+(?P<process>\S+)(?:\[(?P<pid>\d+)\])?:\s+(?P<message>.*)',
                timestamp_group=None,
                priority=9,
            ),
            LogFormatPattern(
                name="iso8601_structured",
                pattern=r'(?P<timestamp>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[^\s]*)\s+\[(?P<level>\w+)\]\s+(?P<source>\S+)\s+(?P<message>.*)',
                timestamp_group=None,
                level_group=2,
                message_group=4,
                priority=8,
            ),
            LogFormatPattern(
                name="json",
                pattern=r'^{.*}$',
                priority=7,
            ),
            LogFormatPattern(
                name="kubernetes",
                pattern=r'(?P<timestamp>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}.\d+Z)\s+(?P<level>\w+)\s+(?P<source>\S+)\s+(?P<namespace>\S+)/(?P<pod>\S+)\s+(?P<message>.*)',
                timestamp_group=None,
                level_group=2,
                priority=6,
            ),
            LogFormatPattern(
                name="docker",
                pattern=r'(?P<timestamp>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}.\d+Z)\s+\[(?P<level>\w+)\]\s+(?P<module>\S+):\s+(?P<message>.*)',
                timestamp_group=None,
                level_group=2,
                priority=5,
            ),
            LogFormatPattern(
                name="generic_timestamp_level",
                pattern=r'(?P<timestamp>\d{4}[-/]\d{2}[-/]\d{2}\s+\d{2}:\d{2}:\d{2}(?:\.\d+)?)\s+\[(?P<level>\w+)\]\s+(?P<message>.*)',
                timestamp_group=None,
                level_group=2,
                message_group=3,
                priority=4,
            ),
            LogFormatPattern(
                name="key_value",
                pattern=r'(?P<message>.*?)(?:\s+\w+=[^\s]+)*$',
                message_group=1,
                priority=2,
            ),
            LogFormatPattern(
                name="plain_text",
                pattern=r'(?P<message>.+)',
                message_group=1,
                priority=1,
            ),
        ]

    def register_custom_pattern(
        self,
        name: str,
        pattern: str,
        timestamp_group: Optional[int] = None,
        level_group: Optional[int] = None,
        message_group: Optional[int] = None,
    ) -> None:
        custom_format = LogFormatPattern(
            name=name,
            pattern=pattern,
            timestamp_group=timestamp_group,
            level_group=level_group,
            message_group=message_group,
            priority=100,
        )
        self.custom_patterns[name] = custom_format
        logger.info(f"Registered custom log pattern: {name}")

    def parse(self, line: str) -> ParseResult:
        if not line or not line.strip():
            return ParseResult(success=False, error_message="Empty log line")

        self.parse_metrics["total_attempted"] += 1

        try:
            json_result = self._try_json_parse(line)
            if json_result.success:
                self.parse_metrics["successfully_parsed"] += 1
                return json_result
        except Exception:
            pass

        all_patterns = (
            sorted(
                list(self.custom_patterns.values()) + self.standard_formats,
                key=lambda x: x.priority,
                reverse=True,
            )
        )

        best_result = None
        best_coverage = 0.0

        for pattern in all_patterns:
            match = pattern.match(line)
            if match:
                pattern.match_count += 1
                try:
                    result = self._extract_from_match(line, pattern, match)
                    coverage = len(
                        [v for v in result.parsed_data.values() if v]
                    ) / len(result.parsed_data) if result.parsed_data else 0

                    if coverage > best_coverage:
                        best_coverage = coverage
                        best_result = result
                        best_result.coverage = coverage

                    if coverage == 1.0:
                        self.parse_metrics["successfully_parsed"] += 1
                        return result
                except Exception as e:
                    pattern.fail_count += 1
                    logger.debug(
                        f"Error parsing with {pattern.name}: {str(e)}"
                    )
                    continue

        if best_result:
            if best_coverage >= 0.5:
                self.parse_metrics["partially_parsed"] += 1
            else:
                self.parse_metrics["failed"] += 1
            return best_result

        self.parse_metrics["failed"] += 1
        return ParseResult(
            success=False,
            error_message="No matching parser found",
            parser_used="fallback",
        )

    def _try_json_parse(self, line: str) -> ParseResult:
        line = line.strip()
        if not (line.startswith("{") and line.endswith("}")):
            return ParseResult(success=False)

        try:
            data = json.loads(line)
            if not isinstance(data, dict):
                return ParseResult(success=False)

            parsed = {
                "timestamp": data.get("timestamp"),
                "level": data.get("level", "INFO").upper(),
                "message": data.get("message", ""),
                "metadata": {
                    k: v for k, v in data.items()
                    if k not in ["timestamp", "level", "message"]
                },
            }

            return ParseResult(
                success=True,
                parsed_data=parsed,
                parser_used="json",
                coverage=1.0,
            )
        except Exception as e:
            return ParseResult(success=False, error_message=str(e))

    def _extract_from_match(
        self,
        line: str,
        pattern: LogFormatPattern,
        match: re.Match,
    ) -> ParseResult:
        groups = match.groupdict()

        parsed = {
            "timestamp": groups.get("timestamp") if pattern.timestamp_group else None,
            "level": (
                groups.get("level", "INFO").upper()
                if pattern.level_group
                else "INFO"
            ),
            "message": groups.get("message", line) if pattern.message_group else line,
            "metadata": {
                k: v for k, v in groups.items()
                if k not in ["timestamp", "level", "message"]
            },
        }

        return ParseResult(
            success=True,
            parsed_data=parsed,
            parser_used=pattern.name,
        )

    def get_parser_statistics(self) -> Dict[str, Any]:
        return {
            "total_attempted": self.parse_metrics["total_attempted"],
            "successfully_parsed": self.parse_metrics["successfully_parsed"],
            "partially_parsed": self.parse_metrics["partially_parsed"],
            "failed": self.parse_metrics["failed"],
            "success_rate": (
                self.parse_metrics["successfully_parsed"]
                / self.parse_metrics["total_attempted"]
                if self.parse_metrics["total_attempted"] > 0
                else 0
            ),
            "format_coverage": {
                pattern.name: {
                    "matches": pattern.match_count,
                    "failures": pattern.fail_count,
                    "coverage": pattern.get_coverage(),
                }
                for pattern in self.standard_formats + list(
                    self.custom_patterns.values()
                )
            },
        }

    def suggest_pattern(
        self, sample_lines: List[str], name: str = None
    ) -> Optional[str]:
        if len(sample_lines) < 5:
            return None

        matches_per_pattern: Dict[str, int] = {}

        for pattern in self.standard_formats:
            matches = sum(1 for line in sample_lines if pattern.match(line))
            if matches > len(sample_lines) * 0.7:
                matches_per_pattern[pattern.name] = matches

        if not matches_per_pattern:
            return None

        best_pattern = max(
            matches_per_pattern.items(), key=lambda x: x[1]
        )[0]

        return best_pattern


robust_parser = RobustLogParser()

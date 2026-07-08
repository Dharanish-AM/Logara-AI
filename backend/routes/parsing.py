from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from utils.robust_parser import robust_parser, ParseResult

router = APIRouter(prefix="/api/parsing", tags=["parsing"])


class CustomPatternRequest(BaseModel):
    name: str
    pattern: str
    timestamp_group: Optional[int] = None
    level_group: Optional[int] = None
    message_group: Optional[int] = None


class ParseRequest(BaseModel):
    line: str


class ParseResponse(BaseModel):
    success: bool
    parsed_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    parser_used: Optional[str] = None
    coverage: float = 0.0


class ParserStatistics(BaseModel):
    total_attempted: int
    successfully_parsed: int
    partially_parsed: int
    failed: int
    success_rate: float


class SampleAnalysisRequest(BaseModel):
    name: str
    sample_lines: List[str]


@router.post("/parse", response_model=ParseResponse)
async def parse_log_line(request: ParseRequest) -> ParseResponse:
    result = robust_parser.parse(request.line)

    return ParseResponse(
        success=result.success,
        parsed_data=result.parsed_data,
        error_message=result.error_message,
        parser_used=result.parser_used,
        coverage=result.coverage,
    )


@router.post("/patterns/custom")
async def register_custom_pattern(
    request: CustomPatternRequest,
) -> Dict[str, str]:
    try:
        robust_parser.register_custom_pattern(
            name=request.name,
            pattern=request.pattern,
            timestamp_group=request.timestamp_group,
            level_group=request.level_group,
            message_group=request.message_group,
        )

        return {
            "message": f"Custom pattern '{request.name}' registered successfully"
        }

    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to register pattern: {str(e)}",
        )


@router.get("/statistics", response_model=ParserStatistics)
async def get_parser_statistics() -> ParserStatistics:
    stats = robust_parser.get_parser_statistics()

    return ParserStatistics(
        total_attempted=stats["total_attempted"],
        successfully_parsed=stats["successfully_parsed"],
        partially_parsed=stats["partially_parsed"],
        failed=stats["failed"],
        success_rate=stats["success_rate"],
    )


@router.get("/formats")
async def get_supported_formats() -> Dict[str, Any]:
    stats = robust_parser.get_parser_statistics()

    return {
        "standard_formats": [
            {
                "name": pattern.name,
                "priority": pattern.priority,
                "matches": stats["format_coverage"][pattern.name][
                    "matches"
                ],
                "success_rate": stats["format_coverage"][pattern.name][
                    "coverage"
                ],
            }
            for pattern in robust_parser.standard_formats
        ],
        "custom_formats": [
            {
                "name": name,
                "priority": pattern.priority,
                "matches": stats["format_coverage"][name]["matches"],
                "success_rate": stats["format_coverage"][name][
                    "coverage"
                ],
            }
            for name, pattern in robust_parser.custom_patterns.items()
        ],
    }


@router.post("/analyze-sample")
async def analyze_sample_logs(
    request: SampleAnalysisRequest,
) -> Dict[str, Any]:
    if not request.sample_lines or len(request.sample_lines) < 1:
        raise HTTPException(
            status_code=400,
            detail="At least 1 sample line is required",
        )

    suggested_pattern = robust_parser.suggest_pattern(
        request.sample_lines, request.name
    )

    parse_results = []
    for line in request.sample_lines:
        result = robust_parser.parse(line)
        parse_results.append({
            "line": line[:100],
            "success": result.success,
            "parser_used": result.parser_used,
            "coverage": result.coverage,
        })

    return {
        "sample_count": len(request.sample_lines),
        "suggested_pattern": suggested_pattern,
        "parse_results": parse_results,
        "overall_success_rate": (
            sum(1 for r in parse_results if r["success"])
            / len(parse_results)
            if parse_results
            else 0
        ),
    }


@router.post("/batch-parse")
async def batch_parse_logs(
    lines: List[str],
) -> Dict[str, Any]:
    if not lines:
        raise HTTPException(
            status_code=400,
            detail="At least 1 log line is required",
        )

    results = []
    success_count = 0
    parser_usage = {}

    for line in lines:
        result = robust_parser.parse(line)
        results.append({
            "success": result.success,
            "parser_used": result.parser_used,
            "coverage": result.coverage,
        })

        if result.success:
            success_count += 1

        if result.parser_used:
            parser_usage[result.parser_used] = (
                parser_usage.get(result.parser_used, 0) + 1
            )

    return {
        "total_lines": len(lines),
        "successfully_parsed": success_count,
        "failed_to_parse": len(lines) - success_count,
        "success_rate": success_count / len(lines) if lines else 0,
        "parser_usage": parser_usage,
        "results": results[:10],
    }


@router.get("/health")
async def parsing_health() -> Dict[str, Any]:
    stats = robust_parser.get_parser_statistics()

    return {
        "status": (
            "healthy"
            if stats["success_rate"] > 0.8
            else "degraded"
        ),
        "success_rate": stats["success_rate"],
        "total_logs_processed": stats["total_attempted"],
    }


@router.post("/test-pattern")
async def test_custom_pattern(
    pattern_name: str,
    pattern: str,
    test_line: str,
) -> Dict[str, Any]:
    import re

    try:
        regex = re.compile(pattern)
        match = regex.search(test_line)

        if not match:
            return {
                "pattern_name": pattern_name,
                "matches": False,
                "error": None,
            }

        return {
            "pattern_name": pattern_name,
            "matches": True,
            "groups": match.groupdict(),
            "groups_count": len(match.groups()),
        }

    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid regex pattern: {str(e)}",
        )

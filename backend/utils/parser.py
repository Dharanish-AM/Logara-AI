import re
from datetime import datetime
from typing import Dict, Optional

class LogParser:
    """
    Utility to parse common log formats into structured JSON.
    Initial support for standard [TIMESTAMP] LEVEL: MESSAGE patterns.
    """
    
    LOG_PATTERN = re.compile(
        r'\[(?P<timestamp>.*?)\]\s+(?P<level>INFO|WARN|ERROR|DEBUG|CRITICAL):\s+(?P<message>.*)'
    )

    @staticmethod
    def parse_line(line: str) -> Optional[Dict]:
        match = LogParser.LOG_PATTERN.match(line)
        if not match:
            return None
        
        data = match.groupdict()
        # Attempt to normalize timestamp
        try:
            # Placeholder for actual parsing logic
            pass
        except Exception:
            pass
            
        return data

    @staticmethod
    def extract_metadata(message: str) -> Dict:
        """
        Simple heuristic to extract potential metadata from log messages.
        Example: Extracts 'auth-service' from 'Latency spike in auth-service'
        """
        metadata = {}
        # Simple keyword matching for demo purposes
        if "service" in message.lower():
            words = message.split()
            for i, word in enumerate(words):
                if "service" in word.lower():
                    metadata["service"] = word.strip(".,")
        return metadata

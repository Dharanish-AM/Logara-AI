from pydantic import BaseModel


class IncidentMemoryResult(BaseModel):
    id: str
    score: float
    error_message: str
    explanation: str
    service_id: str | None = None

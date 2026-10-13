from datetime import datetime

from pydantic import BaseModel


class LeaderboardEntryRead(BaseModel):
    rank: int | None
    display_name: str
    submitted_attempts: int
    average_score_percent: float | None
    best_score_percent: float | None
    last_submitted_at: datetime | None
    is_current_user: bool

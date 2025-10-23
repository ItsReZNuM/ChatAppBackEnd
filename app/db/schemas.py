from pydantic import BaseModel
from datetime import datetime

class MessageOut(BaseModel):
    id: int
    room_id: int
    username: str | None
    content: str
    created_at: datetime
    edited_at: datetime | None = None

    @property
    def edited(self) -> bool:
        return self.edited_at is not None

class HistoryOut(BaseModel):
    room_id: int
    messages: list[MessageOut]
    users: list[str]

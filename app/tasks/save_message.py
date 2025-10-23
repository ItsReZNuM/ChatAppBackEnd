from app.celery_app import app
from app.db.session import SyncSessionLocal
from app.db.crud import save_message_sync

@app.task(name="save_message_task")
def save_message_task(room_id: int, username: str, content: str) -> int:
    with SyncSessionLocal() as db:
        msg_id = save_message_sync(db, room_id=room_id, username=username, content=content)
        return msg_id

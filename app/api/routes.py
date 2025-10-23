from fastapi import APIRouter, Depends, HTTPException, File , UploadFile
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_async_session
from app.db.schemas import HistoryOut, MessageOut
from app.db.crud import get_or_create_room, get_history, update_message, delete_message
import os
from fastapi.responses import FileResponse

router = APIRouter()
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.get("/rooms/{room_id}/history", response_model=HistoryOut)
async def room_history(room_id: int, session: AsyncSession = Depends(get_async_session)):
    await get_or_create_room(session, room_id)
    messages, users = await get_history(session, room_id, limit=2000)
    return {"room_id": room_id, "messages": messages, "users": users}

class EditIn(BaseModel):
    username: str
    content: str

@router.patch("/messages/{message_id}", response_model=MessageOut)
async def edit_message(message_id: int, body: EditIn, session: AsyncSession = Depends(get_async_session)):
    msg = await update_message(session, message_id, body.username, body.content)
    if not msg:
        raise HTTPException(status_code=403, detail="not allowed or message not found")
    # پاسخ استاندارد
    return {
        "id": msg.id,
        "room_id": msg.room_id,
        "username": body.username,
        "content": msg.content,
        "created_at": msg.created_at,
        "edited_at": msg.edited_at,
    }

class DeleteIn(BaseModel):
    username: str

@router.delete("/messages/{message_id}")
async def remove_message(message_id: int, body: DeleteIn, session: AsyncSession = Depends(get_async_session)):
    ok = await delete_message(session, message_id, body.username)
    if not ok:
        raise HTTPException(status_code=403, detail="not allowed or message not found")
    return {"ok": True}

@router.post("/upload/")
async def upload_file(file: UploadFile = File(...)):
    """دریافت فایل و ذخیره در uploads"""
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    try:
        with open(file_path, "wb") as f:
            f.write(await file.read())
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"file upload failed: {e}")

    file_url = f"/api/uploads/{file.filename}"
    return {"url": file_url}


@router.get("/uploads/{filename}")
async def get_uploaded_file(filename: str):
    """دریافت فایل آپلود‌شده"""
    file_path = os.path.join(UPLOAD_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="file not found")
    return FileResponse(file_path)
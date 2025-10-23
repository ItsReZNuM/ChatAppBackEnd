from datetime import datetime, timezone
from sqlalchemy import select, func, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session , aliased
from app.db.models import User, Room, Message

# ---------- Async (FastAPI) ----------
async def get_or_create_user(session: AsyncSession, username: str) -> User:
    res = await session.execute(select(User).where(User.username == username))
    user = res.scalar_one_or_none()
    if user:
        return user
    user = User(username=username)
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user

async def get_or_create_room(session: AsyncSession, room_id: int) -> Room:
    res = await session.execute(select(Room).where(Room.id == room_id))
    room = res.scalar_one_or_none()
    if room:
        return room
    room = Room(id=room_id)
    session.add(room)
    await session.commit()
    await session.refresh(room)
    return room

async def create_message(session: AsyncSession, room_id: int, username: str, content: str) -> Message:
    user = await get_or_create_user(session, username)
    await get_or_create_room(session, room_id)
    msg = Message(room_id=room_id, user_id=user.id, content=content)
    session.add(msg)
    await session.commit()
    await session.refresh(msg)
    return msg

async def get_history(session, room_id: int, limit: int = 2000):
    Parent = aliased(Message)
    ParentUser = aliased(User)

    q = await session.execute(
        select(
            Message.id,
            Message.room_id,
            Message.user_id,
            Message.content,
            Message.created_at,
            Message.edited_at,
            Message.replied_to,
            Message.is_deleted,  # خود پیام
            User.username.label("username"),
            Parent.content.label("reply_text"),
            Parent.is_deleted.label("reply_deleted"),
            ParentUser.username.label("reply_user"),
        )
        .join(User, User.id == Message.user_id)
        .join(Parent, Parent.id == Message.replied_to, isouter=True)
        .join(ParentUser, ParentUser.id == Parent.user_id, isouter=True)
        .where(Message.room_id == room_id)
        .order_by(Message.created_at.asc())
        .limit(limit)
    )

    rows = q.all()
    messages = []
    for r in rows:
        m = r._mapping
        reply_text = None if m["reply_deleted"] else m["reply_text"]
        reply_user = None if m["reply_deleted"] else m["reply_user"]

        messages.append({
            "id": m["id"],
            "room_id": m["room_id"],
            "username": m["username"],
            "content": m["content"] if not m["is_deleted"] else None,
            "created_at": m["created_at"],
            "edited_at": m["edited_at"],
            "replied_to": m["replied_to"],
            "reply_text": reply_text,
            "reply_user": reply_user,
            "reply_deleted": bool(m["reply_deleted"]),
            "is_deleted": bool(m["is_deleted"]),
        })

    users = sorted({mm["username"] for mm in messages})
    return messages, users


async def update_message(session: AsyncSession, message_id: int, username: str, new_content: str) -> Message | None:
    res = await session.execute(
        select(Message, User).join(User, Message.user_id == User.id).where(Message.id == message_id)
    )
    row = res.first()
    if not row:
        return None
    msg, user = row
    if user.username != username:
        return None

    msg.content = new_content
    msg.edited_at = datetime.utcnow()
    await session.commit()
    await session.refresh(msg)
    return msg

async def delete_message(session: AsyncSession, message_id: int, username: str) -> bool:
    res = await session.execute(
        select(Message, User).join(User, Message.user_id == User.id).where(Message.id == message_id)
    )
    row = res.first()
    if not row:
        return False
    msg, user = row
    if user.username != username:
        return False

    await session.delete(msg)
    await session.commit()
    return True

def save_message_sync(db: Session, room_id: int, username: str, content: str) -> int:
    user = db.execute(select(User).where(User.username == username)).scalar_one_or_none()
    if not user:
        user = User(username=username)
        db.add(user)
        db.flush()

    room = db.execute(select(Room).where(Room.id == room_id)).scalar_one_or_none()
    if not room:
        room = Room(id=room_id)
        db.add(room)
        db.flush()

    msg = Message(room_id=room.id, user_id=user.id, content=content)
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return msg.id

async def create_message(session, room_id, user_id, content, replied_to=None):
    msg = Message(room_id=room_id, user_id=user_id, content=content, replied_to=replied_to)
    session.add(msg)
    await session.commit()
    await session.refresh(msg)
    return msg

async def delete_message_db(session, message_id: int, username: str) -> bool:
    q = await session.execute(
        select(Message, User.username)
        .join(User, User.id == Message.user_id)
        .where(Message.id == message_id)
    )
    row = q.first()
    if not row:
        return False
    msg, owner = row
    if owner != username:
        return False

    await session.execute(
        update(Message)
        .where(Message.id == message_id)
        .values(is_deleted=True, edited_at=datetime.now(timezone.utc))
    )
    await session.commit()
    return True
import json
import socketio
from sqlalchemy.orm import aliased
from typing import Dict, Set
from datetime import date, datetime  
from app.db.session import AsyncSessionLocal
from app.db.crud import (
    get_or_create_user,
    get_or_create_room,
    get_history,
    create_message,
    update_message,
    delete_message_db,
)
from sqlalchemy import select
from app.db.models import User
from app.db.models import Message, User

def json_serial(obj):
    """JSON serializer for objects not serializable by default json code."""
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")

def to_json_safe(obj):
    """Return a JSON-safe (dict/list/primitive) structure by converting unknowns via json_serial."""
    return json.loads(json.dumps(obj, default=json_serial))


active_users_by_room: Dict[int, Set[str]] = {}

def register_socket_events(sio: socketio.AsyncServer):

    @sio.event
    async def connect(sid, environ):
        await sio.emit("connected", {"sid": sid}, to=sid)

    @sio.event
    async def join(sid, data):
        username = str(data.get("username", "")).strip()
        room_id = int(data.get("room_id"))
        if not username:
            await sio.emit("error", {"message": "username required"}, to=sid)
            return

        room_users = active_users_by_room.setdefault(room_id, set())
        if username in room_users:
            await sio.emit("error", {"message": "این یوزرنیم در این گروه فعال است"}, to=sid)
            await sio.disconnect(sid)
            return

        async with AsyncSessionLocal() as session:
            user = await get_or_create_user(session, username)
            await get_or_create_room(session, room_id)
            await sio.save_session(sid, {"username": user.username, "room_id": room_id})
            await sio.enter_room(sid, str(room_id))
            messages, users = await get_history(session, room_id, limit=2000)

        room_users.add(username)

        await sio.emit(
            "history",
            to_json_safe({"room_id": room_id, "messages": messages, "users": users}),
            to=sid,
        )

        # ✅ پیام برای خودش
        await sio.emit("system", to_json_safe({
            "content": f"You joined room {room_id}.",
            "room_id": room_id
        }), to=sid)

        # ✅ پیام برای بقیه
        await sio.emit("system", to_json_safe({
            "content": f"{username} joined room {room_id}.",
            "room_id": room_id
        }), room=str(room_id))
        print(f"Sent System message: {username} joined room {room_id}")


    @sio.on("delete_message")
    async def handle_delete_message(sid, data, callback=None):
        message_id = int(data.get("message_id"))
        username = str(data.get("username", "")).strip()

        async with AsyncSessionLocal() as session:
            ok = await delete_message_db(session, message_id, username)
            if not ok:
                await sio.emit("error", {"message": "Delete not allowed or message not found"}, to=sid)
                return

        sess = await sio.get_session(sid)
        room_id = sess.get("room_id") or data.get("room_id")

        await sio.emit("message_deleted", {"id": message_id, "room_id": room_id}, room=str(room_id))
        async with AsyncSessionLocal() as db2:
            q = await db2.execute(
                select(Message.id).where(Message.replied_to == message_id)
            )
            children = [r[0] for r in q.fetchall()]
            for child_id in children:
                await sio.emit(
                    "parent_deleted",
                    {"parent_id": message_id, "room_id": room_id},
                    room=str(room_id),
                )
        await sio.emit(
            "parent_deleted",
            {"parent_id": message_id, "room_id": room_id},
            room=str(room_id),
        )



    @sio.event
    async def disconnect(sid):
        sess = await sio.get_session(sid)
        if sess and "room_id" in sess and "username" in sess:
            room_id = sess["room_id"]
            username = sess["username"]
            users = active_users_by_room.get(room_id)
            if users and username in users:
                users.remove(username)
            await sio.emit("system", {"content": f"{username} left room {room_id}."}, room=str(room_id))
            print(f"Sent System message: {username} Left room {room_id}")

    @sio.on("edit_message")
    async def handle_edit_message(sid, data, callback=None):
        message_id = int(data.get("message_id"))
        username = str(data.get("username", "")).strip()
        new_content = (data.get("content") or "").strip()
        if not new_content:
            await sio.emit("error", {"message": "empty content"}, to=sid)
            return

        async with AsyncSessionLocal() as db:
            msg = await update_message(db, message_id, username, new_content)
            if not msg:
                await sio.emit("error", {"message": "Edit not allowed or message not found"}, to=sid)
                return

            reply_user = None
            reply_text = None
            reply_deleted = False
            if msg.replied_to:
                Parent = aliased(Message)
                ParentUser = aliased(User)
                q = await db.execute(
                    select(Parent.content, Parent.is_deleted, ParentUser.username)
                    .join(ParentUser, ParentUser.id == Parent.user_id)
                    .where(Parent.id == msg.replied_to)
                )
                row = q.first()
                if row:
                    p_content, p_deleted, p_user = row
                    reply_deleted = bool(p_deleted)
                    if not reply_deleted:
                        reply_text = p_content
                        reply_user = p_user

        payload = {
            "id": msg.id,
            "room_id": msg.room_id,
            "username": username,
            "content": msg.content,
            "created_at": msg.created_at,
            "edited_at": msg.edited_at,
            "replied_to": msg.replied_to,
            "reply_text": reply_text,
            "reply_user": reply_user,
            "reply_deleted": reply_deleted,
        }
        await sio.emit("message_edited", to_json_safe(payload), room=str(msg.room_id))
        async with AsyncSessionLocal() as db2:
            q = await db2.execute(
                select(Message.id).where(Message.replied_to == msg.id)
            )
            children = [r[0] for r in q.fetchall()]
            for child_id in children:
                await sio.emit(
                    "parent_edited",
                    {
                        "parent_id": msg.id,
                        "new_text": msg.content,
                        "parent_user": username,
                        "room_id": msg.room_id,
                    },
                    room=str(msg.room_id),
                )
        await sio.emit(
            "parent_edited",
            {"parent_id": msg.id, "new_text": msg.content, "parent_user": username, "room_id": msg.room_id},
            room=str(msg.room_id),
        )


    @sio.on("message")
    async def handle_message(sid, data):
        username = data.get("username")
        room_id = data.get("room_id")
        content = data.get("content")
        replied_to = data.get("replied_to")

        async with AsyncSessionLocal() as db:
            user = await get_or_create_user(db, username)
            msg = await create_message(db, room_id, user.id, content, replied_to)
            reply_user = None
            reply_text = None
            if replied_to:
                
                q = await db.execute(
                    select(Message.content, User.username)
                    .join(User, User.id == Message.user_id)
                    .where(Message.id == replied_to)
                )
                parent = q.first()
                if parent:
                    reply_text, reply_user = parent.content, parent.username
                    
            payload = {
                "id": msg.id,
                "username": username,
                "room_id": room_id,
                "content": content,
                "created_at": msg.created_at,
                "replied_to": replied_to,
                "reply_user": reply_user,
                "reply_text": reply_text,
            }

        await sio.emit("message", to_json_safe(payload), room=str(room_id))


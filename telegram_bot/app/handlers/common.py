from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from aiogram import Bot
from aiogram.enums import ChatMemberStatus

from app.config import TIMEZONE


def get_today_date():
    tz = ZoneInfo(TIMEZONE)
    return datetime.now(tz=tz).date()


async def is_admin(bot: Bot, chat_id: int, user_id: int) -> bool:
    if user_id is None:
        return False
    member = await bot.get_chat_member(chat_id, user_id)
    return member.status in {ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR}


def is_anonymous_admin_message(chat_id: int, sender_chat_id: int | None) -> bool:
    # If an admin writes "as the group", Telegram sets sender_chat to current chat.
    return sender_chat_id is not None and sender_chat_id == chat_id

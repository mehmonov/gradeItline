from __future__ import annotations

from datetime import datetime
from html import escape
from zoneinfo import ZoneInfo

from aiogram import Router, Bot, F
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery

from app.config import TIMEZONE
from app.db import async_session
from app.handlers.common import get_today_date, is_admin, is_anonymous_admin_message
from app import crud
from app.keyboards import students_keyboard, status_keyboard, score_keyboard
from app.models import Group, LessonGradeStatus, NotificationStatus
from app.text import format_grade_message

router = Router()


def _clean_username(username: str | None) -> str | None:
    if not username:
        return None
    return username.lstrip("@").strip() or None


@router.message(Command("add"))
async def add_student(message: Message, bot: Bot):
    if message.chat.type not in {"group", "supergroup"}:
        return

    is_allowed = is_anonymous_admin_message(
        chat_id=message.chat.id,
        sender_chat_id=message.sender_chat.id if message.sender_chat else None,
    )
    if not is_allowed:
        user_id = message.from_user.id if message.from_user else None
        is_allowed = await is_admin(bot, message.chat.id, user_id)

    if not is_allowed:
        await message.reply("Bu buyruq faqat adminlar uchun.")
        return

    if not message.text:
        return

    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.reply("Foydalanish: /add @username Ism Familiya yoki reply /add Ism Familiya")
        return

    rest = parts[1].strip()
    tg_user_id = None
    tg_username = None
    full_name = ""

    if message.reply_to_message and message.reply_to_message.from_user:
        reply_user = message.reply_to_message.from_user
        tg_user_id = reply_user.id
        tg_username = _clean_username(reply_user.username)
        full_name = rest
    else:
        tokens = rest.split(maxsplit=1)
        if not tokens[0].startswith("@"):
            await message.reply("Foydalanish: /add @username Ism Familiya yoki reply /add Ism Familiya")
            return
        tg_username = _clean_username(tokens[0])
        if not tg_username:
            await message.reply("Username noto‘g‘ri. Misol: /add @username Ali Vali")
            return
        if len(tokens) < 2:
            await message.reply("Ism Familiya kiriting. Misol: /add @username Ali Vali")
            return
        full_name = tokens[1].strip()

    if not full_name:
        await message.reply("Ism Familiya bo‘sh bo‘lishi mumkin emas.")
        return

    async with async_session() as session:
        group = await crud.ensure_group(session, message.chat.id, message.chat.title)
        student = await crud.create_or_update_student(
            session=session,
            group_id=group.id,
            tg_user_id=tg_user_id,
            tg_username=tg_username,
            full_name=full_name,
        )

    await message.reply(
        f"O‘quvchi qo‘shildi: {student.full_name}. Kodi: #{student.code}\n"
        f"Eslatma: o‘quvchiga xabarni o‘qituvchi o‘zi yozadi."
    )


@router.message(Command("grade"))
async def grade_students(message: Message, bot: Bot):
    if message.chat.type not in {"group", "supergroup"}:
        return

    is_allowed = is_anonymous_admin_message(
        chat_id=message.chat.id,
        sender_chat_id=message.sender_chat.id if message.sender_chat else None,
    )
    if not is_allowed:
        user_id = message.from_user.id if message.from_user else None
        is_allowed = await is_admin(bot, message.chat.id, user_id)

    if not is_allowed:
        await message.reply("Bu buyruq faqat adminlar uchun.")
        return

    async with async_session() as session:
        group = await crud.ensure_group(session, message.chat.id, message.chat.title)
        students = await crud.get_active_students(session, group.id)
        if not students:
            await message.reply("Guruhda o‘quvchilar yo‘q.")
            return

        lesson_date = get_today_date()
        lesson = await crud.get_or_create_lesson(session, group.id, lesson_date)
        await crud.ensure_lesson_grades(session, lesson.id, students)

    students_list = [(s.id, f"{s.full_name} (#{s.code})") for s in students]
    await message.reply("Baholash uchun o‘quvchini tanlang:", reply_markup=students_keyboard(students_list))


@router.callback_query(F.data.startswith("grade_student:"))
async def pick_student(callback: CallbackQuery, bot: Bot):
    if not callback.message or callback.message.chat.type not in {"group", "supergroup"}:
        await callback.answer()
        return

    user_id = callback.from_user.id if callback.from_user else None
    if not await is_admin(bot, callback.message.chat.id, user_id):
        await callback.answer("Faqat adminlar baholay oladi.", show_alert=True)
        return

    student_id = int(callback.data.split(":")[1])
    async with async_session() as session:
        student = await crud.get_student_by_id(session, student_id)
    if not student:
        await callback.answer("O'quvchi topilmadi.", show_alert=True)
        return

    await callback.message.edit_text(
        f"Tanlandi: {student.full_name}\nHolatni tanlang:",
        reply_markup=status_keyboard(student_id),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("grade_status:"))
async def pick_status(callback: CallbackQuery, bot: Bot):
    if not callback.message or callback.message.chat.type not in {"group", "supergroup"}:
        await callback.answer()
        return

    user_id = callback.from_user.id if callback.from_user else None
    if not await is_admin(bot, callback.message.chat.id, user_id):
        await callback.answer("Faqat adminlar baholay oladi.", show_alert=True)
        return

    parts = callback.data.split(":")
    student_id = int(parts[1])
    status = LessonGradeStatus(parts[2])

    if status == LessonGradeStatus.DONE:
        await callback.message.edit_text("Ballni tanlang:", reply_markup=score_keyboard(student_id))
        await callback.answer()
        return

    await _set_grade(callback, bot, student_id, status, None)


@router.callback_query(F.data.startswith("grade_score:"))
async def pick_score(callback: CallbackQuery, bot: Bot):
    if not callback.message or callback.message.chat.type not in {"group", "supergroup"}:
        await callback.answer()
        return

    user_id = callback.from_user.id if callback.from_user else None
    if not await is_admin(bot, callback.message.chat.id, user_id):
        await callback.answer("Faqat adminlar baholay oladi.", show_alert=True)
        return

    parts = callback.data.split(":")
    student_id = int(parts[1])
    score = int(parts[2])

    await _set_grade(callback, bot, student_id, LessonGradeStatus.DONE, score)


async def _set_grade(callback: CallbackQuery, bot: Bot, student_id: int, status: LessonGradeStatus, score: int | None):
    if not callback.message:
        await callback.answer("Xatolik: xabar topilmadi.", show_alert=True)
        return

    async with async_session() as session:
        group = await crud.ensure_group(session, callback.message.chat.id, callback.message.chat.title)
        lesson_date = get_today_date()
        lesson = await crud.get_or_create_lesson(session, group.id, lesson_date)
        students = await crud.get_active_students(session, group.id)
        await crud.ensure_lesson_grades(session, lesson.id, students)

        grade = await crud.update_grade(
            session=session,
            lesson_id=lesson.id,
            student_id=student_id,
            status=status,
            score=score,
            graded_by_tg_user_id=callback.from_user.id if callback.from_user else None,
        )

        grade = await crud.get_lesson_grade_with_relations(session, grade.id)
        if not grade:
            await callback.answer("Xatolik: baho topilmadi.", show_alert=True)
            return

        await _send_notifications(bot, session, grade)
        await _sync_leaderboard_message(bot, session, group.id)

        message_text = format_grade_message(
            group_title=group.title or "Guruh",
            student_name=grade.student.full_name,
            lesson_date=str(grade.lesson.lesson_date),
            status=grade.status,
            score=grade.score,
        )

    await callback.message.answer(f"Baholandi.\n\n{message_text}")
    try:
        await callback.message.delete()
    except TelegramBadRequest:
        pass
    await callback.answer("Baholandi")


def _build_leaderboard_text(group_title: str, rows: list[dict]) -> str:
    now_text = datetime.now(ZoneInfo(TIMEZONE)).strftime("%Y-%m-%d %H:%M")
    lines = [f"<b>Leaderboard - {escape(group_title)}</b>", ""]
    if not rows:
        lines.append("Hozircha baho yo'q.")
    else:
        for idx, row in enumerate(rows, start=1):
            lines.append(f"{idx}. <b>{escape(row['full_name'])}</b>")
            lines.append(
                f"Jami: {row['total_score']} | O'rtacha: {row['avg_score']:.2f} | "
                f"Bajarmadi: {row['not_done_count']} | Kelmadi: {row['absent_count']}"
            )
            lines.append("")
    lines.append(f"Yangilandi: {now_text}")
    return "\n".join(lines)


async def _sync_leaderboard_message(bot: Bot, session, group_id: int) -> None:
    group = await session.get(Group, group_id)
    if not group:
        return

    rows = await crud.get_group_leaderboard_rows(session, group_id)
    text = _build_leaderboard_text(group.title or "Guruh", rows)
    state = await crud.get_or_create_group_state(session, group_id)

    message_id = state.leaderboard_message_id
    sent_new = False
    if message_id:
        try:
            await bot.edit_message_text(
                text=text,
                chat_id=group.chat_id,
                message_id=message_id,
                parse_mode="HTML",
                disable_web_page_preview=True,
            )
        except TelegramBadRequest as exc:
            if "message is not modified" in str(exc).lower():
                sent_new = False
            else:
                sent = await bot.send_message(
                    group.chat_id,
                    text,
                    parse_mode="HTML",
                    disable_web_page_preview=True,
                )
                message_id = sent.message_id
                sent_new = True
    else:
        sent = await bot.send_message(
            group.chat_id,
            text,
            parse_mode="HTML",
            disable_web_page_preview=True,
        )
        message_id = sent.message_id
        sent_new = True

    if sent_new:
        state.leaderboard_message_id = message_id
        state.updated_at = datetime.utcnow()
        await session.commit()

    try:
        await bot.pin_chat_message(group.chat_id, message_id, disable_notification=True)
    except (TelegramBadRequest, TelegramForbiddenError):
        pass


async def _send_notifications(bot: Bot, session, grade):
    parents = await crud.get_parents_for_student(session, grade.student_id)
    if not parents:
        return

    group_title = grade.lesson.group.title or "Guruh"
    message_text = format_grade_message(
        group_title=group_title,
        student_name=grade.student.full_name,
        lesson_date=str(grade.lesson.lesson_date),
        status=grade.status,
        score=grade.score,
    )

    for parent in parents:
        notification = await crud.get_notification(session, grade.id, parent.id)
        if not notification:
            notification = await crud.create_notification(session, grade.id, parent.id)
        try:
            await bot.send_message(parent.tg_user_id, message_text)
            notification.status = NotificationStatus.SENT
            notification.sent_at = datetime.utcnow()
            notification.error = None
        except Exception as exc:
            notification.status = NotificationStatus.FAILED
            notification.error = str(exc)[:255]
        await session.commit()

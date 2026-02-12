from __future__ import annotations

import re
from datetime import datetime

from aiogram import Router, Bot, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, ReplyKeyboardRemove

from app.db import async_session
from app import crud
from app.models import LessonGradeStatus, NotificationStatus, Student
from app.text import format_grade_message
from app.keyboards import parent_menu_keyboard

router = Router()

BTN_LINK_CHILD = "Bolani bog'lash"
BTN_CHILDREN = "Bog'langan bolalarim"
BTN_ADMIN_PANEL = "Admin panel"
ADMIN_TG_USER_ID = 6329800356

CYR_TO_LAT = {
    "а": "a",
    "б": "b",
    "в": "v",
    "г": "g",
    "ғ": "g",
    "д": "d",
    "е": "e",
    "ё": "yo",
    "ж": "j",
    "з": "z",
    "и": "i",
    "й": "y",
    "к": "k",
    "қ": "q",
    "л": "l",
    "м": "m",
    "н": "n",
    "о": "o",
    "п": "p",
    "р": "r",
    "с": "s",
    "т": "t",
    "у": "u",
    "ф": "f",
    "х": "x",
    "ҳ": "h",
    "ц": "s",
    "ч": "ch",
    "ш": "sh",
    "щ": "sh",
    "ъ": "",
    "ь": "",
    "э": "e",
    "ю": "yu",
    "я": "ya",
    "ў": "o",
    "ы": "i",
}


class ParentRegistration(StatesGroup):
    waiting_name = State()
    waiting_phone = State()
    waiting_code = State()
    waiting_child_name = State()


def _parse_code(text: str) -> str | None:
    raw = text.strip()
    if raw.startswith("#"):
        raw = raw[1:]
    if not raw.isdigit():
        return None
    return raw


def _normalize_name(value: str) -> str:
    text = value.strip().lower()
    for ch in ("'", "’", "`", "ʻ", "ʼ"):
        text = text.replace(ch, "'")

    # Cyrillic -> Latin normalization for Uzbek/Russian-style names.
    text = "".join(CYR_TO_LAT.get(ch, ch) for ch in text)

    # Normalize Uzbek apostrophe variants in Latin script.
    text = text.replace("o'", "o").replace("g'", "g")
    text = text.replace("yo", "yo").replace("yu", "yu").replace("ya", "ya")

    return re.sub(r"[^a-z]", "", text)


def _first_token(value: str) -> str:
    parts = value.strip().split()
    return parts[0] if parts else ""


def _is_super_admin(user_id: int | None) -> bool:
    return user_id == ADMIN_TG_USER_ID


def _menu_markup(user_id: int | None, has_parent: bool):
    return parent_menu_keyboard(is_admin=_is_super_admin(user_id), include_parent=has_parent)


@router.message(Command("start"))
async def start(message: Message, state: FSMContext):
    if message.chat.type != "private":
        return

    user_id = message.from_user.id if message.from_user else None
    async with async_session() as session:
        parent = await crud.get_parent_by_tg_user_id(session, user_id)

    if _is_super_admin(user_id):
        await state.clear()
        await message.answer(
            "Admin bo'limi ochiq. Menyudan kerakli tugmani tanlang.",
            reply_markup=_menu_markup(user_id, has_parent=bool(parent)),
        )
        return

    if parent:
        await state.clear()
        await message.answer(
            "Assalomu alaykum. Menyudan kerakli tugmani tanlang.",
            reply_markup=_menu_markup(user_id, has_parent=True),
        )
        return

    await state.set_state(ParentRegistration.waiting_name)
    await message.answer(
        "Iltimos, ism familiyangizni kiriting:",
        reply_markup=ReplyKeyboardRemove(),
    )


@router.message(ParentRegistration.waiting_name)
async def handle_parent_name(message: Message, state: FSMContext):
    if not message.text:
        await message.answer("Ism familiyani matn ko'rinishida kiriting:")
        return
    name = message.text.strip()
    if len(name) < 3:
        await message.answer("Ism familiya juda qisqa. Qaytadan kiriting:")
        return

    await state.update_data(full_name=name)
    await state.set_state(ParentRegistration.waiting_phone)
    await message.answer("Telefon raqamingizni kiriting (masalan: 998901234567):")


@router.message(ParentRegistration.waiting_phone)
async def handle_parent_phone(message: Message, state: FSMContext):
    if not message.text:
        await message.answer("Telefon raqamni matn ko'rinishida kiriting:")
        return
    phone = message.text.strip()
    if len(phone) < 5:
        await message.answer("Telefon raqam noto‘g‘ri. Qaytadan kiriting:")
        return

    data = await state.get_data()
    full_name = data.get("full_name")
    user_id = message.from_user.id if message.from_user else None

    async with async_session() as session:
        await crud.create_or_update_parent(session, user_id, full_name, phone)

    await state.clear()
    await message.answer(
        "Rahmat. Endi menyudan bolani bog'lash tugmasini tanlang.",
        reply_markup=_menu_markup(user_id, has_parent=True),
    )


@router.message(F.text == BTN_LINK_CHILD)
@router.message(Command("link"))
async def start_link_child(message: Message, state: FSMContext):
    if message.chat.type != "private":
        return

    user_id = message.from_user.id if message.from_user else None
    async with async_session() as session:
        parent = await crud.get_parent_by_tg_user_id(session, user_id)
    if not parent:
        await message.answer("Avval /start orqali ro‘yxatdan o‘ting.")
        return

    await state.set_state(ParentRegistration.waiting_code)
    await message.answer(
        "Bolangizning kodini kiriting (masalan: #1234):",
        reply_markup=ReplyKeyboardRemove(),
    )


@router.message(ParentRegistration.waiting_code)
async def handle_child_code(message: Message, state: FSMContext):
    if not message.text:
        await message.answer("Kodni matn ko'rinishida kiriting. Masalan: #1234")
        return
    code = _parse_code(message.text)
    if not code:
        await message.answer("Kod noto‘g‘ri. Masalan: #1234")
        return

    user_id = message.from_user.id if message.from_user else None
    async with async_session() as session:
        parent = await crud.get_parent_by_tg_user_id(session, user_id)
        if not parent:
            await message.answer("Avval /start orqali ro‘yxatdan o‘ting.")
            await state.clear()
            return

        student = await crud.get_student_by_code(session, code)
        if not student:
            await message.answer("Bu kod bilan o‘quvchi topilmadi.")
            return

    await state.update_data(link_student_id=student.id)
    await state.set_state(ParentRegistration.waiting_child_name)
    await message.answer("Endi bolangizning ismini kiriting:")


@router.message(ParentRegistration.waiting_child_name)
async def handle_child_name_check(message: Message, state: FSMContext, bot: Bot):
    if not message.text:
        await message.answer("Ism-familiyani matn ko'rinishida kiriting:")
        return

    user_id = message.from_user.id if message.from_user else None
    parent_input_name = message.text.strip()
    data = await state.get_data()
    student_id = data.get("link_student_id")
    if not student_id:
        await state.clear()
        await message.answer(
            "Jarayon qayta boshlandi. Menyudan tugmani tanlang.",
            reply_markup=_menu_markup(user_id, has_parent=True),
        )
        return

    async with async_session() as session:
        parent = await crud.get_parent_by_tg_user_id(session, user_id)
        if not parent:
            await message.answer("Avval /start orqali ro‘yxatdan o‘ting.")
            await state.clear()
            return

        student = await session.get(Student, student_id)
        if not student:
            await message.answer("O'quvchi topilmadi. Qayta urinib ko'ring.")
            await state.clear()
            await message.answer("Menyudan tugmani tanlang.", reply_markup=_menu_markup(user_id, has_parent=True))
            return

        input_first_name = _normalize_name(_first_token(parent_input_name))
        student_first_name = _normalize_name(_first_token(student.full_name))
        if not input_first_name or input_first_name != student_first_name:
            await message.answer("Ism mos kelmadi. Qayta kiriting.")
            return

        created = await crud.link_parent_student(session, parent.id, student.id)
        if created:
            await message.answer(f"Bog'landi: {student.full_name}")
        else:
            await message.answer(f"Bu o'quvchi allaqachon bog'langan: {student.full_name}")

        grades = await crud.get_notifications_for_parent(session, parent.id, student.id)
        if grades:
            await _send_pending_grades(bot, session, parent.id, parent.tg_user_id, grades)

    await state.clear()
    await message.answer("Menyudan tugmani tanlang.", reply_markup=_menu_markup(user_id, has_parent=True))


@router.message(F.text == BTN_CHILDREN)
@router.message(Command("children"))
async def list_children(message: Message):
    if message.chat.type != "private":
        return

    user_id = message.from_user.id if message.from_user else None
    async with async_session() as session:
        parent = await crud.get_parent_by_tg_user_id(session, user_id)
        if not parent:
            await message.answer("Avval /start orqali ro‘yxatdan o‘ting.")
            return

        students = await crud.get_students_for_parent(session, parent.id)
        if not students:
            await message.answer("Hozircha bog'langan bolalar yo'q.", reply_markup=_menu_markup(user_id, has_parent=True))
            return

        lines = [f"- {s.full_name} (#{s.code})" for s in students]
        await message.answer("Bog'langan bolalar:\n" + "\n".join(lines), reply_markup=_menu_markup(user_id, has_parent=True))


@router.message(F.text == BTN_ADMIN_PANEL)
@router.message(Command("admin"))
async def admin_panel(message: Message):
    if message.chat.type != "private":
        return

    user_id = message.from_user.id if message.from_user else None
    if not _is_super_admin(user_id):
        await message.answer("Bu bo'lim faqat admin uchun.")
        return

    async with async_session() as session:
        groups = await crud.get_groups_overview(session)
        students = await crud.get_all_students_with_group(session)
        parent = await crud.get_parent_by_tg_user_id(session, user_id)

    total_groups = len(groups)
    total_students = len(students)
    header = (
        "Admin panel\n"
        f"Jami guruhlar: {total_groups}\n"
        f"Jami o'quvchilar: {total_students}"
    )
    await message.answer(header, reply_markup=_menu_markup(user_id, has_parent=bool(parent)))

    group_lines = ["Guruhlar:"]
    if not groups:
        group_lines.append("Hozircha guruh yo'q.")
    else:
        for idx, (title, chat_id, student_count) in enumerate(groups, start=1):
            group_name = title or f"Chat {chat_id}"
            group_lines.append(f"{idx}. {group_name} | Chat: {chat_id} | O'quvchi: {student_count}")
    await _send_long_text(message, "\n".join(group_lines))

    student_lines = ["O'quvchilar:"]
    if not students:
        student_lines.append("Hozircha o'quvchi yo'q.")
    else:
        for idx, (full_name, code, group_title) in enumerate(students, start=1):
            group_name = group_title or "Noma'lum guruh"
            student_lines.append(f"{idx}. {full_name} (#{code}) | {group_name}")
    await _send_long_text(message, "\n".join(student_lines))


@router.message(Command("cancel"))
async def cancel(message: Message, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id if message.from_user else None
    async with async_session() as session:
        parent = await crud.get_parent_by_tg_user_id(session, user_id)
    await message.answer("Bekor qilindi.", reply_markup=_menu_markup(user_id, has_parent=bool(parent)))


@router.message(F.chat.type == "private")
async def parent_menu_fallback(message: Message):
    user_id = message.from_user.id if message.from_user else None
    async with async_session() as session:
        parent = await crud.get_parent_by_tg_user_id(session, user_id)
    if parent or _is_super_admin(user_id):
        await message.answer(
            "Menyudan tugmani tanlang.",
            reply_markup=_menu_markup(user_id, has_parent=bool(parent)),
        )


async def _send_long_text(message: Message, text: str, chunk_size: int = 3500):
    current = []
    current_len = 0
    for line in text.splitlines():
        line_len = len(line) + 1
        if current_len + line_len > chunk_size and current:
            await message.answer("\n".join(current))
            current = [line]
            current_len = line_len
        else:
            current.append(line)
            current_len += line_len
    if current:
        await message.answer("\n".join(current))


async def _send_pending_grades(bot: Bot, session, parent_id: int, parent_tg_id: int, grades):
    for grade in grades:
        if grade.status == LessonGradeStatus.PENDING:
            continue
        notification = await crud.get_notification(session, grade.id, parent_id)
        if notification:
            continue
        notification = await crud.create_notification(session, grade.id, parent_id)

        group_title = grade.lesson.group.title if grade.lesson and grade.lesson.group else "Guruh"
        message_text = format_grade_message(
            group_title=group_title,
            student_name=grade.student.full_name,
            lesson_date=str(grade.lesson.lesson_date),
            status=grade.status,
            score=grade.score,
        )
        try:
            await bot.send_message(parent_tg_id, message_text)
            notification.status = NotificationStatus.SENT
            notification.sent_at = datetime.utcnow()
            notification.error = None
        except Exception as exc:
            notification.status = NotificationStatus.FAILED
            notification.error = str(exc)[:255]
        await session.commit()

from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
)
from app.models import LessonGradeStatus


def students_keyboard(students: list[tuple[int, str]]) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text=name, callback_data=f"grade_student:{student_id}")]
        for student_id, name in students
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def status_keyboard(student_id: int) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text="Bajardi", callback_data=f"grade_status:{student_id}:{LessonGradeStatus.DONE.value}")],
        [InlineKeyboardButton(text="Bajarmadi", callback_data=f"grade_status:{student_id}:{LessonGradeStatus.NOT_DONE.value}")],
        [InlineKeyboardButton(text="Darsga kelmadi", callback_data=f"grade_status:{student_id}:{LessonGradeStatus.ABSENT.value}")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def score_keyboard(student_id: int) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text=str(score), callback_data=f"grade_score:{student_id}:{score}") for score in range(1, 6)]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def parent_menu_keyboard(is_admin: bool = False, include_parent: bool = True) -> ReplyKeyboardMarkup:
    rows = []
    if include_parent:
        rows.append([KeyboardButton(text="Bolani bog'lash")])
        rows.append([KeyboardButton(text="Bog'langan bolalarim")])
    if is_admin:
        rows.append([KeyboardButton(text="Admin panel")])

    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True, is_persistent=True)

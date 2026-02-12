import random
import string
from datetime import date, datetime
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.models import (
    Group,
    GroupState,
    Student,
    Parent,
    ParentStudent,
    Lesson,
    LessonGrade,
    StudentStats,
    StudentStatus,
    LessonGradeStatus,
    Notification,
)


async def ensure_group(session, chat_id: int, title: str | None) -> Group:
    group = await session.scalar(select(Group).where(Group.chat_id == chat_id))
    if group:
        if title and group.title != title:
            group.title = title
        return group
    group = Group(chat_id=chat_id, title=title)
    session.add(group)
    await session.commit()
    await session.refresh(group)
    return group


async def get_or_create_group_state(session, group_id: int) -> GroupState:
    state = await session.get(GroupState, group_id)
    if state:
        return state
    state = GroupState(group_id=group_id)
    session.add(state)
    await session.commit()
    await session.refresh(state)
    return state


async def generate_unique_code(session, length: int = 4) -> str:
    for _ in range(20):
        code = "".join(random.choices(string.digits, k=length))
        exists = await session.scalar(select(Student.id).where(Student.code == code))
        if not exists:
            return code
    return await generate_unique_code(session, length + 1)


async def get_student_by_code(session, code: str) -> Student | None:
    return await session.scalar(select(Student).where(Student.code == code))


async def get_student_by_id(session, student_id: int) -> Student | None:
    return await session.get(Student, student_id)


async def create_or_update_student(
    session,
    group_id: int,
    tg_user_id: int | None,
    tg_username: str | None,
    full_name: str,
) -> Student:
    student = None
    if tg_user_id:
        student = await session.scalar(
            select(Student).where(Student.group_id == group_id, Student.tg_user_id == tg_user_id)
        )
    if not student and tg_username:
        student = await session.scalar(
            select(Student).where(Student.group_id == group_id, Student.tg_username == tg_username)
        )

    if student:
        student.full_name = full_name
        if tg_username and not student.tg_username:
            student.tg_username = tg_username
        if tg_user_id and not student.tg_user_id:
            student.tg_user_id = tg_user_id
        student.status = StudentStatus.ACTIVE
        await session.commit()
        return student

    code = await generate_unique_code(session)
    student = Student(
        group_id=group_id,
        tg_user_id=tg_user_id,
        tg_username=tg_username,
        full_name=full_name,
        code=code,
        status=StudentStatus.ACTIVE,
    )
    session.add(student)
    await session.commit()
    await session.refresh(student)

    stats = await session.get(StudentStats, student.id)
    if not stats:
        session.add(StudentStats(student_id=student.id, not_done_count=0))
        await session.commit()

    return student


async def get_active_students(session, group_id: int) -> list[Student]:
    result = await session.execute(
        select(Student).where(Student.group_id == group_id, Student.status == StudentStatus.ACTIVE)
    )
    return list(result.scalars().all())


async def get_or_create_lesson(session, group_id: int, lesson_date: date) -> Lesson:
    lesson = await session.scalar(
        select(Lesson).where(Lesson.group_id == group_id, Lesson.lesson_date == lesson_date)
    )
    if lesson:
        return lesson
    lesson = Lesson(group_id=group_id, lesson_date=lesson_date)
    session.add(lesson)
    await session.commit()
    await session.refresh(lesson)
    return lesson


async def ensure_lesson_grades(session, lesson_id: int, students: list[Student]) -> None:
    existing = await session.execute(
        select(LessonGrade.student_id).where(LessonGrade.lesson_id == lesson_id)
    )
    existing_ids = set(existing.scalars().all())
    for student in students:
        if student.id in existing_ids:
            continue
        session.add(
            LessonGrade(
                lesson_id=lesson_id,
                student_id=student.id,
                status=LessonGradeStatus.PENDING,
                score=None,
                updated_at=datetime.utcnow(),
            )
        )
    await session.commit()


async def create_or_update_parent(session, tg_user_id: int, full_name: str, phone: str) -> Parent:
    parent = await session.scalar(select(Parent).where(Parent.tg_user_id == tg_user_id))
    if parent:
        parent.full_name = full_name
        parent.phone = phone
        await session.commit()
        return parent
    parent = Parent(tg_user_id=tg_user_id, full_name=full_name, phone=phone)
    session.add(parent)
    await session.commit()
    await session.refresh(parent)
    return parent


async def get_parent_by_tg_user_id(session, tg_user_id: int) -> Parent | None:
    return await session.scalar(select(Parent).where(Parent.tg_user_id == tg_user_id))


async def link_parent_student(session, parent_id: int, student_id: int) -> bool:
    existing = await session.scalar(
        select(ParentStudent).where(
            ParentStudent.parent_id == parent_id, ParentStudent.student_id == student_id
        )
    )
    if existing:
        return False
    session.add(ParentStudent(parent_id=parent_id, student_id=student_id))
    await session.commit()
    return True


async def get_parents_for_student(session, student_id: int) -> list[Parent]:
    result = await session.execute(
        select(Parent)
        .join(ParentStudent, Parent.id == ParentStudent.parent_id)
        .where(ParentStudent.student_id == student_id)
    )
    return list(result.scalars().all())


async def get_students_for_parent(session, parent_id: int) -> list[Student]:
    result = await session.execute(
        select(Student)
        .join(ParentStudent, Student.id == ParentStudent.student_id)
        .where(ParentStudent.parent_id == parent_id)
    )
    return list(result.scalars().all())


async def get_groups_overview(session) -> list[tuple[str, int, int]]:
    result = await session.execute(
        select(
            Group.title,
            Group.chat_id,
            func.count(Student.id).label("student_count"),
        )
        .outerjoin(Student, Student.group_id == Group.id)
        .group_by(Group.id)
        .order_by(func.coalesce(Group.title, "").asc(), Group.chat_id.asc())
    )
    return list(result.all())


async def get_all_students_with_group(session) -> list[tuple[str, str, str]]:
    result = await session.execute(
        select(Student.full_name, Student.code, Group.title)
        .join(Group, Group.id == Student.group_id)
        .order_by(func.coalesce(Group.title, "").asc(), Student.full_name.asc())
    )
    return list(result.all())


async def update_grade(
    session,
    lesson_id: int,
    student_id: int,
    status: LessonGradeStatus,
    score: int | None,
    graded_by_tg_user_id: int | None,
) -> LessonGrade:
    grade = await session.scalar(
        select(LessonGrade).where(
            LessonGrade.lesson_id == lesson_id, LessonGrade.student_id == student_id
        )
    )
    if not grade:
        grade = LessonGrade(lesson_id=lesson_id, student_id=student_id)
        session.add(grade)
        await session.commit()
        await session.refresh(grade)

    old_status = grade.status
    grade.status = status
    grade.score = score
    grade.graded_by_tg_user_id = graded_by_tg_user_id
    grade.updated_at = datetime.utcnow()
    await session.commit()

    await update_not_done_stats(session, student_id, old_status, status)
    return grade


async def update_not_done_stats(
    session, student_id: int, old_status: LessonGradeStatus | None, new_status: LessonGradeStatus
) -> None:
    stats = await session.get(StudentStats, student_id)
    if not stats:
        stats = StudentStats(student_id=student_id, not_done_count=0)
        session.add(stats)
        await session.commit()

    if old_status == LessonGradeStatus.NOT_DONE and new_status != LessonGradeStatus.NOT_DONE:
        stats.not_done_count = max(0, stats.not_done_count - 1)
        stats.updated_at = datetime.utcnow()
        await session.commit()
    elif old_status != LessonGradeStatus.NOT_DONE and new_status == LessonGradeStatus.NOT_DONE:
        stats.not_done_count += 1
        stats.updated_at = datetime.utcnow()
        await session.commit()


async def get_lesson_grade_with_relations(session, lesson_grade_id: int) -> LessonGrade | None:
    return await session.scalar(
        select(LessonGrade)
        .options(
            selectinload(LessonGrade.student),
            selectinload(LessonGrade.lesson).selectinload(Lesson.group),
        )
        .where(LessonGrade.id == lesson_grade_id)
    )


async def get_notifications_for_parent(session, parent_id: int, student_id: int) -> list[LessonGrade]:
    result = await session.execute(
        select(LessonGrade)
        .options(
            selectinload(LessonGrade.student),
            selectinload(LessonGrade.lesson).selectinload(Lesson.group),
        )
        .join(Lesson, Lesson.id == LessonGrade.lesson_id)
        .where(LessonGrade.student_id == student_id)
        .order_by(Lesson.lesson_date.asc())
    )
    return list(result.scalars().all())


async def get_group_leaderboard_rows(session, group_id: int) -> list[dict]:
    students = await get_active_students(session, group_id)
    if not students:
        return []

    rows: dict[int, dict] = {}
    for student in students:
        rows[student.id] = {
            "student_id": student.id,
            "full_name": student.full_name,
            "total_score": 0,
            "done_count": 0,
            "not_done_count": 0,
            "absent_count": 0,
        }

    grades_result = await session.execute(
        select(LessonGrade.student_id, LessonGrade.status, LessonGrade.score)
        .join(Lesson, Lesson.id == LessonGrade.lesson_id)
        .where(Lesson.group_id == group_id)
    )

    for student_id, status, score in grades_result.all():
        if student_id not in rows:
            continue
        if status == LessonGradeStatus.DONE:
            rows[student_id]["done_count"] += 1
            rows[student_id]["total_score"] += score or 0
        elif status == LessonGradeStatus.NOT_DONE:
            rows[student_id]["not_done_count"] += 1
        elif status == LessonGradeStatus.ABSENT:
            rows[student_id]["absent_count"] += 1

    result_rows = []
    for row in rows.values():
        done_count = row["done_count"]
        row["avg_score"] = round(row["total_score"] / done_count, 2) if done_count else 0.0
        result_rows.append(row)

    result_rows.sort(
        key=lambda r: (
            -r["total_score"],
            -r["avg_score"],
            -r["done_count"],
            r["full_name"].lower(),
        )
    )
    return result_rows


async def get_notification(session, lesson_grade_id: int, parent_id: int) -> Notification | None:
    return await session.scalar(
        select(Notification).where(
            Notification.lesson_grade_id == lesson_grade_id, Notification.parent_id == parent_id
        )
    )


async def create_notification(session, lesson_grade_id: int, parent_id: int) -> Notification:
    notification = Notification(lesson_grade_id=lesson_grade_id, parent_id=parent_id)
    session.add(notification)
    await session.commit()
    await session.refresh(notification)
    return notification

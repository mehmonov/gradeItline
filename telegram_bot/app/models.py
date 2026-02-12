from __future__ import annotations

from datetime import datetime, date
from enum import Enum

from sqlalchemy import (
    String,
    Integer,
    BigInteger,
    Date,
    DateTime,
    Enum as SqlEnum,
    ForeignKey,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class StudentStatus(str, Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class LessonGradeStatus(str, Enum):
    PENDING = "PENDING"
    DONE = "DONE"
    NOT_DONE = "NOT_DONE"
    ABSENT = "ABSENT"


class NotificationStatus(str, Enum):
    PENDING = "PENDING"
    SENT = "SENT"
    FAILED = "FAILED"


class Group(Base):
    __tablename__ = "groups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    chat_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    students: Mapped[list[Student]] = relationship("Student", back_populates="group")
    lessons: Mapped[list[Lesson]] = relationship("Lesson", back_populates="group")
    state: Mapped[GroupState | None] = relationship("GroupState", back_populates="group", uselist=False)


class Student(Base):
    __tablename__ = "students"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("groups.id"), index=True)
    tg_user_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, index=True)
    tg_username: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str] = mapped_column(String(10), unique=True, index=True)
    status: Mapped[StudentStatus] = mapped_column(SqlEnum(StudentStatus), default=StudentStatus.ACTIVE)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    group: Mapped[Group] = relationship("Group", back_populates="students")
    grades: Mapped[list[LessonGrade]] = relationship("LessonGrade", back_populates="student")


class Parent(Base):
    __tablename__ = "parents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tg_user_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    students: Mapped[list[ParentStudent]] = relationship("ParentStudent", back_populates="parent")


class ParentStudent(Base):
    __tablename__ = "parent_students"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    parent_id: Mapped[int] = mapped_column(ForeignKey("parents.id"), index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (UniqueConstraint("parent_id", "student_id", name="uq_parent_student"),)

    parent: Mapped[Parent] = relationship("Parent", back_populates="students")
    student: Mapped[Student] = relationship("Student")


class Lesson(Base):
    __tablename__ = "lessons"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("groups.id"), index=True)
    lesson_date: Mapped[date] = mapped_column(Date)

    __table_args__ = (UniqueConstraint("group_id", "lesson_date", name="uq_group_lesson_date"),)

    group: Mapped[Group] = relationship("Group", back_populates="lessons")
    grades: Mapped[list[LessonGrade]] = relationship("LessonGrade", back_populates="lesson")


class LessonGrade(Base):
    __tablename__ = "lesson_grades"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    lesson_id: Mapped[int] = mapped_column(ForeignKey("lessons.id"), index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), index=True)
    status: Mapped[LessonGradeStatus] = mapped_column(SqlEnum(LessonGradeStatus), default=LessonGradeStatus.PENDING)
    score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    graded_by_tg_user_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (UniqueConstraint("lesson_id", "student_id", name="uq_lesson_student"),)

    lesson: Mapped[Lesson] = relationship("Lesson", back_populates="grades")
    student: Mapped[Student] = relationship("Student", back_populates="grades")


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    lesson_grade_id: Mapped[int] = mapped_column(ForeignKey("lesson_grades.id"), index=True)
    parent_id: Mapped[int] = mapped_column(ForeignKey("parents.id"), index=True)
    status: Mapped[NotificationStatus] = mapped_column(SqlEnum(NotificationStatus), default=NotificationStatus.PENDING)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    error: Mapped[str | None] = mapped_column(String(255), nullable=True)

    __table_args__ = (UniqueConstraint("lesson_grade_id", "parent_id", name="uq_grade_parent"),)


class StudentStats(Base):
    __tablename__ = "student_stats"

    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), primary_key=True)
    not_done_count: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class GroupState(Base):
    __tablename__ = "group_states"

    group_id: Mapped[int] = mapped_column(ForeignKey("groups.id"), primary_key=True)
    leaderboard_message_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    group: Mapped[Group] = relationship("Group", back_populates="state")

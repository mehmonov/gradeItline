from app.models import LessonGradeStatus


def format_grade_message(group_title: str, student_name: str, lesson_date: str, status: LessonGradeStatus, score: int | None) -> str:
    status_map = {
        LessonGradeStatus.DONE: "Bajarildi",
        LessonGradeStatus.NOT_DONE: "Bajarmadi",
        LessonGradeStatus.ABSENT: "Darsga kelmadi",
        LessonGradeStatus.PENDING: "Baholanmagan",
    }
    score_text = str(score) if score is not None else "—"
    return (
        f"Guruh: {group_title}\n"
        f"O‘quvchi: {student_name}\n"
        f"Sana: {lesson_date}\n"
        f"Holat: {status_map.get(status, status)}\n"
        f"Ball: {score_text}"
    )

"""EPK-19 Education SM-2 Spaced Repetition & Rubric Exam Autograder package."""

from education.service import (
    create_flashcard,
    grade_exam_submission,
    init_education_db,
    list_flashcards,
    review_flashcard,
    router,
    sm2_schedule,
)

__all__ = [
    "create_flashcard",
    "grade_exam_submission",
    "init_education_db",
    "list_flashcards",
    "review_flashcard",
    "router",
    "sm2_schedule",
]

"""Idempotent demo records. Run explicitly after Alembic migrations."""
import os
from uuid import UUID

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from teacher_materials.models import Course, CourseMembership, Topic, User


def seed_demo(session: Session) -> None:
    for user_id, name, role in (("demo-teacher", "Jamie", "teacher"), ("demo-teacher-other", "Alex", "teacher"), ("demo-student", "Student", "student")):
        if session.get(User, user_id) is None:
            session.add(User(id=user_id, display_name=name, role=role))
    courses = (("11111111-1111-4111-8111-111111111111", "Software Engineering"), ("22222222-2222-4222-8222-222222222222", "Programming"))
    for value, title in courses:
        if session.get(Course, UUID(value)) is None:
            session.add(Course(id=UUID(value), title=title))
    session.flush()
    memberships = ((courses[0][0], "demo-teacher"), (courses[1][0], "demo-teacher-other"), (courses[0][0], "demo-student"))
    for course_id, user_id in memberships:
        key = (UUID(course_id), user_id)
        if session.get(CourseMembership, key) is None:
            session.add(CourseMembership(course_id=key[0], user_id=key[1]))
    for topic_id, course_id, name in (("33333333-3333-4333-8333-333333333333", courses[0][0], "Testing"), ("44444444-4444-4444-8444-444444444444", courses[1][0], "Basics")):
        if session.get(Topic, UUID(topic_id)) is None:
            session.add(Topic(id=UUID(topic_id), course_id=UUID(course_id), name=name))
    session.commit()


if __name__ == "__main__":
    url = os.environ["DATABASE_URL"]
    with Session(create_engine(url)) as session:
        seed_demo(session)

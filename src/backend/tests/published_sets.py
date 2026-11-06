"""Database helpers for STU-02-published-sets tests (contract: workflow/specs/STU-02-published-sets/plan.md).

Inserts published practice sets with SQL (the publish route belongs to TEA-03), in the style of
stu01_helpers.py, together with the material, draft batch and draft questions that the restrictive
foreign keys require. Memberships use stu01_helpers.enroll / unenroll.
"""
import json
import uuid

from stu01_helpers import enroll, make_course, make_topic, sql, uid, unenroll  # noqa: F401

# (question text, four choices, correct index, explanation)
QUESTIONS = [
    ("What does a unit test check?", ["One small piece of behaviour", "The whole deployment", "Only the UI colours", "Nothing"], 0,
     "A unit test checks one small piece of behaviour in isolation."),
    ("Which HTTP status means not found?", ["200", "404", "500", "302"], 1,
     "404 is the status for a resource that does not exist."),
    ("What does len([1, 2, 3]) return?", ["2", "4", "3", "6"], 2, "len returns the number of items, here three."),
]
KEY_INDEX = [q[2] for q in QUESTIONS]


def question_set(correct_indexes=(0, 1, 2), tag=""):
    """Three questions whose correct indexes are `correct_indexes` (choices keep their stored order)."""
    out = []
    for i, idx in enumerate(correct_indexes):
        choices = [f"{tag}Q{i + 1} choice {c}" for c in "ABCD"]
        out.append((f"{tag}Question number {i + 1}?", choices, idx, f"{tag}Explanation {i + 1} for choice {'ABCD'[idx]}."))
    return out


def insert_published_set(course_id, topic_id, title="Testing basics", questions=None, published_at=None, set_id=None,
                         published_by="demo-teacher"):
    """Insert one published set (and the draft rows its foreign keys need). Returns the set id.

    `questions`: list of (text, four choices, correct index, explanation); default `QUESTIONS`.
    """
    questions = questions or QUESTIONS
    set_id = set_id or uid()
    material_id, batch_id = uid(), uid()
    sql("INSERT INTO material(id, course_id, topic_id, uploaded_by, title, original_filename, media_type, size_bytes) "
        "VALUES (%s, %s, %s, 'demo-teacher', 'Source', 's.txt', 'text/plain', 1)", (material_id, course_id, topic_id))
    sql("INSERT INTO material_file(material_id, content) VALUES (%s, 'x'::bytea)", (material_id,))
    sql("INSERT INTO mcq_draft_batch(id, course_id, source_material_id, created_by, updated_by, source_title, version) "
        "VALUES (%s, %s, %s, 'demo-teacher', 'demo-teacher', 'Source', 1)", (batch_id, course_id, material_id))
    draft_ids = []
    for position, (text, choices, correct, explanation) in enumerate(questions, start=1):
        qid = uid()
        draft_ids.append(qid)
        sql("INSERT INTO mcq_draft_question(id, batch_id, position, question, choices, correct_choice_index, explanation) "
            "VALUES (%s, %s, %s, %s, %s::jsonb, %s, %s)",
            (qid, batch_id, position, text, json.dumps(choices), correct, explanation))
    sql("INSERT INTO published_practice_set(id, course_id, topic_id, title, source_draft_id, source_version, "
        "published_by, published_at) VALUES (%s, %s, %s, %s, %s, 1, %s, COALESCE(%s::timestamptz, now()))",
        (set_id, course_id, topic_id, title, batch_id, published_by, published_at))
    for position, (text, choices, correct, explanation) in enumerate(questions, start=1):
        sql("INSERT INTO published_practice_question(id, set_id, position, question, choices, correct_choice_index, "
            "explanation, source_question_id) VALUES (%s, %s, %s, %s, %s::jsonb, %s, %s, %s)",
            (uid(), set_id, position, text, json.dumps(choices), correct, explanation, draft_ids[position - 1]))
    return set_id


def question_rows(set_id):
    """[(id, position, question, choices, correct_choice_index, explanation)] in position order."""
    return sql("SELECT id::text, position, question, choices, correct_choice_index, explanation "
               "FROM published_practice_question WHERE set_id = %s ORDER BY position", (set_id,))


def delete_published_set(set_id):
    """Delete a set at the database level (the application never does)."""
    sql("DELETE FROM published_practice_question WHERE set_id = %s", (set_id,))
    sql("DELETE FROM published_practice_set WHERE id = %s", (set_id,))


def world(title="Testing basics", questions=None, course_title=None, topic_name=None):
    """A course, a topic and one published set; returns (course_id, topic_id, set_id)."""
    cid = make_course(course_title)
    tid = make_topic(cid, topic_name or f"Topic {cid[:6]}")
    return cid, tid, insert_published_set(cid, tid, title, questions)


def attempt_row(attempt_id):
    rows = sql("SELECT id, student_id, set_id, status, answers, score_correct, score_total, key_version "
               "FROM practice_attempt WHERE id = %s", (attempt_id,))
    return rows[0] if rows else None


def new_id():
    return str(uuid.uuid4())

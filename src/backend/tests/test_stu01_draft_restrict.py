"""STU-01 contract: published_lesson.source_draft_id restricts deletion of the draft via the teacher delete route."""
import uuid

from test_tea02_notes import BASE, COURSE, call, error
from test_tea02_mcqs import mcqs  # noqa: F401  (fixture)
from test_tea03_mcqs_cleanup import delete, prepared

MESSAGE = "This draft is referenced by other content and cannot be deleted."


def make_note(app, fake, source):
    fake.text = "Notes"
    r = call(app, "POST", f"{BASE}/materials/{source['id']}/note-drafts")
    assert r.status_code == 201, r.text
    return r.json()


def test_stu01_published_note_draft_delete_returns_409_draft_in_use(mcqs, tea01_database):
    app, fake, source, _ = prepared(mcqs)
    note = make_note(app, fake, source)
    lid = str(uuid.uuid4())
    tea01_database.execute(
        "INSERT INTO published_lesson(id, course_id, title, content, published_by, source_draft_id) "
        "VALUES (%s, %s, 'T', 'C', 'demo-teacher', %s)", (lid, COURSE, note["id"]))
    tea01_database.commit()
    try:
        r = delete(app, "note-drafts", note)
        error(r, 409, "draft_in_use")
        assert r.json()["detail"]["message"] == MESSAGE
        assert call(app, "GET", f"{BASE}/note-drafts/{note['id']}").json() == note
        tea01_database.rollback()
        assert tea01_database.execute("SELECT source_draft_id::text FROM published_lesson WHERE id=%s",
                                      (lid,)).fetchone()[0] == note["id"]
    finally:
        tea01_database.rollback()
        tea01_database.execute("DELETE FROM published_lesson WHERE id=%s", (lid,))
        tea01_database.commit()


def test_stu01_unpublished_note_draft_delete_succeeds(mcqs, tea01_database):
    app, fake, source, _ = prepared(mcqs)
    note = make_note(app, fake, source)
    r = delete(app, "note-drafts", note)
    assert r.status_code == 204 and r.content == b""
    error(call(app, "GET", f"{BASE}/note-drafts/{note['id']}"), 404, "not_found")

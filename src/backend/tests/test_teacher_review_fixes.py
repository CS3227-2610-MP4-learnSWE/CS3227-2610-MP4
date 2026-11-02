"""Independent regression contract for the approved teacher review fixes."""
import pytest

from test_tea02_notes import BASE, COURSE, call, error, generate, notes, upload


@pytest.mark.parametrize("bad", ["\x00", "\ud800", "\udfff"], ids=["nul", "high-surrogate", "low-surrogate"])
def test_teacher_review_invalid_generated_unicode_is_bad_response_and_preserves_work(notes, tea01_database, tea01_storage, bad):
    app, fake = notes
    source = upload(app)
    saved = generate(app, source).json()
    files = {p.name: p.read_bytes() for p in tea01_storage.iterdir()}
    fake.text = f"valid note{bad}tail"
    response = generate(app, source)
    detail = error(response, 502, "llm_bad_response")
    assert detail["message"] == "The AI service returned unusable content. Please try again."
    assert "valid note" not in response.text
    assert len(fake.calls) == 2
    assert tea01_database.execute("SELECT count(*) FROM study_note_draft WHERE source_material_id=%s", (source["id"],)).fetchone()[0] == 1
    assert call(app, "GET", f"{BASE}/note-drafts/{saved['id']}").json() == saved
    assert {p.name: p.read_bytes() for p in tea01_storage.iterdir()} == files


def test_teacher_review_nul_upload_title_is_validation_error_before_file_creation(notes, tea01_database, tea01_storage):
    app, fake = notes
    before = tea01_database.execute("SELECT count(*) FROM material").fetchone()[0]
    tea01_database.commit()
    files = {p.name for p in tea01_storage.iterdir()}
    response = call(app, "POST", f"{BASE}/courses/{COURSE}/materials", data={"title": "Unit\x00testing"}, files={"file": ("source.txt", b"A unit test isolates one behaviour.")})
    error(response, 422, "validation_error")
    assert tea01_database.execute("SELECT count(*) FROM material").fetchone()[0] == before
    assert {p.name for p in tea01_storage.iterdir()} == files
    assert not fake.calls


def test_teacher_review_astral_unicode_remains_valid_in_titles_and_generated_notes(notes):
    app, fake = notes
    source = upload(app, title="  " + "\U0001f680" * 200 + "  ")
    assert source["title"] == "\U0001f680" * 200
    fake.text = "\U0001f680" * 1999
    response = generate(app, source)
    assert response.status_code == 201, response.text
    draft = response.json()
    assert draft["content"] == fake.text
    assert draft["title"] == source["title"]
    assert call(app, "GET", f"{BASE}/note-drafts/{draft['id']}").json() == draft

"""TEA-01 black-box API and PostgreSQL contract tests."""

import asyncio
import io
import json
import os
import subprocess
import sys
import tempfile
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import httpx
import pytest


BASE = "/api/teacher"
COURSE_A = "11111111-1111-4111-8111-111111111111"
COURSE_B = "22222222-2222-4222-8222-222222222222"
TOPIC_A = "33333333-3333-4333-8333-333333333333"
TOPIC_B = "44444444-4444-4444-8444-444444444444"
COURSES = f"{BASE}/courses"
MATERIALS_A = f"{COURSES}/{COURSE_A}/materials"
MATERIALS_B = f"{COURSES}/{COURSE_B}/materials"
MATERIAL_KEYS = {
    "id", "course_id", "topic_id", "uploaded_by", "title",
    "original_filename", "media_type", "size_bytes", "created_at", "updated_at",
}


@pytest.fixture
def app(tea01_database):
    from main import app as application

    return application


def call(app, method, path, *, user="demo-teacher", files=None, data=None, json_body=None):
    headers = {"X-Demo-User-Id": user} if user is not None else {}

    async def send():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            return await client.request(method, path, headers=headers, files=files, data=data, json=json_body)

    return asyncio.run(send())


def upload(app, name="notes.txt", content=b"Source notes", title="  My source  ", path=MATERIALS_A, topic=None, user="demo-teacher", mime="application/octet-stream"):
    data = {"title": title}
    if topic is not None:
        data["topic_id"] = topic
    return call(app, "POST", path, user=user, files={"file": (name, content, mime)}, data=data)


def pdf_bytes():
    from pypdf import PdfWriter

    out = io.BytesIO()
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    writer.write(out)
    return out.getvalue()


def assert_error(response, status, code):
    assert response.status_code == status, response.text
    body = response.json()
    assert set(body) == {"detail"}
    assert set(body["detail"]) == {"code", "message"}
    assert body["detail"]["code"] == code
    assert body["detail"]["message"]
    assert "storage_key" not in response.text
    assert "Traceback" not in response.text


def assert_material(body, *, course=COURSE_A, topic=None, title=None):
    assert set(body) == MATERIAL_KEYS
    assert str(uuid.UUID(body["id"])) == body["id"]
    assert body["course_id"] == course
    assert body["topic_id"] == topic
    assert body["uploaded_by"] in {"demo-teacher", "demo-teacher-other"}
    assert isinstance(body["size_bytes"], int) and body["size_bytes"] > 0
    if title is not None:
        assert body["title"] == title
    for key in ("created_at", "updated_at"):
        assert body[key].endswith("Z")


def material_rows(db):
    return db.execute("SELECT id, storage_key, topic_id, title, original_filename, media_type, size_bytes FROM material").fetchall()


def stored_files(root):
    return {p for p in root.rglob("*") if p.is_file()}


def test_tea01_upload_pdf_and_text_persists_metadata_and_bytes(app, tea01_database, tea01_storage):
    for name, content, media in [("guide.PDF", pdf_bytes(), "application/pdf"), ("notes.TXT", "π lesson".encode(), "text/plain; charset=utf-8")]:
        response = upload(app, name, content, title="  Persistent source  ", mime="image/png")
        assert response.status_code == 201, response.text
        material = response.json()
        assert_material(material, title="Persistent source")
        assert material["original_filename"] == name
        assert material["media_type"] == media
        assert material["size_bytes"] == len(content)
        row = tea01_database.execute("SELECT storage_key, size_bytes FROM material WHERE id = %s", (material["id"],)).fetchone()
        assert row and row[1] == len(content)
        assert (tea01_storage / row[0]).read_bytes() == content
        downloaded = call(app, "GET", f"{BASE}/materials/{material['id']}/file")
        assert downloaded.status_code == 200
        assert downloaded.content == content
        assert downloaded.headers["content-type"] == media
        assert downloaded.headers["content-disposition"].lower().startswith("attachment")
        # A new process imports a fresh app and opens a fresh database connection.
        assert _fresh_download(material["id"]) == content.hex()


def _fresh_download(material_id):
    script = """import asyncio, httpx, json
from main import app
async def main():
 async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test') as c:
  r=await c.get('/api/teacher/materials/%s/file', headers={'X-Demo-User-Id':'demo-teacher'})
  print(json.dumps({'status':r.status_code,'hex':r.content.hex()}))
asyncio.run(main())""" % material_id
    result = subprocess.run([sys.executable, "-c", script], cwd=Path(__file__).resolve().parents[1], env=os.environ.copy(), capture_output=True, text=True, check=True)
    body = json.loads(result.stdout.strip().splitlines()[-1])
    assert body["status"] == 200, body
    return body["hex"]


def test_tea01_teacher_lists_and_downloads(app):
    courses = call(app, "GET", COURSES)
    assert courses.status_code == 200
    assert courses.json() == [{"id": COURSE_A, "title": "Software Engineering", "created_at": courses.json()[0]["created_at"]}]
    assert courses.json()[0]["created_at"].endswith("Z")
    topics = call(app, "GET", f"{COURSES}/{COURSE_A}/topics")
    assert topics.status_code == 200
    assert topics.json() == [{"id": TOPIC_A, "course_id": COURSE_A, "name": "Testing", "created_at": topics.json()[0]["created_at"]}]
    first = upload(app, "old.txt", b"older", "Old")
    second = upload(app, "new.txt", b"newer", "New")
    assert first.status_code == second.status_code == 201
    listed = call(app, "GET", MATERIALS_A).json()
    assert [m["id"] for m in listed[:2]] == [second.json()["id"], first.json()["id"]]
    assert all(set(m) == MATERIAL_KEYS for m in listed)


def test_tea01_assign_filter_and_unassign(app, tea01_database):
    created = upload(app, "assign.txt", b"assign", "Assignment").json()
    mid = created["id"]
    assert created["topic_id"] is None
    assigned = call(app, "PATCH", f"{BASE}/materials/{mid}", json_body={"topic_id": TOPIC_A})
    assert assigned.status_code == 200, assigned.text
    assert_material(assigned.json(), topic=TOPIC_A)
    assert {k: v for k, v in assigned.json().items() if k not in {"topic_id", "updated_at"}} == {k: v for k, v in created.items() if k not in {"topic_id", "updated_at"}}
    assert assigned.json()["updated_at"] >= created["updated_at"]
    filtered = call(app, "GET", f"{MATERIALS_A}?topic_id={TOPIC_A}")
    assert filtered.status_code == 200
    assert mid in [m["id"] for m in filtered.json()]
    assert all(m["topic_id"] == TOPIC_A for m in filtered.json())
    assert_error(call(app, "GET", f"{MATERIALS_A}?topic_id={TOPIC_B}"), 404, "not_found")
    cleared = call(app, "PATCH", f"{BASE}/materials/{mid}", json_body={"topic_id": None})
    assert cleared.status_code == 200 and cleared.json()["topic_id"] is None
    assert mid in [m["id"] for m in call(app, "GET", MATERIALS_A).json()]
    assert mid not in [m["id"] for m in call(app, "GET", f"{MATERIALS_A}?topic_id={TOPIC_A}").json()]
    assert tea01_database.execute("SELECT topic_id FROM material WHERE id=%s", (mid,)).fetchone()[0] is None


def test_tea01_cross_course_access_is_hidden(app):
    created = upload(app).json()
    mid = created["id"]
    for method, path, kwargs in [
        ("GET", f"{COURSES}/{COURSE_A}/topics", {}),
        ("GET", MATERIALS_A, {}),
        ("POST", MATERIALS_A, {"files": {"file": ("a.txt", b"a")}, "data": {"title": "A"}}),
        ("PATCH", f"{BASE}/materials/{mid}", {"json_body": {"topic_id": TOPIC_B}}),
        ("GET", f"{BASE}/materials/{mid}/file", {}),
    ]:
        assert_error(call(app, method, path, user="demo-teacher-other", **kwargs), 404, "not_found")
    assert_error(upload(app, topic=TOPIC_B), 404, "not_found")
    assert_error(call(app, "PATCH", f"{BASE}/materials/{mid}", json_body={"topic_id": TOPIC_B}), 404, "not_found")
    assert call(app, "GET", COURSES, user="demo-teacher-other").json()[0]["id"] == COURSE_B


def test_tea01_rejects_file_types_sizes_and_bad_content(app, tea01_database, tea01_storage):
    baseline = (len(material_rows(tea01_database)), stored_files(tea01_storage))
    bad = [
        (upload(app, "evil.exe", b"hello"), 415, "unsupported_media_type", ("PDF", "UTF-8 text")),
        (upload(app, "huge.txt", b"x" * (10_485_760 + 1)), 413, "file_too_large", ("10 MiB",)),
        (upload(app, "empty.txt", b""), 422, "validation_error", ()),
        (upload(app, "bad.txt", b"\xff"), 422, "validation_error", ()),
        (upload(app, "bad.pdf", b"not a pdf"), 422, "validation_error", ()),
        (upload(app, "valid.txt", b"ok", title="  "), 422, "validation_error", ()),
        (upload(app, "valid.txt", b"ok", title="x" * 201), 422, "validation_error", ()),
    ]
    for response, status, code, words in bad:
        assert_error(response, status, code)
        for word in words:
            assert word in response.json()["detail"]["message"]
    assert len(material_rows(tea01_database)) == baseline[0]
    assert stored_files(tea01_storage) == baseline[1]


def test_tea01_demo_gate_and_roles(app):
    assert_error(call(app, "GET", COURSES, user=None), 401, "unauthenticated")
    assert_error(call(app, "GET", COURSES, user="unknown"), 401, "unauthenticated")
    assert_error(call(app, "GET", COURSES, user="demo-student"), 403, "forbidden")
    assert_error(call(app, "GET", f"{COURSES}/missing/topics"), 422, "validation_error")
    assert_error(call(app, "GET", f"{COURSES}/{uuid.uuid4()}/topics"), 404, "not_found")
    assert_error(call(app, "PATCH", f"{BASE}/materials/{uuid.uuid4()}", json_body={"topic_id": None}), 404, "not_found")
    assert_error(call(app, "GET", f"{BASE}/materials/{uuid.uuid4()}/file"), 404, "not_found")
    assert_error(call(app, "GET", f"{MATERIALS_B}?topic_id=bad"), 404, "not_found")
    for env in ({"ALLOW_DEMO_IDENTITY": "false"}, {"APP_ENV": "production"}):
        assert _fresh_status("GET", COURSES, env) == (403, "demo_identity_disabled")


def _fresh_status(method, path, overrides):
    script = """import asyncio, httpx, json
from main import app
async def main():
 async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test') as c:
  r=await c.request(%r, %r, headers={'X-Demo-User-Id':'demo-teacher'})
  print(json.dumps({'status':r.status_code,'code':r.json()['detail']['code']}))
asyncio.run(main())""" % (method, path)
    env = {**os.environ, **overrides}
    result = subprocess.run([sys.executable, "-c", script], cwd=Path(__file__).resolve().parents[1], env=env, capture_output=True, text=True, check=True)
    body = json.loads(result.stdout.strip().splitlines()[-1])
    return body["status"], body["code"]


def test_tea01_validation_order_and_unknown_fields(app):
    private = f"{BASE}/materials/{uuid.uuid4()}"
    assert_error(call(app, "PATCH", private, user="demo-teacher-other", json_body={"topic_id": "bad"}), 404, "not_found")
    assert_error(call(app, "POST", MATERIALS_B, files={"file": ("bad.exe", b"bad")}, data={"title": " "}), 404, "not_found")
    created = upload(app).json()
    mid = created["id"]
    assert_error(call(app, "PATCH", f"{BASE}/materials/{mid}", json_body={}), 422, "validation_error")
    assert_error(call(app, "PATCH", f"{BASE}/materials/{mid}", json_body={"topic_id": None, "title": "changed"}), 422, "validation_error")
    assert_error(call(app, "GET", f"{MATERIALS_A}?topic_id=bad"), 422, "validation_error")


def test_tea01_upload_does_not_publish(app, tea01_database):
    before = call(app, "GET", "/api/practice-sets/intro-se-1")
    assert before.status_code == 200
    result = upload(app, "private.txt", b"private draft source")
    assert result.status_code == 201
    assert call(app, "GET", "/api/practice-sets/intro-se-1").json() == before.json()
    assert "private draft source" not in json.dumps(before.json())
    # TEA-01 creates source metadata only; the approved schema has no published lesson table.
    assert tea01_database.execute("SELECT count(*) FROM material WHERE id=%s", (result.json()["id"],)).fetchone()[0] == 1


def test_tea01_seed_is_idempotent_and_preserves_uploads(app, tea01_database):
    material = upload(app, "seed-safe.txt", b"keep my source").json()
    before = tea01_database.execute("SELECT count(*) FROM course_membership").fetchone()[0]
    subprocess.run([sys.executable, "-m", "teacher_materials.seed"], cwd=Path(__file__).resolve().parents[1], env=os.environ.copy(), check=True)
    assert tea01_database.execute("SELECT count(*) FROM course_membership").fetchone()[0] == before
    assert tea01_database.execute("SELECT title FROM material WHERE id=%s", (material["id"],)).fetchone()[0] == material["title"]
    assert call(app, "GET", f"{BASE}/materials/{material['id']}/file").content == b"keep my source"


def test_tea01_filename_and_storage_path_cannot_escape_root(app, tea01_database, tea01_storage):
    response = upload(app, "../../private-notes.txt", b"inside only")
    assert response.status_code == 201, response.text
    material = response.json()
    assert material["original_filename"] == "private-notes.txt"
    row = tea01_database.execute("SELECT storage_key FROM material WHERE id=%s", (material["id"],)).fetchone()
    original_key = row[0]
    assert (tea01_storage / original_key).resolve().is_relative_to(tea01_storage.resolve())
    with tempfile.NamedTemporaryFile(dir=tea01_storage.parent, prefix="tea01-private-", delete=True) as outside:
        outside.write(b"outside secret")
        outside.flush()
        tea01_database.execute("UPDATE material SET storage_key=%s WHERE id=%s", ("../" + Path(outside.name).name, material["id"]))
        tea01_database.commit()
        try:
            downloaded = call(app, "GET", f"{BASE}/materials/{material['id']}/file")
            assert_error(downloaded, 503, "service_unavailable")
            assert b"outside secret" not in downloaded.content
        finally:
            tea01_database.execute("UPDATE material SET storage_key=%s WHERE id=%s", (original_key, material["id"]))
            tea01_database.commit()


def test_tea01_failed_upload_cleans_files_and_rows(app, tea01_database, tea01_storage):
    baseline = (len(material_rows(tea01_database)), stored_files(tea01_storage))
    tea01_database.execute("CREATE FUNCTION tea01_fail_material() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'fixture forced insert failure'; END $$")
    tea01_database.execute("CREATE TRIGGER tea01_fail_insert BEFORE INSERT ON material FOR EACH ROW EXECUTE FUNCTION tea01_fail_material()")
    tea01_database.commit()
    try:
        response = upload(app, "failure.txt", b"must be removed")
        assert_error(response, 503, "service_unavailable")
        assert "fixture forced" not in response.text
        assert len(material_rows(tea01_database)) == baseline[0]
        assert stored_files(tea01_storage) == baseline[1]
    finally:
        tea01_database.rollback()
        tea01_database.execute("DROP TRIGGER tea01_fail_insert ON material")
        tea01_database.execute("DROP FUNCTION tea01_fail_material()")
        tea01_database.commit()


def test_tea01_concurrent_uploads_and_assignments(app, tea01_database, tea01_storage):
    with ThreadPoolExecutor(max_workers=2) as pool:
        uploaded = list(pool.map(lambda n: upload(app, f"parallel-{n}.txt", f"content {n}".encode(), f"Parallel {n}"), (1, 2)))
    assert all(r.status_code == 201 for r in uploaded), [r.text for r in uploaded]
    ids = [r.json()["id"] for r in uploaded]
    assert len(set(ids)) == 2
    rows = tea01_database.execute("SELECT storage_key FROM material WHERE id IN (%s,%s)", ids).fetchall()
    assert len(rows) == 2 and rows[0][0] != rows[1][0]
    assert all((tea01_storage / row[0]).is_file() for row in rows)
    initial = uploaded[0].json()
    with ThreadPoolExecutor(max_workers=2) as pool:
        changed = list(pool.map(lambda topic: call(app, "PATCH", f"{BASE}/materials/{ids[0]}", json_body={"topic_id": topic}), (TOPIC_A, None)))
    assert all(r.status_code == 200 for r in changed), [r.text for r in changed]
    final = next(m for m in call(app, "GET", MATERIALS_A).json() if m["id"] == ids[0])
    assert final["topic_id"] in {TOPIC_A, None}
    assert {k: v for k, v in final.items() if k not in {"topic_id", "updated_at"}} == {k: v for k, v in initial.items() if k not in {"topic_id", "updated_at"}}


def test_tea01_post_commit_read_failure_never_orphans_metadata(app, tea01_database, tea01_storage, monkeypatch):
    from sqlalchemy.exc import OperationalError
    from sqlalchemy.orm import Session

    before_files = stored_files(tea01_storage)
    title = "refresh fault " + uuid.uuid4().hex

    def fail_refresh(self, instance, *args, **kwargs):
        raise OperationalError("fixture refresh fault", {}, RuntimeError("connection lost"))

    with monkeypatch.context() as patch:
        patch.setattr(Session, "refresh", fail_refresh)
        response = upload(app, "post-commit.txt", b"still downloadable", title)
    rows = tea01_database.execute("SELECT id, storage_key FROM material WHERE title=%s", (title,)).fetchall()
    if response.status_code == 201:
        assert len(rows) == 1
        assert (tea01_storage / rows[0][1]).read_bytes() == b"still downloadable"
        assert call(app, "GET", f"{BASE}/materials/{rows[0][0]}/file").content == b"still downloadable"
    else:
        assert_error(response, 503, "service_unavailable")
        assert rows == []
        assert stored_files(tea01_storage) == before_files


def test_tea01_delayed_clear_is_last_committed_topic_update(app, tea01_database):
    created = upload(app, "delayed-clear.txt", b"topic race", "Delayed clear").json()
    mid = created["id"]

    async def race():
        entered = asyncio.Event()
        release = asyncio.Event()

        async def delayed_body():
            entered.set()
            await release.wait()
            yield b'{"topic_id":null}'

        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            headers = {"X-Demo-User-Id": "demo-teacher", "Content-Type": "application/json"}
            clear = asyncio.create_task(client.patch(f"{BASE}/materials/{mid}", headers=headers, content=delayed_body()))
            await asyncio.wait_for(entered.wait(), 5)
            assigned = await client.patch(f"{BASE}/materials/{mid}", headers=headers, json={"topic_id": TOPIC_A})
            assert assigned.status_code == 200, assigned.text
            release.set()
            cleared = await asyncio.wait_for(clear, 5)
            return assigned, cleared

    assigned, cleared = asyncio.run(race())
    assert assigned.json()["topic_id"] == TOPIC_A
    assert cleared.status_code == 200, cleared.text
    assert cleared.json()["topic_id"] is None
    final = tea01_database.execute("SELECT topic_id, title, original_filename, size_bytes FROM material WHERE id=%s", (mid,)).fetchone()
    assert final == (None, created["title"], created["original_filename"], created["size_bytes"])


def test_tea01_chunked_oversize_stops_reading_at_file_limit(app, tea01_database, tea01_storage):
    before = (len(material_rows(tea01_database)), stored_files(tea01_storage))
    chunk = b"x" * 65536
    consumed = 0
    boundary = "tea01-boundary"

    async def body():
        nonlocal consumed
        yield f'--{boundary}\r\nContent-Disposition: form-data; name="title"\r\n\r\nChunked\r\n--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="large.txt"\r\nContent-Type: text/plain\r\n\r\n'.encode()
        for _ in range(200):
            consumed += len(chunk)
            yield chunk
        yield f"\r\n--{boundary}--\r\n".encode()

    async def send():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            return await client.post(MATERIALS_A, headers={"X-Demo-User-Id": "demo-teacher", "Content-Type": f"multipart/form-data; boundary={boundary}"}, content=body())

    response = asyncio.run(send())
    assert_error(response, 413, "file_too_large")
    assert "10 MiB" in response.json()["detail"]["message"]
    assert consumed <= 10_485_760 + 2 * len(chunk), f"upload consumed {consumed} bytes before rejecting"
    assert (len(material_rows(tea01_database)), stored_files(tea01_storage)) == before


def test_tea01_multipart_topic_must_be_text_field(app, tea01_database, tea01_storage):
    before = (len(material_rows(tea01_database)), stored_files(tea01_storage))
    response = call(app, "POST", MATERIALS_A, data={"title": "Bad topic shape"}, files={"file": ("source.txt", b"source"), "topic_id": ("topic.txt", TOPIC_A.encode(), "text/plain")})
    assert_error(response, 422, "validation_error")
    assert (len(material_rows(tea01_database)), stored_files(tea01_storage)) == before

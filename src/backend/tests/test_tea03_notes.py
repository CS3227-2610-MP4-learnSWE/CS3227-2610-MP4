"""Independent TEA-03 public API and persistence contract; no live LLM calls."""
import json
import os
import subprocess
import sys
import uuid
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import pytest
from test_tea02_notes import BASE, COURSE, OTHER, call, error, generate, notes, upload

from teacher_auth import teacher_headers

FIELDS = {"id", "course_id", "source_material_id", "created_by", "title", "created_at", "source_title", "version", "updated_at", "updated_by", "content"}


def draft(notes):
    app, fake = notes
    source = upload(app, title="Original source")
    response = generate(app, source)
    assert response.status_code == 201, response.text
    return app, fake, source, response.json()


def patch(app, saved, *, user="demo-teacher", **changes):
    body = {"title": "Edited title", "content": "Edited notes", "version": saved.get("version", 1), **changes}
    return call(app, "PATCH", f"{BASE}/note-drafts/{saved['id']}", user=user, json=body)


def test_tea03_save_reopen_source_attribution_metadata_and_no_llm(notes):
    app, fake, source, saved = draft(notes)
    assert set(saved) == FIELDS
    assert saved["version"] == 1 and saved["source_title"] == source["title"]
    assert saved["updated_by"] == saved["created_by"] == "demo-teacher"
    assert saved["updated_at"] == saved["created_at"]
    calls = len(fake.calls)
    fake.error = AssertionError("editing must not call any LLM")
    result = patch(app, saved, title="  Edited title  ", content="\u2003First\r\nsecond\rthird\u2003")
    assert result.status_code == 200, result.text
    edited = result.json()
    assert set(edited) == FIELDS
    assert edited["title"] == "Edited title" and edited["content"] == "First\nsecond\nthird"
    assert edited["version"] == 2 and edited["updated_at"].endswith("Z")
    assert edited["updated_at"] >= saved["updated_at"]
    for key in ("id", "course_id", "source_material_id", "source_title", "created_at", "created_by"):
        assert edited[key] == saved[key]
    assert len(fake.calls) == calls
    assert call(app, "GET", f"{BASE}/materials/{source['id']}/file").content == b"Functions should do one thing."
    assert call(app, "GET", f"{BASE}/note-drafts/{saved['id']}").json() == edited
    listing = call(app, "GET", f"{BASE}/courses/{COURSE}/note-drafts").json()
    assert next(row for row in listing if row["id"] == saved["id"]) == {k: v for k, v in edited.items() if k != "content"}
    assert listing == sorted(listing, key=lambda row: (row["created_at"], row["id"]), reverse=True)
    script = f'''import asyncio, json, httpx
from main import app
async def main():
 async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url="http://test") as c:
  r=await c.get("{BASE}/note-drafts/{saved['id']}",headers={teacher_headers()!r})
  print(json.dumps(r.json()))
asyncio.run(main())'''
    reopened = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True, check=True)
    assert json.loads(reopened.stdout) == edited


@pytest.mark.parametrize("version", [None, True, False, "1", 1.0, 0, -1])
def test_tea03_version_is_strict_positive_integer(notes, version):
    app, _, _, saved = draft(notes)
    error(patch(app, saved, version=version), 422, "validation_error")
    assert call(app, "GET", f"{BASE}/note-drafts/{saved['id']}").json() == saved


@pytest.mark.parametrize("body", [{}, {"title":"x"}, {"title":"x","content":"x"}, {"title":None,"content":"x","version":1}, {"title":123,"content":"x","version":1}, {"title":"x","content":False,"version":1}, {"title":"x","content":"x","version":1,"created_by":"demo-teacher-other"}, [], None])
def test_tea03_requires_exact_typed_fields(notes, body):
    app, _, _, saved = draft(notes)
    error(call(app, "PATCH", f"{BASE}/note-drafts/{saved['id']}", json=body), 422, "validation_error")
    assert call(app, "GET", f"{BASE}/note-drafts/{saved['id']}").json() == saved


@pytest.mark.parametrize("title,content,valid", [("t"*200,"😀"*2000,True),("t"*201,"ok",False),("t","😀"*2001,False),("\u2003","ok",False),("t"," \r\n\t",False)])
def test_tea03_unicode_boundaries(notes, title, content, valid):
    app, _, _, saved = draft(notes)
    response = patch(app, saved, title=title, content=content)
    if valid:
        assert response.status_code == 200, response.text
        assert response.json()["content"] == content
    else:
        error(response, 422, "validation_error")
        assert call(app, "GET", f"{BASE}/note-drafts/{saved['id']}").json() == saved


def test_tea03_access_precedes_body_validation_and_revocation(notes, tea01_database, monkeypatch):
    app, _, _, saved = draft(notes)
    path = f"{BASE}/note-drafts/{saved['id']}"
    for user, status, code in [(None,401,"unauthenticated"),("unknown",401,"unauthenticated"),("demo-student",403,"forbidden"),("demo-teacher-other",404,"not_found")]:
        error(call(app,"PATCH",path,user=user,content="not json"),status,code)
    with monkeypatch.context() as m:
        m.setenv("ALLOW_DEMO_IDENTITY","false")
        error(call(app,"PATCH",path,content="not json"),422,"validation_error")
    error(call(app,"PATCH",f"{BASE}/note-drafts/not-a-uuid",json={}),422,"validation_error")
    error(call(app,"PATCH",f"{BASE}/note-drafts/{uuid.uuid4()}",json={}),404,"not_found")
    tea01_database.execute("DELETE FROM course_membership WHERE course_id=%s AND user_id='demo-teacher'",(COURSE,));tea01_database.commit()
    try:
        error(patch(app,saved),404,"not_found")
    finally:
        tea01_database.execute("INSERT INTO course_membership(course_id,user_id) VALUES(%s,'demo-teacher')",(COURSE,));tea01_database.commit()
    assert call(app,"GET",path).json()==saved


def test_tea03_concurrent_version_lock_and_lost_response_retry(notes):
    app, _, _, saved = draft(notes)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(lambda title:patch(app,saved,title=title),["First editor","Second editor"]))
    assert sorted(r.status_code for r in results)==[200,409]
    winner=next(r.json() for r in results if r.status_code==200)
    assert winner["version"]==2
    assert call(app,"GET",f"{BASE}/note-drafts/{saved['id']}").json()==winner
    error(patch(app,saved),409,"draft_conflict")
    # A client that lost the successful response cannot overwrite it by retrying version1.
    assert call(app,"GET",f"{BASE}/note-drafts/{saved['id']}").json()==winner
    unchanged=patch(app,winner,title=winner["title"],content=winner["content"])
    assert unchanged.status_code==200 and unchanged.json()["version"]==3


def test_tea03_shared_teacher_editor_and_commit_rollback(notes, tea01_database, monkeypatch):
    from sqlalchemy.orm import Session
    from sqlalchemy.exc import SQLAlchemyError
    app, _, _, saved=draft(notes)
    tea01_database.execute("INSERT INTO course_membership(course_id,user_id) VALUES(%s,'demo-teacher-other')",(COURSE,));tea01_database.commit()
    try:
        result=patch(app,saved,user="demo-teacher-other")
        assert result.status_code==200,result.text
        changed=result.json()
        assert changed["updated_by"]=="demo-teacher-other" and changed["created_by"]==saved["created_by"]
        def fail(*args,**kwargs):raise SQLAlchemyError("sentinel-secret")
        with monkeypatch.context() as m:
            m.setattr(Session,"commit",fail)
            error(patch(app,changed),503,"service_unavailable")
        assert call(app,"GET",f"{BASE}/note-drafts/{saved['id']}").json()==changed
    finally:
        tea01_database.execute("DELETE FROM course_membership WHERE course_id=%s AND user_id='demo-teacher-other'",(COURSE,));tea01_database.commit()


def test_tea03_migration_backfill_downgrade_and_existing_rows(tea01_database):
    import psycopg
    base=os.environ["TEA01_TEST_DATABASE_URL"]
    schema="tea03_migrate_"+uuid.uuid4().hex
    raw=base.replace("postgresql+psycopg://","postgresql://",1)
    env=dict(os.environ);parts=urlsplit(base);query=dict(parse_qsl(parts.query));query["options"]=f"-csearch_path={schema}";env["DATABASE_URL"]=urlunsplit(parts._replace(query=urlencode(query)))
    def migration(*args):subprocess.run([sys.executable,"-m","alembic",*args],env=env,check=True,capture_output=True,text=True)
    with psycopg.connect(raw,autocommit=True) as conn:
        conn.execute(f'CREATE SCHEMA "{schema}"')
        try:
            migration("upgrade","20261101_tea02")
            conn.execute(f'SET search_path TO "{schema}"')
            conn.execute('INSERT INTO "user"(id,display_name,role) VALUES(\'demo-teacher\',\'Teacher\',\'teacher\')')
            conn.execute("INSERT INTO course(id,title) VALUES(%s,'Course')",(COURSE,))
            mid,nid=uuid.uuid4(),uuid.uuid4()
            conn.execute("INSERT INTO material(id,course_id,uploaded_by,title,original_filename,media_type,size_bytes,storage_key) VALUES(%s,%s,'demo-teacher','Source','a.txt','text/plain',1,'private')",(mid,COURSE))
            conn.execute("INSERT INTO study_note_draft(id,course_id,source_material_id,created_by,title,content,created_at) VALUES(%s,%s,%s,'demo-teacher','Old title','Keep text','2026-11-01T10:00:00Z')",(nid,COURSE,mid))
            migration("upgrade","20261102_tea02_mcqs")
            row=conn.execute("SELECT title,content,source_title,version,created_at,updated_at,created_by,updated_by FROM study_note_draft WHERE id=%s",(nid,)).fetchone()
            assert row[:4]==("Old title","Keep text","Old title",1)
            assert row[4]==row[5] and row[6]==row[7]=="demo-teacher"
            for sql in ["UPDATE study_note_draft SET version=0", "UPDATE study_note_draft SET source_title=NULL", "UPDATE study_note_draft SET updated_by='unknown'"]:
                with pytest.raises(psycopg.Error):conn.execute(sql)
            migration("downgrade","20261101_tea02")
            assert conn.execute("SELECT title,content FROM study_note_draft WHERE id=%s",(nid,)).fetchone()==("Old title","Keep text")
            migration("upgrade","20261102_tea02_mcqs")
            assert conn.execute("SELECT source_title,version FROM study_note_draft WHERE id=%s",(nid,)).fetchone()==("Old title",1)
        finally:
            conn.execute("SET search_path TO public");conn.execute(f'DROP SCHEMA "{schema}" CASCADE')


@pytest.mark.parametrize("invalid", ["bad\x00text", "bad\ud800text", "bad\udffftext"])
def test_tea03_unstorable_unicode_is_validation_error(notes, invalid):
    app, _, _, saved=draft(notes)
    for field in ("title", "content"):
        body={"title":"Good title","content":"Good content","version":1,field:invalid}
        response=call(app,"PATCH",f"{BASE}/note-drafts/{saved['id']}",content=json.dumps(body),headers={"Content-Type":"application/json"})
        error(response,422,"validation_error")
    assert call(app,"GET",f"{BASE}/note-drafts/{saved['id']}").json()==saved

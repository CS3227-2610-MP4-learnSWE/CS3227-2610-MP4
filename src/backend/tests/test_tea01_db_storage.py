"""Independent TEA-01 BYTEA persistence, transaction, quota and migration contract."""
import os
import subprocess
import sys
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import pytest

from test_tea01_materials import app, upload as post_upload, call, assert_error, MATERIALS_A, COURSE_A, MATERIAL_KEYS, TOPIC_A, _fresh_download
from test_tea02_notes import notes, upload, pdf_bytes, error, generate
from test_tea02_mcqs import output

MAX_FILE, QUOTA, LOCK = 10_485_760, 104_857_600, 32_272_610
LEGACY, HEAD = '20261102_tea02_mcqs', '20261102_tea01_db_storage'


def totals(db):
    db.commit()
    return db.execute('SELECT count(*), COALESCE(sum(octet_length(content)),0) FROM material_file').fetchone()


@contextmanager
def filled_to(db, target):
    marker = 'quota-' + uuid.uuid4().hex
    remaining = target - totals(db)[1]
    assert remaining >= 0
    try:
        while remaining:
            length, mid = min(remaining, MAX_FILE), uuid.uuid4()
            # Inaccurate metadata deliberately proves admission counts actual bytes.
            db.execute("INSERT INTO material(id,course_id,uploaded_by,title,original_filename,media_type,size_bytes) VALUES(%s,%s,'demo-teacher',%s,'quota.txt','text/plain',1)",(mid,COURSE_A,marker))
            db.execute("INSERT INTO material_file(material_id,content) VALUES(%s,convert_to(repeat('x',%s),'UTF8'))",(mid,length))
            remaining -= length
        db.commit()
        yield marker
    finally:
        db.rollback();db.execute('DELETE FROM material WHERE title=%s OR title LIKE %s',(marker,marker+'-%'));db.commit()


def test_tea01_db_storage_no_directory_and_restart(app, tea01_database, monkeypatch, tmp_path):
    blocked=tmp_path/'file';blocked.write_text('unchanged')
    for env in [None,str(blocked),'relative-unused-path']:
        with monkeypatch.context() as patch:
            if env is None: patch.delenv('FILE_STORAGE_DIR',raising=False)
            else: patch.setenv('FILE_STORAGE_DIR',env)
            raw='Résumé\r\nπ'.encode()
            response=post_upload(app,'résumé.txt',raw,'Database original')
            assert response.status_code == 201,response.text
            item=response.json();assert set(item)==MATERIAL_KEYS
            assert bytes(tea01_database.execute('SELECT content FROM material_file WHERE material_id=%s',(item['id'],)).fetchone()[0])==raw
            assert _fresh_download(item['id'])==raw.hex()
    assert list(tmp_path.iterdir())==[blocked] and blocked.read_text()=='unchanged'
    assert tea01_database.execute("SELECT count(*) FROM information_schema.columns WHERE table_schema=current_schema() AND table_name='material' AND column_name='storage_key'").fetchone()[0]==0


def test_tea01_db_storage_metadata_and_unauthorised_calls_do_not_fetch_bytes(app):
    from sqlalchemy import event
    from sqlalchemy.engine import Engine
    item=post_upload(app).json();sql=[]
    def capture(conn,cursor,statement,*args): sql.append(statement.lower())
    event.listen(Engine,'before_cursor_execute',capture)
    try:
        assert call(app,'GET',MATERIALS_A).status_code==200
        assert call(app,'PATCH',f"/api/teacher/materials/{item['id']}",json_body={'topic_id':TOPIC_A}).status_code==200
        for suffix,method in [('file','GET'),('note-drafts','POST'),('mcq-drafts','POST')]:
            assert_error(call(app,method,f"/api/teacher/materials/{item['id']}/{suffix}",user='demo-teacher-other'),404,'not_found')
        assert_error(call(app,'GET',f"/api/teacher/materials/{item['id']}/file",user='demo-student'),403,'forbidden')
    finally: event.remove(Engine,'before_cursor_execute',capture)
    assert not any('material_file' in statement for statement in sql),sql


@pytest.mark.parametrize('kind',['text','pdf'])
def test_tea01_db_storage_generators_use_bytes(notes, tea01_database, monkeypatch, kind):
    app,fake=notes;data=b'One\r\nTwo' if kind=='text' else pdf_bytes(['One','Two'])
    source=upload(app,data,name='input.txt' if kind=='text' else 'input.pdf')
    monkeypatch.delenv('FILE_STORAGE_DIR',raising=False)
    assert generate(app,source).status_code==201
    assert fake.calls[-1][0][1].content=='One\nTwo'
    fake.text=output()
    assert call(app,'POST',f"/api/teacher/materials/{source['id']}/mcq-drafts").status_code==201
    assert fake.calls[-1][0][1].content=='One\nTwo'
    assert bytes(tea01_database.execute('SELECT content FROM material_file WHERE material_id=%s',(source['id'],)).fetchone()[0])==data


def test_tea01_db_storage_missing_blob_is_safe_and_no_inference(notes, tea01_database):
    app,fake=notes;source=upload(app)
    tea01_database.execute('DELETE FROM material_file WHERE material_id=%s',(source['id'],));tea01_database.commit()
    assert source['id'] in [m['id'] for m in call(app,'GET',MATERIALS_A).json()]
    for suffix,method in [('file','GET'),('note-drafts','POST'),('mcq-drafts','POST')]:
        response=call(app,method,f"/api/teacher/materials/{source['id']}/{suffix}")
        assert error(response,503,'service_unavailable')['message']=='Stored material content is unavailable.'
    assert not fake.calls


def test_tea01_db_storage_exact_quota_counts_bytes(app, tea01_database):
    with filled_to(tea01_database,QUOTA-1) as marker:
        accepted=post_upload(app,content=b'x',title=marker+'-accepted')
        assert accepted.status_code==201,accepted.text
        assert totals(tea01_database)[1]==QUOTA
        before=totals(tea01_database)
        response=post_upload(app,content=b'y',title=marker+'-rejected')
        assert_error(response,413,'storage_quota_exceeded')
        assert response.json()['detail']['message']=='Upload would exceed the 100 MiB total storage limit.'
        assert totals(tea01_database)==before
        assert tea01_database.execute('SELECT count(*) FROM material WHERE title=%s',(marker+'-rejected',)).fetchone()[0]==0


def test_tea01_db_storage_concurrent_quota(app, tea01_database):
    with filled_to(tea01_database,QUOTA-1) as marker:
        with ThreadPoolExecutor(max_workers=2) as pool:
            results=list(pool.map(lambda n:post_upload(app,content=b'x',title=marker+'-'+str(n)),range(2)))
        assert sorted(r.status_code for r in results)==[201,413],[r.text for r in results]
        assert totals(tea01_database)[1]==QUOTA
        assert tea01_database.execute('SELECT count(*) FROM material WHERE title LIKE %s',(marker+'-%',)).fetchone()[0]==1


def test_tea01_db_storage_advisory_lock_and_fresh_usage(app, tea01_database):
    import psycopg
    with filled_to(tea01_database,QUOTA-1) as marker:
        with psycopg.connect(os.environ['DATABASE_URL'].replace('postgresql+psycopg://','postgresql://',1)) as holder:
            holder.execute('SELECT pg_advisory_xact_lock(%s)',(LOCK,))
            with ThreadPoolExecutor(max_workers=1) as pool:
                future=pool.submit(post_upload,app,content=b'x',title=marker+'-waiter')
                try:
                    deadline=time.monotonic()+5
                    waiting=False
                    while time.monotonic()<deadline and not future.done():
                        waiting=tea01_database.execute("SELECT EXISTS(SELECT 1 FROM pg_locks WHERE locktype='advisory' AND objid=%s AND NOT granted)",(LOCK,)).fetchone()[0]
                        if waiting: break
                        time.sleep(.01)
                    assert waiting and not future.done(),'upload did not wait on the transaction quota lock'
                    mid=uuid.uuid4()
                    holder.execute("INSERT INTO material(id,course_id,uploaded_by,title,original_filename,media_type,size_bytes) VALUES(%s,%s,'demo-teacher',%s,'lock.txt','text/plain',1)",(mid,COURSE_A,marker+'-holder'))
                    holder.execute("INSERT INTO material_file(material_id,content) VALUES(%s,'x'::bytea)",(mid,));holder.commit()
                    assert_error(future.result(timeout=10),413,'storage_quota_exceeded')
                    assert totals(tea01_database)[1]==QUOTA
                finally: holder.rollback()


@pytest.mark.parametrize('table',['material','material_file'])
def test_tea01_db_storage_insert_rollback(app, tea01_database, table):
    before=totals(tea01_database);meta=tea01_database.execute('SELECT count(*) FROM material').fetchone()[0]
    tea01_database.execute("CREATE FUNCTION db_storage_fail() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'private sentinel'; END $$")
    tea01_database.execute(f'CREATE TRIGGER db_storage_fail BEFORE INSERT ON {table} FOR EACH ROW EXECUTE FUNCTION db_storage_fail()');tea01_database.commit()
    try:
        response=post_upload(app,title='Must roll back');assert_error(response,503,'service_unavailable')
        assert 'private sentinel' not in response.text
        assert totals(tea01_database)==before
        assert tea01_database.execute('SELECT count(*) FROM material').fetchone()[0]==meta
    finally:
        tea01_database.rollback();tea01_database.execute(f'DROP TRIGGER db_storage_fail ON {table}');tea01_database.execute('DROP FUNCTION db_storage_fail()');tea01_database.commit()


def test_tea01_db_storage_commit_failure_preserves_previous(app, tea01_database, monkeypatch):
    from sqlalchemy.orm import Session
    from sqlalchemy.exc import SQLAlchemyError
    old=post_upload(app,content=b'keep').json();before=totals(tea01_database)
    def fail(*args,**kwargs): raise SQLAlchemyError('private sentinel')
    with monkeypatch.context() as patch:
        patch.setattr(Session,'commit',fail)
        assert_error(post_upload(app,content=b'not saved'),503,'service_unavailable')
    assert totals(tea01_database)==before
    assert call(app,'GET',f"/api/teacher/materials/{old['id']}/file").content==b'keep'
    assert post_upload(app,content=b'next succeeds').status_code==201


def test_tea01_db_storage_constraints_and_cascade(app, tea01_database):
    import psycopg
    source=post_upload(app).json();tea01_database.commit()
    for data in [None,b'',b'x'*(MAX_FILE+1)]:
        with pytest.raises(psycopg.Error):
            with tea01_database.transaction(): tea01_database.execute('UPDATE material_file SET content=%s WHERE material_id=%s',(data,source['id']))
    with pytest.raises(psycopg.Error):
        with tea01_database.transaction(): tea01_database.execute("INSERT INTO material_file(material_id,content) VALUES(%s,'x'::bytea)",(uuid.uuid4(),))
    tea01_database.execute('DELETE FROM material WHERE id=%s',(source['id'],));tea01_database.commit()
    assert tea01_database.execute('SELECT count(*) FROM material_file WHERE material_id=%s',(source['id'],)).fetchone()[0]==0


@contextmanager
def migration_schema():
    import psycopg
    base=os.environ['TEA01_TEST_DATABASE_URL'];schema='db_storage_migrate_'+uuid.uuid4().hex
    env=dict(os.environ);parts=urlsplit(base);query=dict(parse_qsl(parts.query));query['options']=f'-csearch_path={schema}'
    env['DATABASE_URL']=urlunsplit(parts._replace(query=urlencode(query)))
    with psycopg.connect(base.replace('postgresql+psycopg://','postgresql://',1),autocommit=True) as db:
        db.execute(f'CREATE SCHEMA "{schema}"');db.execute(f'SET search_path TO "{schema}"')
        def migrate(*args,ok=True):
            result=subprocess.run([sys.executable,'-m','alembic',*args],env=env,capture_output=True,text=True)
            assert (result.returncode==0)==ok,result.stdout+result.stderr
            return result
        try: yield db,migrate
        finally:
            db.execute('SET search_path TO public');db.execute(f'DROP SCHEMA "{schema}" CASCADE')


def test_tea01_db_storage_fresh_empty_downgrade_reupgrade(tea01_database):
    with migration_schema() as (db,migrate):
        migrate('upgrade','head')
        assert db.execute('SELECT version_num FROM alembic_version').fetchone()[0]==HEAD
        assert db.execute("SELECT to_regclass('material_file')").fetchone()[0]
        migrate('downgrade',LEGACY)
        assert db.execute("SELECT to_regclass('material_file')").fetchone()[0] is None
        assert db.execute("SELECT is_nullable FROM information_schema.columns WHERE table_schema=current_schema() AND table_name='material' AND column_name='storage_key'").fetchone()[0]=='NO'
        migrate('upgrade','head')
        assert db.execute('SELECT version_num FROM alembic_version').fetchone()[0]==HEAD


def test_tea01_db_storage_populated_upgrade_refuses_unchanged(tea01_database,tmp_path):
    original=tmp_path/'old.txt';original.write_bytes(b'keep old file')
    with migration_schema() as (db,migrate):
        migrate('upgrade',LEGACY)
        db.execute("INSERT INTO course(id,title) VALUES(%s,'Old course')",(COURSE_A,))
        db.execute('INSERT INTO "user"(id,display_name,role) VALUES(\'demo-teacher\',\'Teacher\',\'teacher\')')
        mid,nid=uuid.uuid4(),uuid.uuid4()
        db.execute("INSERT INTO material(id,course_id,uploaded_by,title,original_filename,media_type,size_bytes,storage_key) VALUES(%s,%s,'demo-teacher','Old source','old.txt','text/plain',13,'old.txt')",(mid,COURSE_A))
        db.execute("INSERT INTO study_note_draft(id,course_id,source_material_id,created_by,title,content,source_title,updated_by) VALUES(%s,%s,%s,'demo-teacher','Old draft','Keep draft','Old source','demo-teacher')",(nid,COURSE_A,mid))
        response=migrate('upgrade','head',ok=False)
        assert 'Configure a fresh empty database' in response.stderr
        assert db.execute('SELECT version_num FROM alembic_version').fetchone()[0]==LEGACY
        assert db.execute("SELECT to_regclass('material_file')").fetchone()[0] is None
        assert db.execute('SELECT title,storage_key FROM material WHERE id=%s',(mid,)).fetchone()==('Old source','old.txt')
        assert db.execute('SELECT content FROM study_note_draft WHERE id=%s',(nid,)).fetchone()[0]=='Keep draft'
        assert original.read_bytes()==b'keep old file'


def test_tea01_db_storage_populated_downgrade_refuses_without_blob(tea01_database):
    with migration_schema() as (db,migrate):
        migrate('upgrade','head')
        db.execute("INSERT INTO course(id,title) VALUES(%s,'Current')",(COURSE_A,))
        db.execute('INSERT INTO "user"(id,display_name,role) VALUES(\'demo-teacher\',\'Teacher\',\'teacher\')')
        mid=uuid.uuid4()
        db.execute("INSERT INTO material(id,course_id,uploaded_by,title,original_filename,media_type,size_bytes) VALUES(%s,%s,'demo-teacher','Current','a.txt','text/plain',1)",(mid,COURSE_A))
        response=migrate('downgrade',LEGACY,ok=False)
        assert 'Cannot downgrade file storage while materials exist' in response.stderr
        assert db.execute('SELECT version_num FROM alembic_version').fetchone()[0]==HEAD
        assert db.execute('SELECT title FROM material WHERE id=%s',(mid,)).fetchone()[0]=='Current'
        assert db.execute("SELECT to_regclass('material_file')").fetchone()[0]


def test_tea01_db_storage_upgrade_serialises_guard_with_legacy_writer(tea01_database, tmp_path):
    """The empty-table decision and removal of storage_key must be one locked operation."""
    import psycopg
    with migration_schema() as (db, migrate):
        migrate('upgrade', LEGACY)
        db.execute("INSERT INTO course(id,title) VALUES(%s,'Legacy course')", (COURSE_A,))
        db.execute('INSERT INTO "user"(id,display_name,role) VALUES(\'demo-teacher\',\'Teacher\',\'teacher\')')
        schema = db.execute('SELECT current_schema()').fetchone()[0]
        base = os.environ['TEA01_TEST_DATABASE_URL']
        parts = urlsplit(base)
        query = dict(parse_qsl(parts.query)); query['options'] = f'-csearch_path={schema}'
        env = dict(os.environ, DATABASE_URL=urlunsplit(parts._replace(query=urlencode(query))))
        ready, release = tmp_path/'guard-complete', tmp_path/'resume-migration'
        # Public Alembic operation boundary: guard already ran, destructive DDL has not.
        script = '''import sys,time
from pathlib import Path
from alembic import command
from alembic.config import Config
from alembic.operations import Operations
ready,release=map(Path,sys.argv[1:])
original=Operations.create_table
def paused(self,name,*args,**kwargs):
 if name=='material_file':
  ready.touch()
  deadline=time.monotonic()+15
  while not release.exists():
   if time.monotonic()>deadline: raise RuntimeError('test migration barrier timed out')
   time.sleep(.01)
 return original(self,name,*args,**kwargs)
Operations.create_table=paused
command.upgrade(Config('alembic.ini'),'head')
'''
        process = subprocess.Popen([sys.executable, '-c', script, str(ready), str(release)], env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        mid = uuid.uuid4()
        accepted = False
        try:
            deadline = time.monotonic()+10
            while not ready.exists() and process.poll() is None and time.monotonic()<deadline:
                time.sleep(.01)
            assert ready.exists(), 'migration never reached the post-guard DDL boundary'
            # A fixed migration keeps its table lock until commit; the writer then times out.
            with psycopg.connect(env['DATABASE_URL'].replace('postgresql+psycopg://','postgresql://',1)) as writer:
                try:
                    writer.execute("SET LOCAL lock_timeout='500ms'")
                    writer.execute("INSERT INTO material(id,course_id,uploaded_by,title,original_filename,media_type,size_bytes,storage_key) VALUES(%s,%s,'demo-teacher','Racing source','race.txt','text/plain',1,'preserve-me.txt')", (mid,COURSE_A))
                    writer.commit()
                    accepted = True
                except psycopg.errors.LockNotAvailable:
                    writer.rollback()
            release.touch()
            stdout, stderr = process.communicate(timeout=15)
            assert not (accepted and process.returncode == 0), 'migration and legacy upload both committed: original file mapping was discarded'
            if accepted:
                assert process.returncode != 0
                assert db.execute('SELECT version_num FROM alembic_version').fetchone()[0] == LEGACY
                assert db.execute('SELECT storage_key FROM material WHERE id=%s',(mid,)).fetchone()[0] == 'preserve-me.txt'
            else:
                assert process.returncode == 0, stdout+stderr
                assert db.execute('SELECT version_num FROM alembic_version').fetchone()[0] == HEAD
                assert db.execute('SELECT count(*) FROM material').fetchone()[0] == 0
        finally:
            release.touch()
            if process.poll() is None:
                try: process.communicate(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill();process.communicate()


def test_tea01_db_storage_repeatable_read_default_cannot_hide_prelock_upload(tea01_database, tmp_path):
    """A pre-lock Alembic snapshot must not hide a committed legacy source."""
    import time
    with migration_schema() as (db, migrate):
        migrate('upgrade', LEGACY)
        db.execute("INSERT INTO course(id,title) VALUES(%s,'Old course')", (COURSE_A,))
        db.execute('INSERT INTO "user"(id,display_name,role) VALUES(%s,%s,%s)', ('demo-teacher', 'Teacher', 'teacher'))
        schema = db.execute('SELECT current_schema()').fetchone()[0]
        parts = urlsplit(os.environ['TEA01_TEST_DATABASE_URL'])
        query = dict(parse_qsl(parts.query))
        query['options'] = f'-csearch_path={schema} ' r'-cdefault_transaction_isolation=repeatable\ read'
        env = dict(os.environ, DATABASE_URL=urlunsplit(parts._replace(query=urlencode(query))))
        ready, release = tmp_path / 'before-lock', tmp_path / 'release-lock'
        script = f"""
import os, time
from pathlib import Path
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from alembic import command
from alembic.config import Config
with create_engine(os.environ['DATABASE_URL']).connect() as connection:
    assert connection.get_isolation_level() == 'REPEATABLE READ'
@event.listens_for(Engine, 'before_cursor_execute')
def pause_before_lock(connection, cursor, statement, parameters, context, executemany):
    if statement.startswith('LOCK TABLE material IN ACCESS EXCLUSIVE MODE'):
        Path({str(ready)!r}).touch()
        deadline = time.monotonic() + 15
        while not Path({str(release)!r}).exists():
            if time.monotonic() > deadline:
                raise RuntimeError('migration test barrier timed out')
            time.sleep(.01)
command.upgrade(Config('alembic.ini'), 'head')
"""
        process = subprocess.Popen([sys.executable, '-c', script], env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        mid = uuid.uuid4()
        try:
            deadline = time.monotonic() + 10
            while not ready.exists() and process.poll() is None and time.monotonic() < deadline:
                time.sleep(.01)
            assert ready.exists(), 'migration did not reach the pre-lock barrier'
            db.execute("INSERT INTO material(id,course_id,uploaded_by,title,original_filename,media_type,size_bytes,storage_key) VALUES(%s,%s,'demo-teacher','Pre-lock source','keep.txt','text/plain',1,'keep.txt')", (mid, COURSE_A))
            release.touch()
            stdout, stderr = process.communicate(timeout=15)
            assert process.returncode != 0, 'stale migration snapshot missed a committed legacy upload'
            assert 'Configure a fresh empty database' in stderr, stdout + stderr
            assert db.execute('SELECT version_num FROM alembic_version').fetchone()[0] == LEGACY
            assert db.execute('SELECT storage_key FROM material WHERE id=%s', (mid,)).fetchone()[0] == 'keep.txt'
            assert db.execute("SELECT to_regclass('material_file')").fetchone()[0] is None
        finally:
            release.touch()
            if process.poll() is None:
                process.kill()
                process.communicate()

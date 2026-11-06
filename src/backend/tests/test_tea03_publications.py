"""Independent TEA-03 publication API contract; isolated PostgreSQL and fake LLM only."""
import copy
import hashlib
import json
import os
import subprocess
import sys
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import pytest

from teacher_auth import teacher_headers
from test_tea02_notes import BASE, COURSE, OTHER, call, error, upload, generate as generate_note
from test_tea02_mcqs import mcqs, generate as generate_batch

TOPIC = "33333333-3333-4333-8333-333333333333"
FOREIGN_TOPIC = "44444444-4444-4444-8444-444444444444"
META = {'id','kind','course_id','topic_id','topic_name','title','published_at'}
PRIVATE = {'source_draft_id','source_version','published_by','withdrawn'}
_DEFAULT = object()


def prepared(mcqs, kind='practice_set'):
    app, fake = mcqs
    source = upload(app, title='Publication source')
    response = (generate_note if kind == 'note' else generate_batch)(app, source)
    assert response.status_code == 201, response.text
    return app, fake, source, response.json()


def post(app, draft, kind='practice_set', payload=_DEFAULT, **kw):
    resource = 'note-drafts' if kind == 'note' else 'mcq-drafts'
    body = {'version':draft['version'], 'title':'Published testing', 'topic_id':TOPIC} if payload is _DEFAULT else payload
    # Escaped JSON can transmit adversarial lone-surrogate input without client-side failure.
    return call(app,'POST',f"{BASE}/{resource}/{draft['id']}/publish",content=json.dumps(body),headers={'Content-Type':'application/json',**kw.pop('headers',{})},**kw)


def detail(app, saved, user='demo-teacher'):
    resource = 'published-notes' if saved['kind']=='note' else 'published-practice-sets'
    return call(app,'GET',f"{BASE}/{resource}/{saved['id']}",user=user)


def assert_private_free(value):
    if isinstance(value,dict):
        for key,item in value.items():
            assert key not in {'correct_choice_index','correct_choice','correct','explanation','source_draft_id','source_question_id','source_version','published_by','withdrawn','storage_key','content'}
            assert_private_free(item)
    elif isinstance(value,list):
        for item in value:assert_private_free(item)


def student_call(app, method, path, **kw):
    return call(app,method,path,user=None,headers=teacher_headers('demo-student'),**kw)


@pytest.mark.parametrize('kind',['note','practice_set'])
def test_tea03_publications_create_retry_reopen_snapshot_and_no_llm(mcqs,tea01_database,kind):
    app,fake,source,draft=prepared(mcqs,kind)
    calls=len(fake.calls);fake.error=AssertionError('Publication must not call AI')
    r=post(app,draft,kind)
    assert r.status_code==201,r.text
    saved=r.json();assert set(saved)==META|PRIVATE|({'content'} if kind=='note' else {'question_count','questions'})
    assert saved['kind']==kind and saved['course_id']==COURSE and saved['topic_id']==TOPIC
    assert saved['source_draft_id']==draft['id'] and saved['source_version']==draft['version']
    assert saved['title']=='Published testing' and saved['topic_name']=='Testing'
    assert saved['published_by']=='demo-teacher' and saved['withdrawn'] is False
    assert saved['published_at'].endswith('Z') and str(uuid.UUID(saved['id']))==saved['id']
    assert r.headers.get('cache-control')=='no-store'
    if kind=='note':assert saved['content']==draft['content']
    else:
        assert saved['question_count']==3
        assert [q['position'] for q in saved['questions']]==[1,2,3]
        assert not {q['id'] for q in saved['questions']} & {q['id'] for q in draft['questions']}
        for original,snapshot in zip(draft['questions'],saved['questions']):
            assert set(snapshot)=={'id','position','question','choices','correct_choice_index','explanation'}
            for field in ['position','question','choices','correct_choice_index','explanation']:assert snapshot[field]==original[field]
    again=post(app,draft,kind);assert again.status_code==200 and again.json()==saved
    assert detail(app,saved).json()==saved
    listing=call(app,'GET',f'{BASE}/courses/{COURSE}/publications')
    assert listing.status_code==200
    assert next(x for x in listing.json() if x['id']==saved['id'])=={k:v for k,v in saved.items() if k not in {'content','questions'}}
    assert len(fake.calls)==calls
    changed={'title':'Private edited notes','content':'Private changed content','version':draft['version']} if kind=='note' else {'version':draft['version'],'questions':[{k:v for k,v in q.items() if k!='position'} for q in copy.deepcopy(draft['questions'])]}
    if kind!='note':changed['questions'][0]['question']='Private changed question'
    patch=call(app,'PATCH',f"{BASE}/{'note-drafts' if kind=='note' else 'mcq-drafts'}/{draft['id']}",json=changed)
    assert patch.status_code==200,patch.text
    assert detail(app,saved).json()==saved
    # Lost-response retry compares the published version BEFORE the newer private draft version.
    assert post(app,draft,kind).json()==saved
    error(post(app,{**draft,'version':patch.json()['version']},kind),409,'already_published')
    error(call(app,'DELETE',f"{BASE}/{'note-drafts' if kind=='note' else 'mcq-drafts'}/{draft['id']}?version={patch.json()['version']}"),409,'draft_in_use')
    error(call(app,'DELETE',f"{BASE}/materials/{source['id']}"),409,'material_in_use')
    script=f'''import json\nfrom fastapi.testclient import TestClient\nfrom main import app\nr=TestClient(app).get("{BASE}/{'published-notes' if kind=='note' else 'published-practice-sets'}/{saved['id']}",headers={teacher_headers()!r})\nprint(json.dumps(r.json()))'''
    assert json.loads(subprocess.run([sys.executable,'-c',script],capture_output=True,text=True,check=True).stdout)==saved


def test_tea03_publications_student_notes_reuse_existing_lessons_and_completion(mcqs):
    app,_,_,draft=prepared(mcqs,'note');saved=post(app,draft,'note').json()
    r=student_call(app,'GET',f"/api/study/lessons/{saved['id']}");assert r.status_code==200,r.text
    assert r.json()['title']==saved['title'] and r.json()['content']==draft['content']
    assert r.json()['completed'] is False
    lesson_list=student_call(app,'GET',f'/api/study/courses/{COURSE}/lessons').json()
    assert saved['id'] in {l['id'] for group in lesson_list['topics'] for l in group['lessons']}
    completed=student_call(app,'PUT',f"/api/study/lessons/{saved['id']}/completion",json={'completed':True})
    assert completed.status_code==200 and completed.json()['completed'] is True
    assert student_call(app,'GET',f"/api/study/lessons/{saved['id']}").json()['completed'] is True


def test_tea03_publications_student_set_reads_are_allowlisted_and_old_attempt_flow_unmodified(mcqs):
    app,_,_,draft=prepared(mcqs);saved=post(app,draft).json()
    r=student_call(app,'GET',f"/api/study/practice-sets/{saved['id']}");assert r.status_code==200,r.text
    assert set(r.json())=={'id','title','questions'};assert_private_free(r.json())
    for q,original in zip(r.json()['questions'],draft['questions']):
        assert set(q)=={'id','text','code','choices'} and q['code'] is None
        assert q['text']==original['question'] and [c['id'] for c in q['choices']]==list('abcd')
        assert [c['text'] for c in q['choices']]==original['choices']
    listed=student_call(app,'GET',f'/api/study/courses/{COURSE}/practice-sets')
    assert listed.status_code==200 and listed.headers.get('cache-control')=='no-store'
    item=next(x for x in listed.json() if x['id']==saved['id']);assert set(item)==META|{'question_count'};assert_private_free(item)
    # STU-02-published-sets reverses the old assertions: the code fixture is gone (not a UUID: 422) and a
    # published set is served to a member by the practice routes, with the same answer-free body.
    error(student_call(app,'GET','/api/practice-sets/intro-se-1'),422,'validation_error')
    served=student_call(app,'GET',f"/api/practice-sets/{saved['id']}");assert served.status_code==200,served.text
    assert served.json()==r.json();assert_private_free(served.json())
    started=student_call(app,'POST',f"/api/practice-sets/{saved['id']}/attempts");assert started.status_code==201,started.text
    assert started.json()['set_id']==saved['id'] and started.json()['answers']=={}
    # a teacher action (reading the teacher catalogue) does not change the student's view
    call(app,'GET',f'{BASE}/courses/{COURSE}/publications')
    assert student_call(app,'GET',f"/api/practice-sets/{saved['id']}").json()==served.json()


@pytest.mark.parametrize('kind',['note','practice_set'])
def test_tea03_publications_strict_input_normalisation_and_conflicts(mcqs,kind):
    app,_,_,draft=prepared(mcqs,kind)
    good={'version':1,'title':'Public title','topic_id':TOPIC}
    invalid=[None,[],{}, {**good,'extra':'forged'}, {**good,'course_id':OTHER}]
    for version in [True,False,'1',1.0,0,-1,None]:invalid.append({**good,'version':version})
    for title in ['', ' ', '\0', '\ud800', 'x'*201, 3, None]:invalid.append({**good,'title':title})
    for topic in [None,True,42,'bad']:invalid.append({**good,'topic_id':topic})
    for payload in invalid:
        error(post(app,draft,kind,payload),422,'validation_error')
    resource='note-drafts' if kind=='note' else 'mcq-drafts'
    duplicate=call(app,'POST',f"{BASE}/{resource}/{draft['id']}/publish",content=f'{{"version":1,"version":2,"title":"x","topic_id":"{TOPIC}"}}',headers={'Content-Type':'application/json'})
    error(duplicate,422,'validation_error')
    error(post(app,draft,kind,{**good,'topic_id':FOREIGN_TOPIC}),404,'not_found')
    error(post(app,draft,kind,{**good,'version':2}),409,'draft_conflict')
    saved=post(app,draft,kind,{**good,'title':'\u2003'+'😀'*200+'\u001c'})
    assert saved.status_code==201 and saved.json()['title']=='😀'*200
    error(post(app,draft,kind,{**good,'title':'Different'}),409,'already_published')


@pytest.mark.parametrize('kind',['note','practice_set'])
def test_tea03_publications_auth_access_order_and_no_store_errors(mcqs,tea01_database,kind):
    app,_,_,draft=prepared(mcqs,kind);resource='note-drafts' if kind=='note' else 'mcq-drafts'
    path=f"{BASE}/{resource}/{draft['id']}/publish"
    for user,status,code in [(None,401,'unauthenticated'),('demo-student',403,'forbidden'),('demo-admin',403,'forbidden'),('demo-teacher-other',404,'not_found')]:
        r=call(app,'POST',path,user=user,json={});error(r,status,code);assert r.headers.get('cache-control')=='no-store'
    error(call(app,'POST',path,user=None,headers={'X-Demo-User-Id':'demo-teacher'},json={}),401,'unauthenticated')
    error(call(app,'POST',path,user=None,headers=teacher_headers(csrf=False),json={}),403,'csrf_failed')
    error(call(app,'POST',path,headers={'Origin':'https://evil.example'},json={}),403,'csrf_failed')
    headers=teacher_headers();token=headers['Cookie'].split('=',1)[1]
    tea01_database.execute("UPDATE auth_session SET expires_at=now()-interval '1 second' WHERE token_hash=%s",(hashlib.sha256(token.encode()).hexdigest(),));tea01_database.commit()
    error(call(app,'POST',path,user=None,headers=headers,json={}),401,'unauthenticated')
    saved=post(app,draft,kind).json()
    resource='published-notes' if kind=='note' else 'published-practice-sets'
    gets=[f"{BASE}/{resource}/{saved['id']}",f'{BASE}/courses/{COURSE}/publications']
    for target in gets:
        for user,status,code in [(None,401,'unauthenticated'),('demo-student',403,'forbidden'),('demo-admin',403,'forbidden'),('demo-teacher-other',404,'not_found')]:
            r=call(app,'GET',target,user=user);error(r,status,code);assert r.headers.get('cache-control')=='no-store'
    if kind!='note':
        for target in [f"/api/study/practice-sets/{saved['id']}",f'/api/study/courses/{COURSE}/practice-sets']:
            for user,status,code in [(None,401,'unauthenticated'),('demo-teacher',403,'forbidden'),('demo-admin',403,'forbidden')]:
                r=call(app,'GET',target,user=user);error(r,status,code);assert r.headers.get('cache-control')=='no-store'
        error(student_call(app,'GET',f'/api/study/courses/{OTHER}/practice-sets'),404,'not_found')


@pytest.mark.parametrize('kind',['note','practice_set'])
def test_tea03_publications_any_managing_teacher_and_revoked_membership(mcqs,tea01_database,kind):
    app,_,_,draft=prepared(mcqs,kind)
    tea01_database.execute('INSERT INTO course_membership(course_id,user_id) VALUES(%s,%s)',(COURSE,'demo-teacher-other'));tea01_database.commit()
    try:
        response=post(app,draft,kind,user='demo-teacher-other');assert response.status_code==201
        assert response.json()['published_by']=='demo-teacher-other'
    finally:
        tea01_database.execute('DELETE FROM course_membership WHERE course_id=%s AND user_id=%s',(COURSE,'demo-teacher-other'));tea01_database.commit()
    error(detail(app,response.json(),'demo-teacher-other'),404,'not_found')


@pytest.mark.parametrize('kind',['note','practice_set'])
@pytest.mark.parametrize('same',[True,False])
def test_tea03_publications_concurrent_requests_create_one_snapshot(mcqs,tea01_database,kind,same):
    app,_,_,draft=prepared(mcqs,kind)
    payloads=[{'version':1,'title':('Same' if same else f'Title {i}'),'topic_id':TOPIC} for i in range(2)]
    with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(lambda p:post(app,draft,kind,p),payloads))
    assert sorted(r.status_code for r in results)==([200,201] if same else [201,409])
    table='published_lesson' if kind=='note' else 'published_practice_set'
    tea01_database.commit();assert tea01_database.execute(f'SELECT count(*) FROM {table} WHERE source_draft_id=%s',(draft['id'],)).fetchone()[0]==1


@pytest.mark.parametrize('kind',['note','practice_set'])
def test_tea03_publications_publish_races_edit_and_delete(mcqs,kind):
    for action in ['edit','delete']:
        app,_,_,draft=prepared(mcqs,kind)
        if kind=='note':
            body={'version':1,'title':'Private title','content':'Private corrected notes'}
        else:
            body={'version':1,'questions':[{k:v for k,v in q.items() if k!='position'} for q in copy.deepcopy(draft['questions'])]}
            body['questions'][0]['question']='Private corrected wording'
        target=f"{BASE}/{'note-drafts' if kind=='note' else 'mcq-drafts'}/{draft['id']}"
        with ThreadPoolExecutor(max_workers=2) as pool:
            published=pool.submit(post,app,draft,kind)
            other=pool.submit(call,app,'PATCH' if action=='edit' else 'DELETE',target if action=='edit' else target+'?version=1',**({'json':body} if action=='edit' else {}))
            pub,mutation=published.result(),other.result()
        assert pub.status_code in {201,404,409} and mutation.status_code in {200,204,409},(pub.text,mutation.text)
        if pub.status_code==201:
            if kind=='note':assert pub.json()['content']==draft['content']
            else:assert pub.json()['questions'][0]['question']==draft['questions'][0]['question']
            assert detail(app,pub.json()).json()==pub.json()
            if action=='delete':assert mutation.status_code==409 and mutation.json()['detail']['code']=='draft_in_use'


@pytest.mark.parametrize('kind',['note','practice_set'])
def test_tea03_publications_database_failure_rolls_back_everything(mcqs,tea01_database,kind):
    app,_,source,draft=prepared(mcqs,kind)
    table='published_lesson' if kind=='note' else 'published_practice_question'
    marker='reject_pub_'+uuid.uuid4().hex
    tea01_database.execute(f"CREATE FUNCTION {marker}() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'sentinel-private-sql'; END $$")
    tea01_database.execute(f'CREATE TRIGGER {marker} BEFORE INSERT ON {table} FOR EACH ROW EXECUTE FUNCTION {marker}()');tea01_database.commit()
    try:error(post(app,draft,kind),503,'service_unavailable')
    finally:
        tea01_database.rollback();tea01_database.execute(f'DROP TRIGGER {marker} ON {table}');tea01_database.execute(f'DROP FUNCTION {marker}()');tea01_database.commit()
    dest='published_lesson' if kind=='note' else 'published_practice_set'
    assert tea01_database.execute(f'SELECT count(*) FROM {dest} WHERE source_draft_id=%s',(draft['id'],)).fetchone()[0]==0
    assert call(app,'GET',f"{BASE}/materials/{source['id']}/file").status_code==200
    assert post(app,draft,kind).status_code==201


def legacy_note(db,draft,*,version=None,withdrawn=False,origin=True):
    ident=str(uuid.uuid4())
    db.execute("INSERT INTO published_lesson(id,course_id,topic_id,title,content,source_draft_id,published_by,source_version,withdrawn_at) VALUES(%s,%s,NULL,'Legacy note','Legacy content',%s,'demo-teacher',%s,CASE WHEN %s THEN now() ELSE NULL END)",(ident,COURSE,draft['id'] if origin else None,version,withdrawn));db.commit()
    return ident


def test_tea03_publications_legacy_null_ambiguous_and_withdrawn_notes(mcqs,tea01_database):
    app,_,_,draft=prepared(mcqs,'note')
    legacy=legacy_note(tea01_database,draft,withdrawn=True)
    error(post(app,draft,'note'),409,'already_published')
    r=call(app,'GET',f'{BASE}/published-notes/{legacy}');assert r.status_code==200
    assert r.json()['withdrawn'] is True and r.json()['source_version'] is None and r.json()['topic_id'] is None and r.json()['topic_name']=='General'
    error(student_call(app,'GET',f'/api/study/lessons/{legacy}'),404,'not_found')
    unrelated=legacy_note(tea01_database,draft,origin=False)
    assert call(app,'GET',f'{BASE}/published-notes/{unrelated}').json()['source_draft_id'] is None
    app,_,_,multiple=prepared(mcqs,'note')
    legacy_note(tea01_database,multiple,version=1);legacy_note(tea01_database,multiple,version=1)
    error(post(app,multiple,'note'),409,'already_published')


def test_tea03_publications_helper_defaults_overrides_append_and_no_commit(mcqs,tea01_database):
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from auth.dependencies import AuthUser
    from teacher_materials.models import StudyNoteDraft
    from study_lessons.publish import publish_lesson
    app,_,_,draft=prepared(mcqs,'note')
    engine=create_engine(os.environ['DATABASE_URL'])
    try:
        with Session(engine) as db:
            row=db.get(StudyNoteDraft,uuid.UUID(draft['id']))
            teacher=AuthUser('demo-teacher',None,'Teacher','teacher')
            first=publish_lesson(db,row,teacher)
            assert first.title==draft['title'] and first.source_version==1 and first.topic_id is None
            second=publish_lesson(db,row,teacher,title='Explicit title',topic_id=uuid.UUID(TOPIC))
            assert second.id!=first.id and second.title=='Explicit title' and str(second.topic_id)==TOPIC
            assert row.title==draft['title'] and row.version==1
            tea01_database.commit();assert tea01_database.execute('SELECT count(*) FROM published_lesson WHERE source_draft_id=%s',(draft['id'],)).fetchone()[0]==0
            db.commit()
        assert tea01_database.execute('SELECT count(*) FROM published_lesson WHERE source_draft_id=%s',(draft['id'],)).fetchone()[0]==2
    finally:engine.dispose()


@pytest.mark.parametrize('kind',['note','practice_set'])
def test_tea03_publications_invalid_saved_content_never_creates_partial_snapshot(mcqs,tea01_database,kind):
    app,_,_,draft=prepared(mcqs,kind)
    if kind=='note':tea01_database.execute("UPDATE study_note_draft SET content='   ' WHERE id=%s",(draft['id'],))
    else:tea01_database.execute("UPDATE mcq_draft_question SET choices='[\"same\",\"SAME\",\"c\",\"d\"]'::jsonb WHERE batch_id=%s AND position=1",(draft['id'],))
    tea01_database.commit();error(post(app,draft,kind),422,'validation_error')
    table='published_lesson' if kind=='note' else 'published_practice_set'
    assert tea01_database.execute(f'SELECT count(*) FROM {table} WHERE source_draft_id=%s',(draft['id'],)).fetchone()[0]==0


def test_tea03_publications_expired_parallel_requests_both_unauthenticated(mcqs,tea01_database,monkeypatch):
    import auth.dependencies as deps
    app,_,_,draft=prepared(mcqs)
    headers=teacher_headers();token=headers['Cookie'].split('=',1)[1]
    tea01_database.execute("UPDATE auth_session SET expires_at=now()-interval '1 second' WHERE token_hash=%s",(hashlib.sha256(token.encode()).hexdigest(),));tea01_database.commit()
    original=deps.load_session;barrier=threading.Barrier(2)
    def together(db,token):
        try:barrier.wait(timeout=5)
        except threading.BrokenBarrierError:pass
        return original(db,token)
    monkeypatch.setattr(deps,'load_session',together)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(lambda _:post(app,draft,user=None,headers=headers),range(2)))
    for r in results:error(r,401,'unauthenticated')


def test_tea03_publications_catalogue_order_and_question_reference_protection(mcqs,tea01_database):
    app,_,_,draft=prepared(mcqs);saved=post(app,draft).json()
    listing=call(app,'GET',f'{BASE}/courses/{COURSE}/publications').json()
    expected=sorted(listing,key=lambda x:x['kind'])
    expected.sort(key=lambda x:(x['published_at'],x['id']),reverse=True)
    assert listing==expected
    with pytest.raises(Exception):
        tea01_database.execute('DELETE FROM mcq_draft_question WHERE id=%s',(draft['questions'][0]['id'],))
    tea01_database.rollback()
    assert detail(app,saved).json()==saved


def test_tea03_publications_migration_preserves_legacy_and_guards_downgrade(tea01_database):
    import psycopg
    base=os.environ['TEA01_TEST_DATABASE_URL'];schema='pub_migration_'+uuid.uuid4().hex
    parts=urlsplit(base);query=dict(parse_qsl(parts.query));query['options']='-csearch_path='+schema
    url=urlunsplit(parts._replace(query=urlencode(query)));env={**os.environ,'DATABASE_URL':url}
    def migrate(*args,ok=True):
        r=subprocess.run([sys.executable,'-m','alembic',*args],env=env,capture_output=True,text=True)
        if ok:assert r.returncode==0,r.stderr
        return r
    with psycopg.connect(base.replace('postgresql+psycopg://','postgresql://',1),autocommit=True) as db:
        db.execute(f'CREATE SCHEMA "{schema}"');db.execute(f'SET search_path TO "{schema}"')
        try:
            migrate('upgrade','20261104_stu01_lessons')
            db.execute('INSERT INTO course(id,title) VALUES(%s,\'Migration course\')',(COURSE,))
            db.execute('INSERT INTO "user"(id,display_name,role) VALUES(\'demo-teacher\',\'Teacher\',\'teacher\')')
            db.execute('INSERT INTO "user"(id,display_name,role) VALUES(\'demo-student\',\'Student\',\'student\')')
            old=str(uuid.uuid4())
            db.execute("INSERT INTO published_lesson(id,course_id,title,content,published_by) VALUES(%s,%s,'Legacy','Preserve me','demo-teacher')",(old,COURSE))
            db.execute("INSERT INTO lesson_completion(user_id,lesson_id,course_id,completed,completed_at) VALUES('demo-student',%s,%s,true,now())",(old,COURSE))
            completion=db.execute('SELECT user_id,lesson_id,course_id,completed,completed_at FROM lesson_completion').fetchall()
            migrate('upgrade','20261105_tea03_publications')
            assert db.execute('SELECT user_id,lesson_id,course_id,completed,completed_at FROM lesson_completion').fetchall()==completion
            assert db.execute('SELECT version_num FROM alembic_version').fetchone()[0]=='20261105_tea03_publications'
            assert db.execute('SELECT content,source_version FROM published_lesson WHERE id=%s',(old,)).fetchone()==('Preserve me',None)
            for bad in [0,-1]:
                with pytest.raises(psycopg.Error):db.execute('UPDATE published_lesson SET source_version=%s WHERE id=%s',(bad,old))
            db.execute('UPDATE published_lesson SET source_version=1 WHERE id=%s',(old,))
            refusal=migrate('downgrade','20261104_stu01_lessons',ok=False)
            assert refusal.returncode!=0 and 'Cannot downgrade publication storage' in refusal.stderr
            assert db.execute('SELECT version_num FROM alembic_version').fetchone()[0]=='20261105_tea03_publications'
            assert db.execute('SELECT source_version,content FROM published_lesson WHERE id=%s',(old,)).fetchone()==(1,'Preserve me')
            db.execute('UPDATE published_lesson SET source_version=NULL WHERE id=%s',(old,))
            migrate('downgrade','20261104_stu01_lessons')
            assert db.execute('SELECT content FROM published_lesson WHERE id=%s',(old,)).fetchone()==('Preserve me',)
            assert db.execute('SELECT user_id,lesson_id,course_id,completed,completed_at FROM lesson_completion').fetchall()==completion
            migrate('upgrade','head')
            assert db.execute('SELECT source_version FROM published_lesson WHERE id=%s',(old,)).fetchone()==(None,)
            assert db.execute("SELECT to_regclass('published_practice_question') IS NOT NULL").fetchone()[0]
        finally:
            db.execute('SET search_path TO public');db.execute(f'DROP SCHEMA "{schema}" CASCADE')


def test_tea03_publications_migration_refuses_populated_practice_sets(mcqs,tea01_database):
    app,_,_,draft=prepared(mcqs)
    saved=post(app,draft).json()
    before=tea01_database.execute('SELECT version_num FROM alembic_version').fetchone()[0]
    result=subprocess.run([sys.executable,'-m','alembic','downgrade','20261104_stu01_lessons'],env=os.environ.copy(),capture_output=True,text=True)
    assert result.returncode!=0 and 'Cannot downgrade publication storage' in result.stderr
    assert tea01_database.execute('SELECT version_num FROM alembic_version').fetchone()[0]==before
    assert tea01_database.execute("SELECT to_regclass('published_practice_set'),to_regclass('published_practice_question')").fetchone()==('published_practice_set','published_practice_question')
    assert tea01_database.execute('SELECT count(*) FROM published_practice_question WHERE set_id=%s',(saved['id'],)).fetchone()[0]==3
    assert detail(app,saved).json()==saved

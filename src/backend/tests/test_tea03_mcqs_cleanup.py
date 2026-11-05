"""Independent TEA-03 MCQ edits/deletions; public contracts, fake LLM and isolated PG."""
import copy
import hashlib
import json
import os
import subprocess
import sys
import uuid
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager

import pytest

from teacher_auth import teacher_headers
from test_tea02_notes import BASE, COURSE, OTHER, call, upload, error
from test_tea02_mcqs import mcqs, generate, META, QKEYS


def prepared(mcqs):
    app, fake = mcqs
    source = upload(app)
    r = generate(app, source)
    assert r.status_code == 201, r.text
    return app, fake, source, r.json()


def body(batch):
    return {"version": batch["version"], "questions": [{k: v for k, v in q.items() if k != "position"} for q in copy.deepcopy(batch["questions"])]}


def patch(app, batch, payload=None, **kw):
    return call(app, "PATCH", f"{BASE}/mcq-drafts/{batch['id']}", content=json.dumps(body(batch) if payload is None else payload), headers={"Content-Type": "application/json"}, **kw)


def get(app, batch):
    return call(app, "GET", f"{BASE}/mcq-drafts/{batch['id']}")


def delete(app, kind, row, query=None, **kw):
    suffix = "" if kind == "materials" else f"?version={row['version']}"
    return call(app, "DELETE", f"{BASE}/{kind}/{row['id']}{suffix if query is None else query}", **kw)


def test_tea03_mcqs_save_metadata_persistence_immutable_ids_and_no_llm(mcqs, tea01_database):
    app, fake, source, saved = prepared(mcqs)
    assert saved['version'] == 1 and saved['updated_by'] == saved['created_by']
    assert saved['updated_at'] == saved['created_at']
    payload = body(saved)
    payload['questions'].reverse()
    payload['questions'][0]['question'] = '  Edited\r\nquestion  '
    payload['questions'][0]['choices'] = ['  α  ', 'β', 'γ', 'δ']
    payload['questions'][0]['correct_choice_index'] = 2
    payload['questions'][0]['explanation'] = '  Explanation\rnew line  '
    fake.error = AssertionError('Editing must not call LLM')
    calls = len(fake.calls)
    response = patch(app, saved, payload)
    assert response.status_code == 200, response.text
    updated = response.json()
    assert set(updated) == META | {'questions'}
    assert updated['version'] == 2 and updated['updated_at'] >= saved['updated_at']
    for key in ['id', 'course_id', 'source_material_id', 'source_title', 'created_by', 'created_at']:
        assert updated[key] == saved[key]
    assert [q['id'] for q in updated['questions']] == [q['id'] for q in saved['questions']]
    assert [q['position'] for q in updated['questions']] == [1, 2, 3]
    assert updated['questions'][2]['question'] == 'Edited\nquestion'
    assert updated['questions'][2]['choices'] == ['α', 'β', 'γ', 'δ']
    assert updated['questions'][2]['correct_choice_index'] == 2
    assert updated['questions'][2]['explanation'] == 'Explanation\nnew line'
    assert len(fake.calls) == calls
    assert get(app, saved).json() == updated
    listing = call(app, 'GET', f'{BASE}/courses/{COURSE}/mcq-drafts').json()
    assert listing == sorted(listing, key=lambda b:(b['created_at'], b['id']), reverse=True)
    assert next(b for b in listing if b['id'] == saved['id']) == {k:v for k,v in updated.items() if k != 'questions'}
    script = f'''from fastapi.testclient import TestClient
from main import app
import json
r=TestClient(app).get("{BASE}/mcq-drafts/{saved['id']}",headers={teacher_headers()!r})
print(json.dumps(r.json()))'''
    restarted = subprocess.run([sys.executable, '-c', script], check=True, capture_output=True, text=True)
    assert json.loads(restarted.stdout) == updated
    assert call(app,'GET',f"{BASE}/materials/{source['id']}/file").content == b'Functions should do one thing.'


def invalid_payloads(saved):
    good=body(saved)
    for version in [None, True, False, '1', 1.0, 0, -1]:
        yield {**copy.deepcopy(good), 'version':version}
    for extra in ['course_id','created_by','updated_by','title']:
        yield {**copy.deepcopy(good),extra:'forged'}
    for value in [None,{},[],good['questions'][:2],good['questions']*2]:
        yield {**copy.deepcopy(good),'questions':value}
    for field, value in [('question',''),('question','x'*201),('question','\0'),('question','\ud800'),('explanation',' '),('explanation','x'*201),('choices',['a','b','c']),('choices',['a','b','c','d','e']),('choices',['a','b',3,'d']),('choices',['a','b','c',' '*4]),('choices',['a'*81,'b','c','d']),('choices',['Straße','STRASSE','c','d']),('correct_choice_index',True),('correct_choice_index',1.0),('correct_choice_index','1'),('correct_choice_index',-1),('correct_choice_index',4),('id',str(uuid.uuid4())),('id','bad'),('position',1)]:
        p=copy.deepcopy(good);p['questions'][0][field]=value;yield p
    p=copy.deepcopy(good);p['questions'][1]['id']=p['questions'][0]['id'];yield p
    p=copy.deepcopy(good);p['questions'][1]['question']=p['questions'][0]['question'].upper();yield p
    for field in ['version','questions']:
        p=copy.deepcopy(good);del p[field];yield p
    for field in ['id','question','choices','correct_choice_index','explanation']:
        p=copy.deepcopy(good);del p['questions'][0][field];yield p


def test_tea03_mcqs_invalid_bodies_are_atomic(mcqs):
    app, _, _, saved = prepared(mcqs)
    for p in invalid_payloads(saved):
        error(patch(app,saved,p),422,'validation_error')
        assert get(app,saved).json()==saved
    for malformed in ['not json','[]','null','{}']:
        error(call(app,'PATCH',f"{BASE}/mcq-drafts/{saved['id']}",content=malformed),422,'validation_error')


def test_tea03_mcqs_unicode_boundaries_and_no_aggregate_model_cap(mcqs):
    app, _, _, saved = prepared(mcqs)
    p=body(saved)
    for i,q in enumerate(p['questions']):
        q['question']=str(i)+'😀'*199
        q['choices']=[str(c)+'😀'*79 for c in range(4)]
        q['explanation']='😀'*200
    assert len(json.dumps(p))>2000
    r=patch(app,saved,p)
    assert r.status_code==200,r.text
    assert len(r.json()['questions'][0]['question'])==200
    p=body(r.json());p['questions'][0]['question']+='😀'
    error(patch(app,r.json(),p),422,'validation_error')


def test_tea03_mcqs_any_managing_teacher_and_lost_response_retry(mcqs,tea01_database):
    app, _, _, saved=prepared(mcqs)
    tea01_database.execute("INSERT INTO course_membership(course_id,user_id) VALUES(%s,'demo-teacher-other')",(COURSE,));tea01_database.commit()
    try:
        r=patch(app,saved,user='demo-teacher-other')
        assert r.status_code==200,r.text
        assert r.json()['updated_by']=='demo-teacher-other' and r.json()['created_by']=='demo-teacher'
        error(patch(app,saved),409,'draft_conflict')
        error(delete(app,'mcq-drafts',saved),409,'draft_conflict')
        assert get(app,saved).json()==r.json()
        assert delete(app,'mcq-drafts',r.json(),user='demo-teacher-other').status_code==204
    finally:
        tea01_database.execute("DELETE FROM course_membership WHERE course_id=%s AND user_id='demo-teacher-other'",(COURSE,));tea01_database.commit()


def test_tea03_mcqs_concurrent_saves_and_edit_delete(mcqs):
    app, _, _, saved=prepared(mcqs)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(lambda _:patch(app,saved),range(2)))
    assert sorted(r.status_code for r in results)==[200,409]
    updated=get(app,saved).json();assert updated['version']==2
    with ThreadPoolExecutor(max_workers=2) as pool:
        edit=pool.submit(patch,app,updated);remove=pool.submit(delete,app,'mcq-drafts',updated)
        results=[edit.result(),remove.result()]
    assert sum(r.status_code in [200,204] for r in results)==1
    assert all(r.status_code in [200,204,404,409] for r in results)


@pytest.mark.parametrize('query',['','?version=0','?version=-1','?version=+1','?version=1.0','?version=true','?version=%201','?version=١','?version=1&version=1'])
def test_tea03_delete_versions_are_strict_after_access(mcqs,query):
    app, _, _, saved=prepared(mcqs)
    error(delete(app,'mcq-drafts',saved,query),422,'validation_error')
    error(delete(app,'mcq-drafts',saved,query,user='demo-teacher-other'),404,'not_found')
    assert get(app,saved).json()==saved


def test_tea03_delete_note_batch_then_source_and_unrelated_preservation(mcqs,tea01_database):
    app,fake,source,batch=prepared(mcqs)
    fake.text='Concise notes'
    r=call(app,'POST',f"{BASE}/materials/{source['id']}/note-drafts")
    assert r.status_code==201,r.text
    note=r.json();calls=len(fake.calls)
    unrelated=upload(app,b'Unrelated',title='Keep source')
    error(delete(app,'materials',source),409,'material_in_use')
    r=delete(app,'note-drafts',note);assert r.status_code==204 and r.content==b''
    error(delete(app,'note-drafts',note),404,'not_found')
    error(delete(app,'materials',source),409,'material_in_use')
    r=delete(app,'mcq-drafts',batch);assert r.status_code==204 and r.content==b''
    error(get(app,batch),404,'not_found')
    tea01_database.commit()
    assert tea01_database.execute('SELECT count(*) FROM mcq_draft_question WHERE batch_id=%s',(batch['id'],)).fetchone()[0]==0
    assert delete(app,'materials',source).status_code==204
    tea01_database.commit()
    for table,column in [('material','id'),('material_file','material_id')]:
        assert tea01_database.execute(f'SELECT count(*) FROM {table} WHERE {column}=%s',(source['id'],)).fetchone()[0]==0
    assert call(app,'GET',f"{BASE}/materials/{unrelated['id']}/file").content==b'Unrelated'
    assert len(fake.calls)==calls


@pytest.mark.parametrize('kind',['note-drafts','mcq-drafts'])
def test_tea03_draft_delete_stale_version_and_restrictive_reference(mcqs,tea01_database,kind):
    app,fake,source,batch=prepared(mcqs)
    row=batch
    if kind=='note-drafts':
        fake.text='Notes';row=call(app,'POST',f"{BASE}/materials/{source['id']}/note-drafts").json()
        edited=call(app,'PATCH',f"{BASE}/{kind}/{row['id']}",json={'title':'Updated','content':'Updated notes','version':1})
    else:edited=patch(app,row)
    assert edited.status_code==200,edited.text
    error(delete(app,kind,row),409,'draft_conflict')
    current=edited.json();table='study_note_draft' if kind=='note-drafts' else 'mcq_draft_batch'
    ref='cleanup_ref_'+uuid.uuid4().hex
    tea01_database.execute(f'CREATE TABLE {ref}(id uuid REFERENCES {table}(id))')
    tea01_database.execute(f'INSERT INTO {ref}(id) VALUES(%s)',(row['id'],));tea01_database.commit()
    try:
        error(delete(app,kind,current),409,'draft_in_use')
        assert call(app,'GET',f"{BASE}/{kind}/{row['id']}").json()==current
    finally:
        tea01_database.rollback();tea01_database.execute(f'DROP TABLE {ref}');tea01_database.commit()


def test_tea03_all_teacher_routes_cookie_role_csrf_and_demo_forgery(mcqs):
    app,_,source,batch=prepared(mcqs)
    routes=[('GET',f'{BASE}/courses'),('GET',f'{BASE}/courses/{COURSE}/topics'),('GET',f'{BASE}/courses/{COURSE}/materials'),('POST',f'{BASE}/courses/{COURSE}/materials'),('PATCH',f"{BASE}/materials/{source['id']}"),('GET',f"{BASE}/materials/{source['id']}/file"),('DELETE',f"{BASE}/materials/{source['id']}"),('POST',f"{BASE}/materials/{source['id']}/note-drafts"),('POST',f"{BASE}/materials/{source['id']}/mcq-drafts"),('GET',f'{BASE}/courses/{COURSE}/note-drafts'),('GET',f'{BASE}/courses/{COURSE}/mcq-drafts'),('GET',f"{BASE}/mcq-drafts/{batch['id']}"),('PATCH',f"{BASE}/mcq-drafts/{batch['id']}"),('DELETE',f"{BASE}/mcq-drafts/{batch['id']}?version=1")]
    for method,path in routes:
        error(call(app,method,path,user=None,headers={'X-Demo-User-Id':'demo-teacher'}),401,'unauthenticated')
        for user in ['demo-student','demo-admin']:
            error(call(app,method,path,user=user),403,'forbidden')
        if method!='GET':
            error(call(app,method,path,headers={'X-CSRF-Token':'wrong'}),403,'csrf_failed')
            error(call(app,method,path,headers={'Origin':'https://attacker.example'}),403,'csrf_failed')
    assert call(app,'GET',f'{BASE}/courses',headers={'X-Demo-User-Id':'demo-teacher-other'}).json()[0]['id']==COURSE


@pytest.mark.parametrize('action',['logout','expire','role','membership'])
@pytest.mark.parametrize('kind',['note-drafts','mcq-drafts'])
def test_tea03_session_and_access_revoked_during_generation_prevents_save(mcqs,tea01_database,action,kind):
    app,fake=mcqs;source=upload(app)
    if kind=='note-drafts':fake.text='Notes'
    headers=teacher_headers()
    token=headers['Cookie'].split('=',1)[1]
    def revoke():
        if action=='logout':tea01_database.execute('DELETE FROM auth_session WHERE token_hash=%s',(hashlib.sha256(token.encode()).hexdigest(),))
        elif action=='expire':tea01_database.execute("UPDATE auth_session SET expires_at=now()-interval '1 second' WHERE token_hash=%s",(hashlib.sha256(token.encode()).hexdigest(),))
        elif action=='role':tea01_database.execute('UPDATE "user" SET role=\'student\' WHERE id=\'demo-teacher\'')
        else:tea01_database.execute("DELETE FROM course_membership WHERE user_id='demo-teacher' AND course_id=%s",(COURSE,))
        tea01_database.commit()
    fake.hook=revoke
    try:
        r=call(app,'POST',f"{BASE}/materials/{source['id']}/{kind}",headers=headers)
        error(r,401 if action in ['logout','expire'] else 403 if action=='role' else 404,'unauthenticated' if action in ['logout','expire'] else 'forbidden' if action=='role' else 'not_found')
        tea01_database.commit()
        table='study_note_draft' if kind=='note-drafts' else 'mcq_draft_batch'
        assert tea01_database.execute(f'SELECT count(*) FROM {table} WHERE source_material_id=%s',(source['id'],)).fetchone()[0]==0
    finally:
        tea01_database.execute('UPDATE "user" SET role=\'teacher\' WHERE id=\'demo-teacher\'')
        tea01_database.execute("INSERT INTO course_membership(course_id,user_id) VALUES(%s,'demo-teacher') ON CONFLICT DO NOTHING",(COURSE,));tea01_database.commit()


def test_tea03_source_deleted_while_llm_runs_and_generation_wins_protects_source(mcqs):
    app,fake=mcqs;source=upload(app)
    fake.hook=lambda: delete(app,'materials',source).status_code==204 or pytest.fail('unused source should delete')
    error(generate(app,source),404,'not_found')
    fake.hook=None;source=upload(app);batch=generate(app,source).json()
    error(delete(app,'materials',source),409,'material_in_use')
    assert get(app,batch).status_code==200


@pytest.mark.parametrize('operation',['edit','delete_batch','delete_note','delete_source'])
def test_tea03_database_failure_rolls_back_all_mutations(mcqs,tea01_database,operation):
    app,fake,source,batch=prepared(mcqs)
    target=batch;table='mcq_draft_batch';event='UPDATE' if operation=='edit' else 'DELETE'
    if operation=='delete_note':
        fake.text='Notes';target=call(app,'POST',f"{BASE}/materials/{source['id']}/note-drafts").json();table='study_note_draft'
    if operation=='delete_source':
        source=upload(app,b'Keep bytes');table='material'
    name='cleanup_failure_'+uuid.uuid4().hex
    tea01_database.execute(f"CREATE FUNCTION {name}() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'private sentinel'; END $$")
    tea01_database.execute(f'CREATE TRIGGER {name} BEFORE {event} ON {table} FOR EACH ROW EXECUTE FUNCTION {name}()');tea01_database.commit()
    try:
        r=patch(app,batch) if operation=='edit' else delete(app,'materials',source) if operation=='delete_source' else delete(app,'note-drafts' if operation=='delete_note' else 'mcq-drafts',target)
        error(r,503,'service_unavailable');assert 'private sentinel' not in r.text
        if operation=='delete_source':assert call(app,'GET',f"{BASE}/materials/{source['id']}/file").content==b'Keep bytes'
        else:assert call(app,'GET',f"{BASE}/{'note-drafts' if operation=='delete_note' else 'mcq-drafts'}/{target['id']}").json()==target
    finally:
        tea01_database.rollback();tea01_database.execute(f'DROP TRIGGER {name} ON {table}');tea01_database.execute(f'DROP FUNCTION {name}()');tea01_database.commit()


def test_tea03_delete_releases_quota_for_next_upload(mcqs,tea01_database):
    from test_tea01_db_storage import filled_to, QUOTA, totals
    app,_=mcqs
    source=upload(app,b'x'*100)
    with filled_to(tea01_database,QUOTA) as marker:
        error(call(app,'POST',f'{BASE}/courses/{COURSE}/materials',files={'file':('one.txt',b'x')},data={'title':marker+'-blocked'}),413,'storage_quota_exceeded')
        assert delete(app,'materials',source).status_code==204
        assert totals(tea01_database)[1]==QUOTA-100
        accepted=call(app,'POST',f'{BASE}/courses/{COURSE}/materials',files={'file':('replacement.txt',b'x'*100)},data={'title':marker+'-replacement'})
        assert accepted.status_code==201,accepted.text
        assert totals(tea01_database)[1]==QUOTA


def test_tea03_topic_patch_waiting_for_body_then_source_deleted_returns_404(mcqs):
    import asyncio
    import httpx
    app,_=mcqs;source=upload(app)
    headers=teacher_headers()
    async def scenario():
        started=asyncio.Event();resume=asyncio.Event()
        async def chunks():
            started.set();await resume.wait();yield b'{"topic_id":null}'
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app,raise_app_exceptions=False),base_url='http://test') as c:
            task=asyncio.create_task(c.patch(f"{BASE}/materials/{source['id']}",headers={**headers,'Content-Type':'application/json'},content=chunks()))
            await started.wait()
            removed=await c.delete(f"{BASE}/materials/{source['id']}",headers=headers)
            resume.set();return removed,await task
    removed,assigned=asyncio.run(scenario())
    assert removed.status_code==204,removed.text
    error(assigned,404,'not_found')


def test_tea03_mcq_edit_migration_backfill_down_up_and_constraints(tea01_database):
    import psycopg
    from auth_helpers import schema_url
    base=os.environ['TEA01_TEST_DATABASE_URL'];schema='cleanup_migrate_'+uuid.uuid4().hex
    env={**os.environ,'DATABASE_URL':schema_url(base,schema)}
    def migrate(*args):
        subprocess.run([sys.executable,'-m','alembic',*args],env=env,check=True,capture_output=True,text=True)
    with psycopg.connect(base.replace('postgresql+psycopg://','postgresql://',1),autocommit=True) as db:
        db.execute(f'CREATE SCHEMA "{schema}"')
        try:
            migrate('upgrade','20261103_shr01_auth');db.execute(f'SET search_path TO "{schema}"')
            db.execute("INSERT INTO course(id,title) VALUES(%s,'Test')",(COURSE,))
            db.execute('INSERT INTO "user"(id,display_name,role) VALUES(\'demo-teacher\',\'Teacher\',\'teacher\')')
            mid,bid=uuid.uuid4(),uuid.uuid4()
            db.execute("INSERT INTO material(id,course_id,uploaded_by,title,original_filename,media_type,size_bytes) VALUES(%s,%s,'demo-teacher','Source','s.txt','text/plain',1)",(mid,COURSE))
            db.execute("INSERT INTO mcq_draft_batch(id,course_id,source_material_id,created_by,source_title,created_at) VALUES(%s,%s,%s,'demo-teacher','Original','2026-11-01T00:00:00Z')",(bid,COURSE,mid))
            migrate('upgrade','20261104_tea03_mcq_edit')
            row=db.execute('SELECT version,created_at,updated_at,created_by,updated_by FROM mcq_draft_batch WHERE id=%s',(bid,)).fetchone()
            assert row[0]==1 and row[1]==row[2] and row[3]==row[4]=='demo-teacher'
            assert db.execute('SELECT version_num FROM alembic_version').fetchone()[0]=='20261104_tea03_mcq_edit'
            for column,value in [('version',0),('version',None),('updated_by','missing'),('updated_by',None),('updated_at',None)]:
                with pytest.raises(psycopg.Error):db.execute(f'UPDATE mcq_draft_batch SET {column}=%s WHERE id=%s',(value,bid))
            migrate('downgrade','20261103_shr01_auth')
            assert db.execute('SELECT source_title FROM mcq_draft_batch WHERE id=%s',(bid,)).fetchone()[0]=='Original'
            migrate('upgrade','head')
            assert db.execute('SELECT version,updated_by FROM mcq_draft_batch WHERE id=%s',(bid,)).fetchone()==(1,'demo-teacher')
        finally:
            db.execute('SET search_path TO public');db.execute(f'DROP SCHEMA "{schema}" CASCADE')


def test_tea03_mcq_question_reference_blocks_whole_batch_delete_atomically(mcqs,tea01_database):
    app,_,_,batch=prepared(mcqs)
    ref='question_ref_'+uuid.uuid4().hex
    tea01_database.execute(f'CREATE TABLE {ref}(question_id uuid REFERENCES mcq_draft_question(id))')
    # Reference the final question so rollback must also restore any earlier child deletions.
    tea01_database.execute(f'INSERT INTO {ref} VALUES(%s)',(batch['questions'][-1]['id'],));tea01_database.commit()
    try:
        error(delete(app,'mcq-drafts',batch),409,'draft_in_use')
        assert get(app,batch).json()==batch
    finally:
        tea01_database.rollback();tea01_database.execute(f'DROP TABLE {ref}');tea01_database.commit()


def test_tea03_concurrent_expired_cookie_deletes_both_return_401_without_mutation(mcqs,tea01_database,monkeypatch):
    import threading
    import auth.dependencies as dependencies
    app,_=mcqs
    source=upload(app,b'Expired requests must not delete this file')
    headers=teacher_headers()
    token=headers['Cookie'].split('=',1)[1]
    tea01_database.execute("UPDATE auth_session SET expires_at=now()-interval '1 second' WHERE token_hash=%s",(hashlib.sha256(token.encode()).hexdigest(),))
    tea01_database.commit()
    rendezvous=threading.Barrier(2)
    original=dependencies.load_session
    def load_together(db,raw_token):
        # Allow fixes which serialize authentication before this call to make progress too.
        try:rendezvous.wait(timeout=5)
        except threading.BrokenBarrierError:pass
        return original(db,raw_token)
    monkeypatch.setattr(dependencies,'load_session',load_together)
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures=[pool.submit(call,app,'DELETE',f"{BASE}/materials/{source['id']}",user=None,headers=headers) for _ in range(2)]
        responses=[future.result(timeout=15) for future in futures]
    for response in responses:error(response,401,'unauthenticated')
    monkeypatch.setattr(dependencies,'load_session',original)
    assert call(app,'GET',f"{BASE}/materials/{source['id']}/file").content==b'Expired requests must not delete this file'

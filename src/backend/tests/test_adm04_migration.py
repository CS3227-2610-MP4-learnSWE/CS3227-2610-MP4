"""ADM-04 additive migration preserves populated survey/progress/account history."""
import os
import uuid
import psycopg
import pytest
from auth_helpers import psycopg_url
from test_shr01_seed_migration import Isolated


@pytest.fixture
def isolated_adm04():
    base=os.environ.get('TEA01_TEST_DATABASE_URL')
    if not base:pytest.skip('TEA01_TEST_DATABASE_URL is not set')
    schema='adm04_'+uuid.uuid4().hex
    with psycopg.connect(psycopg_url(base),autocommit=True) as conn:conn.execute(f'CREATE SCHEMA "{schema}"')
    try:yield Isolated(base,schema)
    finally:
        with psycopg.connect(psycopg_url(base),autocommit=True) as conn:conn.execute(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE')


def test_adm04_ac03_12_additive_upgrade_preserves_populated_feedback_and_progress(isolated_adm04):
    db=isolated_adm04
    db.migrate('upgrade','20261107_adm02_feedback');db.seed_teacher()
    db.sql("INSERT INTO \"user\"(id,display_name,role,access_status) VALUES ('adm04-history-admin','Historical administrator','admin','enabled')")
    db.sql('INSERT INTO "user"(id,display_name,role,access_status) VALUES (\'adm04-retain\',\'Retained\',\'student\',\'disabled\')')
    form,response,inbox=[str(uuid.uuid4()) for _ in range(3)]
    db.sql("INSERT INTO feedback_forms(id,title,description,association,questions,state,version,created_by,created_at,updated_at,published_at,audience_role) VALUES (%s,'Historical feedback','Retain',NULL,'[]','open',2,'adm04-history-admin',now(),now(),now(),'student')",(form,))
    db.sql("INSERT INTO feedback_recipients(form_id,user_id,display_name_snapshot,role_snapshot,inbox_id,read_at) VALUES (%s,'adm04-retain','Retained','student',%s,now())",(form,inbox))
    db.sql("INSERT INTO feedback_responses(id,form_id,user_id,display_name_snapshot,submitted_at,form_snapshot,answers) VALUES (%s,%s,'adm04-retain','Retained',now(),'{\"title\":\"Historical feedback\"}','[]')",(response,form))
    db.sql("INSERT INTO practice_attempt(id,student_id,set_id,status) VALUES ('adm04-retain-attempt','adm04-retain','intro-se-1','in_progress')")
    tables=['user','course_membership','practice_attempt','feedback_forms','feedback_recipients','feedback_responses','feedback_response_drafts','ai_usage_coverage']
    before={t:db.sql(f'SELECT t::text FROM "{t}" t ORDER BY t::text') for t in tables}
    db.migrate('upgrade','20261107_adm04_messaging')
    for table,rows in before.items():assert db.sql(f'SELECT t::text FROM "{table}" t ORDER BY t::text')==rows
    for table in ['admin_message_previews','admin_messages','admin_message_deliveries']:
        assert db.sql('SELECT to_regclass(%s)::text',(table,))[0][0]==table
        assert db.sql(f'SELECT count(*) FROM {table}')[0][0]==0
    db.migrate('upgrade','20261107_adm04_messaging')
    assert db.sql('SELECT count(*) FROM feedback_responses WHERE id=%s',(response,))[0][0]==1

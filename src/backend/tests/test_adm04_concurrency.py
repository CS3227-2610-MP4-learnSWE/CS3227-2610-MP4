"""ADM-04 real database concurrency, revocation ordering and atomicity."""
from concurrent.futures import ThreadPoolExecutor
import os
import time

import psycopg
from sqlalchemy import create_engine
import pytest

from auth_helpers import call, sql, psycopg_url
from adm02_helpers import actor, race, uid
from adm04_helpers import ADMIN, INBOX, PREVIEWS, announcement, preview, delivered, messages, send, check_error, counts


def test_adm04_ac12_eight_concurrent_confirmations_share_one_receipt_and_delivery():
    admin, user = actor('admin'), actor()
    value = preview(admin, announcement([user]))
    replies = race(*[lambda: send(admin, value) for _ in range(8)])
    assert [r.status_code for r in replies] == [200]*8, [(r.status_code,r.text) for r in replies]
    assert len({r.json()['message_id'] for r in replies}) == 1
    assert len({r.text for r in replies}) == 1
    assert messages(user)['unread_count'] == 1
    assert sql('SELECT count(*) FROM admin_messages WHERE preview_id=%s',(value['id'],))[0][0] == 1
    assert sql('SELECT count(*) FROM admin_message_deliveries WHERE recipient_id=%s',(str(user),))[0][0] == 1


def test_adm04_ac12_concurrent_read_and_send_replays_never_erase_first_read():
    admin, user = actor('admin'), actor()
    value = preview(admin, announcement([user])); receipt = delivered(admin, value)
    mid = messages(user)['items'][0]['id']
    replies = race(lambda: send(admin,value), lambda: call('POST',f'{INBOX}/{mid}/read',user,{}),
                   lambda: call('POST',f'{INBOX}/{mid}/read',user,{}), lambda: send(admin,value))
    assert [r.status_code for r in replies] == [200]*4
    assert replies[1].json() == replies[2].json()
    assert replies[0].json() == replies[3].json() == receipt
    assert messages(user)['items'][0]['read_at'] == replies[1].json()['read_at']
    assert messages(user)['unread_count'] == 0


def test_adm04_ac12_failed_second_delivery_rolls_back_entire_fanout_then_same_review_recovers():
    admin, a, b = actor('admin'), actor(), actor()
    value = preview(admin, announcement([a,b]))
    trigger = 'adm04_fail_'+uid().replace('-','')
    before = counts()
    # Test-only constraint at the database boundary fails after another insert,
    # proving transaction rollback rather than mocking the service under test.
    sql(f'''CREATE FUNCTION {trigger}() RETURNS trigger LANGUAGE plpgsql AS $$
      BEGIN IF EXISTS(SELECT 1 FROM admin_message_deliveries WHERE recipient_id IN ('{a}','{b}'))
      THEN RAISE EXCEPTION 'ADM04_PRIVATE_TEST_FAILURE'; END IF; RETURN NEW; END $$''')
    sql(f'CREATE TRIGGER {trigger} BEFORE INSERT ON admin_message_deliveries FOR EACH ROW EXECUTE FUNCTION {trigger}()')
    try:
        reply = send(admin,value)
        assert reply.status_code in (500,503), reply.text
        assert reply.json()['detail']['code'] in ('MESSAGING_ERROR','MESSAGING_UNAVAILABLE')
        assert 'ADM04_PRIVATE_TEST_FAILURE' not in reply.text
        assert counts() == before
        assert messages(a)['items'] == messages(b)['items'] == []
    finally:
        sql(f'DROP TRIGGER IF EXISTS {trigger} ON admin_message_deliveries')
        sql(f'DROP FUNCTION IF EXISTS {trigger}()')
    delivered(admin,value)
    assert messages(a)['unread_count'] == messages(b)['unread_count'] == 1


def blocked_on(observer, pid, marker, timeout=10):
    deadline = time.monotonic()+timeout
    while time.monotonic()<deadline:
        rows=observer.execute('SELECT pid FROM pg_stat_activity WHERE %s=ANY(pg_blocking_pids(pid)) AND application_name=%s', (pid,marker)).fetchall()
        if rows:return rows[0][0]
        time.sleep(.02)
    raise AssertionError('Expected real request never reached the deliberately held database lock')


@pytest.mark.parametrize('revoked', ['recipient','sender'])
def test_adm04_ac11_12_disable_completed_before_waiting_send_validation_cannot_deliver(monkeypatch, revoked):
    administrator, sender, user = actor('admin'), actor('admin'), actor()
    value=preview(sender,announcement([user]))
    target=user if revoked=='recipient' else sender
    holder=psycopg.connect(psycopg_url()); observer=psycopg.connect(psycopg_url(),autocommit=True)
    marker='adm04_revoke_'+uid().replace('-','')
    engine=create_engine(os.environ['DATABASE_URL'],pool_size=3,max_overflow=0,
                         connect_args={'application_name':marker})
    monkeypatch.setattr('auth.db.engine_for',lambda _url:engine)
    pool=ThreadPoolExecutor(max_workers=2)
    try:
        holder.execute('SELECT id FROM "user" WHERE id=%s FOR UPDATE',(str(target),))
        disabling=pool.submit(call,'PUT',f'/api/admin/accounts/{target}/status',administrator,{'status':'disabled'})
        disable_pid=blocked_on(observer,holder.info.backend_pid,marker)
        sending=pool.submit(send,sender,value)
        # The send must wait behind the in-flight account mutation, then recheck.
        blocked_on(observer,disable_pid,marker)
        assert not sending.done()
        holder.commit()
        reply=disabling.result(timeout=15);assert reply.status_code==200,reply.text
        check_error(sending.result(timeout=15),409 if revoked=='recipient' else 401,
                    'AUDIENCE_CHANGED' if revoked=='recipient' else 'unauthenticated')
        assert sql('SELECT count(*) FROM admin_messages WHERE preview_id=%s',(value['id'],))[0][0]==0
        assert sql('SELECT count(*) FROM admin_message_deliveries WHERE recipient_id=%s',(str(user),))[0][0]==0
    finally:
        holder.rollback();holder.close();observer.close();pool.shutdown(wait=True);engine.dispose()


def test_adm04_ac12_single_connection_pool_parallel_preview_send_and_read_has_no_nested_checkout(monkeypatch):
    admin,user=actor('admin'),actor()
    value=preview(admin,announcement([user]))
    engine=create_engine(os.environ['DATABASE_URL'],pool_size=1,max_overflow=0,pool_timeout=3)
    monkeypatch.setattr('auth.db.engine_for',lambda _url:engine)
    try:
        replies=race(lambda:send(admin,value),lambda:send(admin,value),lambda:messages(user))
        assert replies[0].status_code==replies[1].status_code==200
        assert replies[0].json()==replies[1].json()
        assert messages(user)['unread_count']==1
        assert engine.pool.checkedout()==0
    finally:engine.dispose()

"""Real MySQL regression: simultaneous cold logins and competing for one used item.

Creates/drops only a new random test_week9_ schema and starts its own loopback server.
No payment, production accounts, production keys, or existing service are touched.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import secrets
import shutil
import socket
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args()
    out=args.output.resolve();out.mkdir(parents=True,exist_ok=False)
    from dotenv import dotenv_values
    from sqlalchemy import create_engine,text
    from sqlalchemy.engine import URL
    from cryptography.fernet import Fernet
    import requests
    c=dotenv_values(ROOT/'.env')
    url=URL.create('mysql+pymysql',username=c.get('DB_USERNAME','root'),password=c.get('DB_PASSWORD',''),
                   host=c.get('DB_HOST','localhost'),port=int(c.get('DB_PORT',3306)))
    admin=create_engine(url,isolation_level='AUTOCOMMIT')
    database='test_week9_'+secrets.token_hex(8)
    work=ROOT/'dist-releases'/('week9-correctness-'+secrets.token_hex(8))
    work.mkdir(parents=True)
    for folder in ('src','api_service'):
        shutil.copytree(ROOT/folder,work/folder,ignore=shutil.ignore_patterns('__pycache__','*.pyc','*.log'))
    (work/'scripts').mkdir()
    for name in ('week9_server.py','week9_settings.py'):shutil.copy2(ROOT/'scripts'/name,work/'scripts'/name)
    env=dict(os.environ)
    env.update({'DB_NAME':database,'DB_USERNAME':url.username,'DB_PASSWORD':url.password or '',
                'DB_HOST':url.host,'DB_PORT':str(url.port),'DATABASE_URL':url.set(database=database).render_as_string(hide_password=False),
                'DJANGO_SECRET_KEY':secrets.token_urlsafe(48),'JWT_SECRET_KEY':secrets.token_urlsafe(48),
                'MTLS_PROXY_SECRET':secrets.token_urlsafe(48),'MFA_ENCRYPTION_KEY':Fernet.generate_key().decode(),
                'BANK_CARD_ENCRYPTION_KEY':Fernet.generate_key().decode(),'TUNNEL_KEY_ENCRYPTION_KEY':Fernet.generate_key().decode(),
                'SM3_PBKDF2_ITERATIONS':'2500','PYTHONIOENCODING':'utf-8','PYTHONUNBUFFERED':'1','DEBUG':'False'})
    created=False;server=None;report={}
    def request(method,path,body=None,token=None):
        headers={'Authorization':'Bearer '+token} if token else {}
        return requests.request(method,'http://127.0.0.1:8770'+path,json=body,headers=headers,timeout=30)
    try:
        with admin.connect() as db:
            db.execute(text(f'CREATE DATABASE `{database}` CHARACTER SET utf8mb4'));created=True
        with (out/'server-console.txt').open('w',encoding='utf-8') as log:
            server=subprocess.Popen([sys.executable,str(work/'scripts/week9_server.py'),'--port','8770','--output',str(out)],
                                    cwd=work,env=env,stdout=log,stderr=subprocess.STDOUT)
            for _ in range(240):
                if server.poll() is not None:raise RuntimeError('Isolated server failed')
                try:
                    if (out/'ready.json').exists():
                        with socket.create_connection(('127.0.0.1',8770),timeout=1):break
                except OSError:pass
                time.sleep(.5)
            else:raise RuntimeError('Readiness timeout')
            def login(uid):return request('POST','/api/auth/login',{'username':f'perf_user_{uid}','password':'Week9PerfOnly123!'})
            # Repeat the missing-state race, instead of relying on one lucky schedule.
            import threading
            cold_rounds=[]
            for trial in range(5):
                with admin.connect() as db:
                    db.execute(text(f'DELETE FROM `{database}`.security_states WHERE user_id IN (1,2)'))
                login_barrier=threading.Barrier(2)
                def cold_login(uid):
                    login_barrier.wait(timeout=10)
                    return login(uid)
                with ThreadPoolExecutor(max_workers=2) as pool: responses=list(pool.map(cold_login,(1,2)))
                cold_rounds.append([r.status_code for r in responses])
                report['concurrent_cold_login_rounds']=cold_rounds
                assert all(r.status_code==200 and r.json()['code']==0 for r in responses),'Cold login failed'
            original_secret=Fernet(env['MFA_ENCRYPTION_KEY'].encode()).encrypt(b'ABCDEFGHIJKLMNOP').decode()
            with admin.connect() as db:
                db.execute(text(f'UPDATE `{database}`.security_states SET enabled=1, secret=:secret, version=7, failures=2, last_step=123, recovery_hashes=:recovery WHERE user_id=1'),
                           {'secret':original_secret,'recovery':'["fixture-recovery-hash"]'})
            responses[0]=login(1)
            assert responses[0].status_code==200
            with admin.connect() as db:
                state=db.execute(text(f'SELECT enabled,secret,version,failures,last_step,recovery_hashes FROM `{database}`.security_states WHERE user_id=1')).one()
            report['existing_mfa_and_version_preserved']=tuple(state)==(1,original_secret,7,2,123,'["fixture-recovery-hash"]')
            assert report['existing_mfa_and_version_preserved']
            tokens=[r.json()['data']['token'] for r in responses]
            hot=request('GET','/api/products/10000').json()['data']['stock_quantity']
            assert hot==1
            for token in tokens:
                response=request('POST','/api/cart',{'product_id':10000,'quantity':1},token)
                assert response.status_code==200 and response.json()['code']==0
            barrier=threading.Barrier(2)
            def buy(token):
                barrier.wait(timeout=10)
                return request('POST','/api/orders',{},token)
            with ThreadPoolExecutor(max_workers=2) as pool: purchases=list(pool.map(buy,tokens))
            report['competing_order_status']=sorted(r.status_code for r in purchases)
            assert report['competing_order_status']==[200,400],'Expected one winner, one out-of-stock rejection'
            with admin.connect() as db:
                count=db.execute(text(f'SELECT COUNT(*) FROM `{database}`.orders')).scalar_one()
                stock=db.execute(text(f'SELECT stock_quantity FROM `{database}`.products WHERE product_id=10000')).scalar_one()
                items=db.execute(text(f'SELECT SUM(quantity) FROM `{database}`.order_items WHERE product_id=10000')).scalar_one()
            report['persisted']={'orders':count,'stock':stock,'sold_quantity':int(items)}
            assert count==1 and stock==0 and items==1,'Overselling or duplicate order'
            report['cached_detail_stock_after_purchase']=request('GET','/api/products/10000').json()['data']['stock_quantity']
            assert report['cached_detail_stock_after_purchase']==0,'Stale cache after purchase'
            report['normal_user_admin_access']=request('GET','/api/admin/users',token=tokens[0]).status_code
            assert report['normal_user_admin_access']==403
            report['anonymous_order']=request('POST','/api/orders',{}).status_code
            assert report['anonymous_order']==401
            response=request('POST','/api/auth/login',{'username':'perf_user_1','password':'WrongPassword123!'})
            report['wrong_password_status']=response.status_code
            assert response.status_code in (400,401)
            report['passed']=True
    finally:
        if server is not None:
            server.terminate()
            try:server.wait(timeout=15)
            except subprocess.TimeoutExpired:server.kill();server.wait(timeout=10)
        if created:
            with admin.connect() as db:db.execute(text(f'DROP DATABASE `{database}`'))
            report['owned_test_database_dropped']=True
        admin.dispose()
        (out/'results.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()

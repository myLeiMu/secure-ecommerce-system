"""JMeter comparison on fresh isolated MySQL databases, never the business database.

Example: python scripts/week9_perf.py --source-ref 3a81987 --output docs/evidence/week9/before
Use --source-ref WORKTREE for the optimized working copy. No production service is restarted.
"""
import argparse
import csv
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import io
import json
import math
import os
from pathlib import Path
import platform
import re
import secrets
import shutil
import socket
import subprocess
import sys
import threading
import time
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from week8_perf import summarize, write_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-ref', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--jmeter', default='D:/apache-jmeter-5.6.3/apache-jmeter-5.6.3/bin/jmeter.bat')
    parser.add_argument('--loops', type=int, default=25)
    parser.add_argument('--repeats', type=int, default=3)
    parser.add_argument('--smoke-only', action='store_true')
    parser.add_argument('--allow-errors', action='store_true', help='Retain all failing baseline samples; never mark them successful')
    parser.add_argument('--resume', action='store_true', help='Verify the saved environment and resume incomplete rounds only')
    parser.add_argument('--port', type=int, default=8769)
    parser.add_argument('--cache', choices=('locmem', 'redis'), default='locmem')
    parser.add_argument('--threads', type=int, default=2)
    parser.add_argument('--pause-ms', type=int, default=1000)
    parser.add_argument('--capacity', action='store_true', help='Isolated loopback only: omit IP limiter, preserve all other middleware')
    args = parser.parse_args()
    if not 2 <= args.threads <= 60 or not 0 <= args.pause_ms <= 10000:
        parser.error('threads must be 2..60 and pause-ms 0..10000')
    if (args.threads != 2 or args.capacity) and args.source_ref != 'WORKTREE':
        parser.error('Extended fixture requires reviewed WORKTREE')
    if not 1 <= args.loops <= 100 or not 1 <= args.repeats <= 5:
        parser.error('loops must be 1..100 and repeats 1..5')
    output = (ROOT / args.output).resolve()
    if args.resume:
        if not (output/'environment.json').is_file(): parser.error('No saved run to resume')
    else:
        output.mkdir(parents=True, exist_ok=False)
    from dotenv import dotenv_values
    from sqlalchemy import create_engine, text
    from sqlalchemy.engine import URL
    from cryptography.fernet import Fernet
    import psutil
    config = dotenv_values(ROOT / '.env')
    redis_client = None
    redis_metadata = None
    if args.cache == 'redis':
        if args.source_ref != 'WORKTREE':
            parser.error('Redis experiment supports reviewed WORKTREE only; legacy cache code may delete unrelated keys')
        import redis
        redis_client = redis.Redis(host=config.get('REDIS_HOST', 'localhost'),
            port=int(config.get('REDIS_PORT', 6379)), db=int(config.get('REDIS_DB', 0)),
            password=config.get('REDIS_PASSWORD') or None, socket_connect_timeout=5, socket_timeout=5)
        redis_client.ping()
        info = redis_client.info('server')
        redis_metadata = {'version': info['redis_version'], 'host': config.get('REDIS_HOST', 'localhost'),
                          'port': int(config.get('REDIS_PORT',6379)), 'db': int(config.get('REDIS_DB',0)),
                          'isolation': 'random test_week9_ prefix per round; no FLUSHDB/FLUSHALL',
                          'client_version': importlib.metadata.version('redis'),
                          'django_redis_version': importlib.metadata.version('django-redis')}
    def clean_redis(prefix, folder):
        if redis_client is None: return
        if not re.fullmatch(r'test_week9_[0-9a-f]{16}', prefix): raise RuntimeError('Unsafe Redis cleanup prefix')
        keys = list(redis_client.scan_iter(match=prefix+':*', count=100))
        for i in range(0,len(keys),100): redis_client.delete(*keys[i:i+100])
        remaining = sum(1 for _ in redis_client.scan_iter(match=prefix+':*', count=100))
        write_json(folder/'redis-cleanup.json', {'prefix':prefix,'deleted_keys':len(keys),'remaining_keys':remaining})
        if remaining: raise RuntimeError('Redis experiment keys remain')
    admin_url = URL.create('mysql+pymysql', username=config.get('DB_USERNAME', 'root'),
                          password=config.get('DB_PASSWORD', ''), host=config.get('DB_HOST', 'localhost'),
                          port=int(config.get('DB_PORT', 3306)))
    admin = create_engine(admin_url, connect_args={'connect_timeout':5}, isolation_level='AUTOCOMMIT')
    with admin.connect() as c:
        mysql = c.execute(text('SELECT VERSION()')).scalar_one()
    scratch = ROOT / 'dist-releases' / ('week9-' + secrets.token_hex(8))
    scratch.mkdir(parents=True, exist_ok=False)
    source = scratch / 'source'
    source.mkdir()
    if args.source_ref == 'WORKTREE':
        for folder in ('src', 'api_service'):
            shutil.copytree(ROOT / folder, source / folder, ignore=shutil.ignore_patterns('__pycache__', '*.pyc', '*.log'))
    else:
        archive = subprocess.check_output(['git', 'archive', '--format=zip', args.source_ref], cwd=ROOT)
        with zipfile.ZipFile(io.BytesIO(archive)) as z:
            for entry in z.infolist():
                if entry.filename.startswith(('src/', 'api_service/')):
                    target = (source / entry.filename).resolve()
                    if not target.is_relative_to(source.resolve()): raise RuntimeError('Unsafe archive member')
                    z.extract(entry, source)
    (source / 'scripts').mkdir(exist_ok=True)
    for name in ('week9_server.py', 'week9_settings.py'):
        shutil.copy2(ROOT / 'scripts' / name, source / 'scripts' / name)
    jmx = scratch / 'week9-comparison.jmx'
    shutil.copy2(ROOT / 'performance/week9-comparison.jmx', jmx)
    files = sorted(p for p in source.rglob('*.py') if '__pycache__' not in p.parts)
    manifest = {
        'time_utc':datetime.now(timezone.utc).isoformat(), 'source_ref':args.source_ref,
        'git_head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        'source_sha256':{p.relative_to(source).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in files},
        'jmx_sha256':hashlib.sha256(jmx.read_bytes()).hexdigest(),
        'python':sys.version, 'platform':platform.platform(), 'cpu_logical':os.cpu_count(),
        'ram_bytes':psutil.virtual_memory().total, 'mysql':mysql,
        'java':subprocess.run(['java','-version'],capture_output=True,text=True).stderr.strip(),
        'jmeter':subprocess.run([args.jmeter,'-v'],capture_output=True,text=True).stdout.strip(),
        'packages':{n:importlib.metadata.version(n) for n in ('Django','SQLAlchemy','PyMySQL','waitress','cryptography','gmssl','psutil')},
        'fixed':{'server':'Waitress 1 process, 4 threads', 'entry':f'http://127.0.0.1:{args.port}',
                 'database':'MySQL fresh dedicated schema per round, same instance, InnoDB',
                 'cache':'LocMem, 2000 entries, same before/after; Redis deliberately not used',
                 'pool_size':10,'max_overflow':20,'pool_timeout':30,'pool_pre_ping':True,
                 'users':args.threads+4,'independent_trading_threads':args.threads,'products':20000,'categories':102,'stock_per_item':1,
                 'password_algorithm':'PBKDF2-HMAC-SM3','password_iterations':2500,'dklen':32,
                 'threads':args.threads,'ramp_seconds':2,'pause_before_each_sample_ms':args.pause_ms,
                 'warmup_loops_per_thread':2,'loops_per_thread':args.loops,'repeats':args.repeats,
                 'rate_limit':'unchanged 100/IP/60s, products exempt; no forged client IP',
                 'measurement':'nearest-rank p95 including failures; throughput = samples / per-label elapsed window'},
        'limitations':['Dedicated loopback API experiment; does not measure nginx/TLS or production capacity.',
                       'MySQL process is shared with other projects; machine CPU is recorded, avoid concurrent loads.',
                       'Credentials and key files stay in ignored temporary snapshot directories.']}
    manifest['cache_backend'] = args.cache
    if args.capacity:
        manifest['fixed']['rate_limit'] = 'CAPACITY ONLY: IP limiter omitted in isolated loopback settings; auth/audit/stock checks retained'
    manifest['redis'] = redis_metadata
    if args.cache == 'redis':
        manifest['fixed']['cache'] = 'WSL Redis; isolated prefix per round; payload TTL 300 seconds'
    if args.resume:
        previous = json.loads((output/'environment.json').read_text(encoding='utf-8'))
        if previous.get('redis') != redis_metadata: raise RuntimeError('Redis environment changed')
        for key in ('fixed','source_ref','source_sha256','jmx_sha256','python','platform','mysql','java','jmeter','packages'):
            if previous[key] != manifest[key]: raise RuntimeError('Cannot resume changed environment: '+key)
        previous.setdefault('resume_times_utc',[]).append(manifest['time_utc'])
        write_json(output/'environment.json',previous)
    else:
        write_json(output / 'environment.json', manifest)
    results = json.loads((output/'results.json').read_text(encoding='utf-8')) if args.resume and (output/'results.json').exists() else {}
    phases = [('smoke',1)] if args.smoke_only else [('smoke',1)] + [(f'round-{i}',args.loops) for i in range(1,args.repeats+1)]
    for phase, loops in phases:
        if phase in results:
            print(phase+': preserved previously completed round',flush=True)
            continue
        phase_dir = output / phase
        if phase_dir.exists():
            if not args.resume: raise RuntimeError('Phase directory already exists')
            ready = phase_dir/'ready.json'
            if ready.exists() and not (phase_dir/'cleanup.json').exists():
                old_database = json.loads(ready.read_text())['database']
                if not re.fullmatch(r'test_week9_[0-9a-f]{16}',old_database): raise RuntimeError('Invalid owned test schema')
                with admin.connect() as c:
                    active = c.execute(text('SELECT COUNT(*) FROM information_schema.processlist WHERE DB=:name'),{'name':old_database}).scalar_one()
                    if active: raise RuntimeError('Previous test database is still in use; do not resume concurrently')
                    exists = c.execute(text('SELECT COUNT(*) FROM information_schema.schemata WHERE SCHEMA_NAME=:name'),{'name':old_database}).scalar_one()
                    if exists:
                        users = c.execute(text(f'SELECT username FROM `{old_database}`.users ORDER BY user_id')).scalars().all()
                        expected_users = ['perf_user_1','perf_user_2','perf_seller','admin','testuser','perf_auditor'] + [f'perf_user_{i}' for i in range(3,args.threads+1)]
                        if users != expected_users:
                            raise RuntimeError('Unexpected interrupted fixture; refusing cleanup')
                        c.execute(text(f'DROP DATABASE `{old_database}`'))
                write_json(phase_dir/'cleanup.json',{'database':old_database,'owned_test_database_dropped':True,'reason':'interrupted run, no live connections'})
            if ready.exists():
                clean_redis(json.loads(ready.read_text())['database'], phase_dir)
            preserved = output/(phase+'-interrupted-'+str(int(time.time())))
            if not phase_dir.resolve().is_relative_to(ROOT.resolve()) or not preserved.resolve().is_relative_to(ROOT.resolve()):
                raise RuntimeError('Resume move must stay inside the project workspace')
            phase_dir.rename(preserved)
        phase_dir.mkdir()
        database = 'test_week9_' + secrets.token_hex(8)
        created = False
        server = None
        stop = threading.Event()
        resources = []
        stage = ['startup']
        counters_before = {}
        successful_orders = [0]
        env = dict(os.environ)
        env.update({'PYTHONIOENCODING':'utf-8','PYTHONUNBUFFERED':'1', 'DB_NAME':database,
                    'DB_HOST':str(admin_url.host), 'DB_PORT':str(admin_url.port),
                    'DB_USERNAME':admin_url.username, 'DB_PASSWORD':admin_url.password or '',
                    'DATABASE_URL':admin_url.set(database=database).render_as_string(hide_password=False),
                    'DJANGO_SECRET_KEY':secrets.token_urlsafe(48),'JWT_SECRET_KEY':secrets.token_urlsafe(48),
                    'MTLS_PROXY_SECRET':secrets.token_urlsafe(48),'MFA_ENCRYPTION_KEY':Fernet.generate_key().decode(),
                    'BANK_CARD_ENCRYPTION_KEY':Fernet.generate_key().decode(),
                    'TUNNEL_KEY_ENCRYPTION_KEY':Fernet.generate_key().decode(), 'SM3_PBKDF2_ITERATIONS':'2500',
                    'DEBUG':'False','ECOMMERCE_MERCHANT_PRIVATE_KEY':'','BANK_MERCHANT_PRIVATE_KEYS':''})
        env['WEEK9_CACHE'] = args.cache
        env['WEEK9_THREADS'] = str(args.threads)
        env['WEEK9_CAPACITY'] = '1' if args.capacity else '0'
        env['WEEK9_CACHE_PREFIX'] = database
        if redis_client is not None:
            for key, default in (('REDIS_HOST','localhost'),('REDIS_PORT','6379'),('REDIS_DB','0'),('REDIS_PASSWORD','')):
                env[key] = config.get(key) or default
        def state():
            path = phase_dir / 'server-state.json'
            return json.loads(path.read_text()) if path.exists() else {}
        def jmeter(label, count, product_start):
            stage[0] = 'warmup' if label == 'warmup' else 'measurement'
            jtl = phase_dir / (label + '.jtl')
            command = [args.jmeter,'-n','-t',str(jmx),'-l',str(jtl),'-j',str(phase_dir/(label+'.log')),
                       f'-Jport={args.port}',f'-Jthreads={args.threads}',f'-Jloops={count}','-Jramp=2',f'-Jpause_ms={args.pause_ms}',
                       f'-Jproduct_start={product_start}','-Jjmeter.save.saveservice.output_format=csv',
                       '-Jjmeter.save.saveservice.response_data=false','-Jjmeter.save.saveservice.response_data.on_error=false',
                       '-Jjmeter.save.saveservice.samplerData=false','-Jjmeter.save.saveservice.requestHeaders=false',
                       '-Jjmeter.save.saveservice.responseHeaders=false','-Jjmeter.save.saveservice.assertion_results_failure_message=true']
            with (phase_dir/(label+'-console.txt')).open('w',encoding='utf-8') as log:
                done = subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,timeout=2400,cwd=scratch)
            metrics = summarize(jtl)
            successful_orders[0] += metrics['order']['samples'] - metrics['order']['errors']
            write_json(phase_dir/(label+'-metrics.json'),metrics)
            if done.returncode or any(v['samples'] != count*args.threads or (v['errors'] and not args.allow_errors) for v in metrics.values()):
                raise RuntimeError(f'{phase}/{label}: failed samples; inspect retained evidence')
            return metrics
        try:
            with admin.connect() as c:
                # No IF NOT EXISTS: never take ownership of somebody else's database.
                c.execute(text(f'CREATE DATABASE `{database}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci'))
                created = True
            log = (phase_dir/'server-console.txt').open('w',encoding='utf-8')
            server = subprocess.Popen([sys.executable,str(source/'scripts/week9_server.py'),'--port',str(args.port),
                                       '--output',str(phase_dir)],cwd=source,env=env,stdout=log,stderr=subprocess.STDOUT)
            process = psutil.Process(server.pid)
            def monitor():
                process.cpu_percent(None)
                while not stop.wait(1):
                    try:
                        resources.append({'time_utc':datetime.now(timezone.utc).isoformat(),'stage':stage[0],
                                          'backend_cpu_percent_one_core':process.cpu_percent(None),
                                          'backend_rss_bytes':process.memory_info().rss,
                                          'machine_cpu_percent':psutil.cpu_percent(None)})
                    except psutil.NoSuchProcess: return
            sampler = threading.Thread(target=monitor,daemon=True)
            sampler.start()
            deadline = time.monotonic()+120
            while time.monotonic()<deadline:
                if server.poll() is not None: raise RuntimeError('Benchmark server exited; inspect its log')
                if (phase_dir/'ready.json').exists():
                    try:
                        with socket.create_connection(('127.0.0.1', args.port), timeout=2):
                            break
                    except OSError:
                        pass
                time.sleep(.5)
            else: raise RuntimeError('Benchmark server readiness timeout')
            if phase!='smoke': jmeter('warmup',2,1)
            time.sleep(1.2)
            counters_before = state()
            metrics = jmeter('measurement',loops,1 if phase=='smoke' else 2*args.threads+1)
            time.sleep(1.2)
            final = state()
            if redis_client is not None:
                redis_client.ping()
                keys = list(redis_client.scan_iter(match=database+':*', count=100))
                write_json(phase_dir/'redis-evidence.json', {'ping':True,'prefix':database,
                    'key_count':len(keys), 'product_payload_keys':sum(b'product_v2:' in key for key in keys),
                    'payload_ttl_seconds':[redis_client.ttl(key) for key in keys if b'product_v2:' in key][:10],
                    'note':'Only this round namespace inspected; no values or credentials exported.'})
                if not any(b'product_v2:' in key for key in keys): raise RuntimeError('No real Redis product cache evidence')
            if final.get('cache_errors',0): raise RuntimeError('Cache read errors; do not accept fallback-only results')
            expected = successful_orders[0]
            persistence = {'expected_orders':expected,'orders':final.get('orders'),'cart_items':final.get('cart_items'),
                           'negative_stock':final.get('negative_stock')}
            if (final.get('orders') != expected or final.get('negative_stock') != 0
                    or (final.get('cart_items') != 0 and not args.allow_errors)):
                raise RuntimeError(f'{phase}: persistence validation failed')
            results[phase] = {'metrics':metrics,'persistence':persistence,
                              'sql_delta':{k:round(final.get(k,0)-counters_before.get(k,0),3)
                                           for k in ('queries','sql_ms','ddl','checkouts','checkins','cache_hits','cache_misses','cache_errors')},
                              'peak_pool_checked_out_including_monitor':final.get('peak_checked_out')}
            write_json(output/'results.json',results)
            status = 'COMPLETED WITH ERRORS' if any(v['errors'] for v in metrics.values()) else 'PASS'
            print(phase + ': ' + status + ' ' + json.dumps({k:v['p95_ms'] for k,v in metrics.items()}),flush=True)
        finally:
            stop.set()
            if server is not None:
                server.terminate()
                try: server.wait(timeout=15)
                except subprocess.TimeoutExpired: server.kill(); server.wait(timeout=10)
                log.close()
            write_json(phase_dir/'resources.json',resources)
            if created:
                # This exact unpredictable schema was created by this process above.
                with admin.connect() as c: c.execute(text(f'DROP DATABASE `{database}`'))
                write_json(phase_dir/'cleanup.json',{'database':database,'owned_test_database_dropped':True})
            clean_redis(database, phase_dir)
    admin.dispose()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

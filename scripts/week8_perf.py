"""Run genuine JMeter against a disposable, clearly labelled integration environment.

No production users/orders/keys are touched. This is not the MySQL/nginx capacity
baseline: that environment must be measured separately before week 9 comparison.
"""
import argparse
import csv
import hashlib
import importlib.metadata
import json
import logging
import math
import os
import platform
import shutil
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from wsgiref.simple_server import WSGIRequestHandler, make_server

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def write_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')


def summarize(path):
    rows = list(csv.DictReader(path.open(encoding='utf-8-sig', newline='')))
    metrics = {}
    for label in ('login', 'products', 'order', 'setup_cart'):
        group = [r for r in rows if r['label'] == label]
        if not group:
            raise RuntimeError(f'Missing sampler: {label}')
        elapsed = sorted(int(r['elapsed']) for r in group)
        errors = sum(r['success'].lower() != 'true' for r in group)
        duration = (max(int(r['timeStamp']) + int(r['elapsed']) for r in group) - min(int(r['timeStamp']) for r in group)) / 1000
        metrics[label] = {'samples': len(group), 'errors': errors, 'error_rate_percent': errors / len(group) * 100,
                          'p95_ms': elapsed[math.ceil(.95 * len(group)) - 1],
                          'mean_ms': round(sum(elapsed) / len(elapsed), 3),
                          'throughput_rps': round(len(group) / max(duration, .001), 4)}
    return metrics


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', default='docs/evidence/week8/performance')
    parser.add_argument('--jmeter', default=shutil.which('jmeter.bat') or shutil.which('jmeter'))
    parser.add_argument('--port', type=int, default=8768)
    parser.add_argument('--loops', type=int, default=10)
    parser.add_argument('--repeats', type=int, default=3)
    args = parser.parse_args()
    if not args.jmeter:
        parser.error('JMeter not found; pass --jmeter with its absolute path')
    if not (1 <= args.loops <= 20 and 1 <= args.repeats <= 5):
        parser.error('This bounded week 8 run supports loops 1..20 and repeats 1..5')
    output = (ROOT / args.output).resolve()
    output.mkdir(parents=True, exist_ok=False)  # Never overwrite earlier evidence.
    import psutil
    from api_service.tests.test_course_security import CourseSecurityTests, SessionLocal, User, Product, Order
    from src.Data_base.models.order import CartItem
    from django.core.wsgi import get_wsgi_application
    from django.core.cache import cache
    # Fixture import sets 50 rounds for unit tests: restore the real default here.
    os.environ['SM3_PBKDF2_ITERATIONS'] = '2500'
    logging.disable(logging.INFO)
    class QuietHandler(WSGIRequestHandler):
        def log_message(self, *args):
            pass
    packages = {d.metadata['Name']: d.version for d in importlib.metadata.distributions() if d.metadata.get('Name')}
    java_version = subprocess.run(['java', '-version'], capture_output=True, text=True).stderr.strip()
    jmeter_version = subprocess.run([args.jmeter, '-v'], capture_output=True, text=True, timeout=60).stdout.strip()
    source_files = sorted(p for parent in ('src', 'api_service', 'performance', 'scripts') for p in (ROOT / parent).rglob('*')
                          if p.suffix in ('.py', '.jmx') and '__pycache__' not in p.parts)
    hashes = {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in source_files}
    manifest = {'time_utc': datetime.now(timezone.utc).isoformat(), 'python': sys.version, 'platform': platform.platform(),
                'cpu_logical': os.cpu_count(), 'ram_bytes': psutil.virtual_memory().total,
                'java_version': java_version, 'jmeter_version': jmeter_version,
                'node_version': subprocess.check_output(['node', '--version'], text=True).strip(),
                'git_head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                'source_sha256': hashes, 'packages': packages, 'entry': f'http://127.0.0.1:{args.port}',
                'web_server': 'Python wsgiref, 1 process / 1 request at a time', 'database': 'disposable shared-memory SQLite',
                'cache': 'Django LocMem; Redis disabled by test settings', 'users': 5, 'products': 1000,
                'roles': ['normal (buyer and seller)', 'admin', 'auditor'], 'stock_per_item': 1,
                'password_sm3_pbkdf2_iterations': 2500, 'rate_limit': 'unchanged: 100/IP/60s; products exempt',
                'threads': 1, 'ramp_seconds': 1, 'pause_before_each_sample_ms': 1000,
                'measured_loops': args.loops, 'repeats': args.repeats, 'warmup_loops': 2,
                'target_samplers': ['login', 'products', 'order'], 'setup_sampler_excluded': 'setup_cart',
                'p95_method': 'nearest-rank, ceil(0.95*n), includes error samples',
                'throughput_method': 'per label: samples / (last sample end - first sample start), seconds',
                'limit': 'Week 8 low-load integration reference only, not nginx/MySQL production capacity or week 9 optimization proof.'}
    write_json(output / 'environment.json', manifest)
    results = {}
    phases = [('smoke', 1)] + [(f'baseline-{i}', args.loops) for i in range(1, args.repeats + 1)]
    for name, loops in phases:
        fixture = CourseSecurityTests()
        fixture.setUp()
        try:
            with SessionLocal.begin() as db:
                for user in db.query(User):
                    if user.user_role == 'merchant':
                        user.user_role = 'normal'
                db.get(Product, 1).stock_quantity = 1
                db.add_all(Product(product_id=i, sku=f'perf-{i}', product_name=f'Used item {i}', sale_price=10,
                                   stock_quantity=1, category_id=1, seller_id=2, is_active=True,
                                   is_available=True, status='active') for i in range(2, 1001))
            cache.clear()
            server = make_server('127.0.0.1', args.port, get_wsgi_application(), handler_class=QuietHandler)
            finished = threading.Event()
            resources = []
            stage = ['startup']
            failures = []
            process = psutil.Process()
            def monitor():
                process.cpu_percent(None)
                while not finished.wait(1):
                    resources.append({'time_utc': datetime.now(timezone.utc).isoformat(),
                                      'stage': stage[0],
                                      'backend_cpu_percent_one_core': process.cpu_percent(None),
                                      'backend_rss_bytes': process.memory_info().rss})
            def run_jmeter(label, count, product_start=1):
                stage[0] = 'warmup' if label.endswith('-warmup') else 'measurement'
                jtl = output / f'{label}.jtl'
                command = [args.jmeter, '-n', '-t', str(ROOT / 'performance/week8-baseline.jmx'),
                           '-l', str(jtl), '-j', str(output / f'{label}.log'),
                           f'-Jport={args.port}', '-Jthreads=1', f'-Jloops={count}', '-Jpause_ms=1000',
                           f'-Jproduct_start={product_start}',
                           '-Jjmeter.save.saveservice.output_format=csv',
                           '-Jjmeter.save.saveservice.response_data=false',
                           '-Jjmeter.save.saveservice.response_data.on_error=false',
                           '-Jjmeter.save.saveservice.samplerData=false',
                           '-Jjmeter.save.saveservice.requestHeaders=false',
                           '-Jjmeter.save.saveservice.responseHeaders=false',
                           '-Jjmeter.save.saveservice.assertion_results_failure_message=true']
                with (output / f'{label}-console.txt').open('w', encoding='utf-8') as log:
                    done = subprocess.run(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, timeout=600)
                if done.returncode != 0 or not jtl.exists():
                    raise RuntimeError(f'JMeter failed: {label}; inspect console log')
                metrics = summarize(jtl)
                if any(v['samples'] != count or v['errors'] for v in metrics.values()):
                    write_json(output / f'{label}-failed-metrics.json', metrics)
                    raise RuntimeError(f'JMeter assertions failed: {label}; inspect JTL')
                return metrics
            def client():
                try:
                    if name != 'smoke':
                        run_jmeter(name + '-warmup', 2)
                    results[name] = run_jmeter(name, loops, 1 if name == 'smoke' else 3)
                except Exception as exc:
                    failures.append(str(exc))
                finally:
                    finished.set()
                    server.shutdown()
            worker = threading.Thread(target=client, daemon=True)
            sampler = threading.Thread(target=monitor, daemon=True)
            worker.start()
            sampler.start()
            server.serve_forever(poll_interval=.1)
            worker.join()
            sampler.join()
            server.server_close()
            write_json(output / f'{name}-resources.json', resources)
            if failures:
                raise RuntimeError('; '.join(failures))
            with SessionLocal() as db:
                expected = loops + (2 if name != 'smoke' else 0)
                actual = db.query(Order).filter(Order.user_id == 1).count() - 1
                remaining = db.query(CartItem).filter(CartItem.user_id == 1).count()
                if actual != expected or remaining != 0:
                    raise RuntimeError('Order persistence/cart cleanup check failed')
                results[name]['persistence'] = {'new_orders': actual, 'expected': expected, 'cart_items': remaining}
            write_json(output / 'results.json', results)
            print(f'{name}: PASS, {loops} samples per target API', flush=True)
        finally:
            fixture.doCleanups()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

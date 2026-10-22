"""Isolated real Django/Waitress/MySQL server. Invoked by week9_perf, not production.

The launcher supplies a new empty database and a private snapshot working directory.
Only startup fixtures/settings differ; views, auth, crypto and SQL run unmodified.
"""
import argparse
import hashlib
import json
import logging
import os
from pathlib import Path
import sys
import threading
import time
from datetime import datetime, timedelta

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'api_service'), str(ROOT / 'scripts')]


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--port', type=int, default=8769)
    p.add_argument('--output', required=True)
    args = p.parse_args()
    out = Path(args.output)
    if not os.environ.get('DB_NAME', '').startswith('test_week9_'):
        raise RuntimeError('Only isolated test_week9_ databases are permitted')
    # Existing security middleware stays enabled, but this dedicated loopback
    # experiment measures API processing without TLS or the nginx transport.
    os.environ['DJANGO_SETTINGS_MODULE'] = 'week9_settings'
    (ROOT / 'api_service' / 'logs').mkdir(exist_ok=True)
    import django
    django.setup()
    from src.Data_base.database import Base, engine, SessionLocal
    from src.Data_base.models.user import User
    from src.Data_base.models.product import Category, Product
    from src.Data_base.models.order import Order, CartItem
    from src.Data_base.models import security  # register the security tables
    from sqlalchemy import event, text
    Base.metadata.create_all(engine)
    # Seed using the standard algorithm and cost, independent of code under test.
    salt = '11112222333344445555666677778888'
    digest = hashlib.pbkdf2_hmac('sm3', b'Week9PerfOnly123!', bytes.fromhex(salt), 2500).hex()
    with SessionLocal.begin() as db:
        for i, (name, role) in enumerate([('perf_user_1', 'normal'), ('perf_user_2', 'normal'),
                                        ('perf_seller', 'normal'), ('admin', 'admin'),
                                        ('testuser', 'normal'), ('perf_auditor', 'auditor')], 1):
            db.add(User(user_id=i, username=name, phone=f'13990000{i:03}', email=f'{name}@example.invalid',
                        pass_word=digest, salt=salt, user_role=role, is_active=True, is_verified=True))
        for i in range(1, 101):
            db.add(Category(category_id=i, category_name=f'Perf category {i}', is_active=True))
        # Satisfy legacy demo checks identically without creating extra objects during measurement.
        db.add(Category(category_id=101, category_name='电子产品', is_active=True))
        db.add(Category(category_id=102, category_name='手机', parent_category_id=101, is_active=True))
        db.flush()
        seed = datetime(2026, 1, 1)
        rows = []
        for i in range(1, 20001):
            sku = ['IPHONE13-001', 'SAMSUNGS22-001', 'XIAOMI13-001'][i-19998] if i >= 19998 else f'week9-{i}'
            rows.append(dict(product_id=i, sku=sku, product_name=f'Used item {i}', description='Fictional secondhand item',
                             sale_price=10, stock_quantity=1, category_id=(i-1) % 100 + 1, seller_id=3,
                             status='active', is_active=True, is_available=True, created_at=seed + timedelta(seconds=i)))
        db.execute(Product.__table__.insert(), rows)
    with engine.connect() as connection:
        query = ('SELECT product_id FROM products WHERE category_id=1 AND is_active=1 '
                 'AND is_available=1 AND stock_quantity>0 ORDER BY created_at DESC LIMIT 50')
        plan = [dict(r) for r in connection.execute(text('EXPLAIN ' + query)).mappings()]
        (out / 'query-plan.json').write_text(json.dumps(plan, default=str, indent=2), encoding='utf-8')
    counters = {'queries': 0, 'sql_ms': 0.0, 'ddl': 0, 'checkouts': 0, 'checkins': 0, 'checked_out': 0, 'peak_checked_out': 0}
    lock = threading.Lock()
    @event.listens_for(engine, 'before_cursor_execute')
    def before(conn, cursor, statement, params, context, many):
        context._week9_started = time.perf_counter()
    @event.listens_for(engine, 'after_cursor_execute')
    def after(conn, cursor, statement, params, context, many):
        if context.execution_options.get('week9_observer'):
            return
        with lock:
            counters['queries'] += 1
            counters['sql_ms'] += (time.perf_counter() - context._week9_started) * 1000
            counters['ddl'] += int(statement.lstrip().upper().startswith(('ALTER ', 'CREATE ', 'DROP ')))
    @event.listens_for(engine, 'checkout')
    def checkout(*unused):
        with lock:
            counters['checkouts'] += 1
            counters['checked_out'] += 1
            counters['peak_checked_out'] = max(counters['peak_checked_out'], counters['checked_out'])
    @event.listens_for(engine, 'checkin')
    def checkin(*unused):
        with lock:
            counters['checkins'] += 1
            counters['checked_out'] -= 1
    def observe():
        while True:
            try:
                with engine.connect().execution_options(week9_observer=True) as connection:
                    row = connection.execute(text('SELECT COUNT(*) FROM orders WHERE user_id IN (1,2)')).scalar_one()
                    cart = connection.execute(text('SELECT COUNT(*) FROM cart_items WHERE user_id IN (1,2)')).scalar_one()
                    negative = connection.execute(text('SELECT COUNT(*) FROM products WHERE stock_quantity<0')).scalar_one()
                with lock: report = dict(counters)
                report.update(orders=row, cart_items=cart, negative_stock=negative, time=time.time())
                target = out / 'server-state.json'
                temp = out / 'server-state.tmp'
                temp.write_text(json.dumps(report, indent=2), encoding='utf-8')
                temp.replace(target)
            except Exception as exc:
                (out / 'monitor-error.txt').write_text(type(exc).__name__, encoding='utf-8')
            time.sleep(1)
    threading.Thread(target=observe, daemon=True).start()
    logging.disable(logging.INFO)
    from django.core.wsgi import get_wsgi_application
    from waitress import serve
    app = get_wsgi_application()
    (out / 'ready.json').write_text(json.dumps({'database':os.environ['DB_NAME'], 'fixture_products':20000,
                                              'users':6, 'password_iterations':2500}), encoding='utf-8')
    serve(app, listen=f'127.0.0.1:{args.port}', threads=4)


if __name__ == '__main__':
    main()

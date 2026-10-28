"""Add the two reviewed catalog indexes; never drop tables or alter credentials.

Run once after backup during the agreed maintenance window. --dry-run inspects only.
"""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--dry-run', action='store_true')
    args = p.parse_args()
    from src.Data_base.database import engine
    from src.Data_base.models.product import Product
    from sqlalchemy import inspect
    names = {'ix_products_catalog', 'ix_products_category_catalog'}
    existing = {i['name'] for i in inspect(engine).get_indexes('products')}
    missing = sorted(names - existing)
    if not args.dry_run:
        for index in sorted(Product.__table__.indexes, key=lambda i:i.name):
            if index.name in missing:
                index.create(bind=engine, checkfirst=True)
    print(json.dumps({'dialect':engine.dialect.name,'dry_run':args.dry_run,
                      'missing_before':missing,'created':[] if args.dry_run else missing}, indent=2))


if __name__ == '__main__':
    main()

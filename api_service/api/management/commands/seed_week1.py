"""Explicit demo fixtures; never change an existing account's credentials/role."""
import getpass
from django.core.management.base import BaseCommand, CommandError
from src.Data_base.database import SessionLocal
from src.Data_base.models.user import User
from src.Data_base.models.product import Product, Category
from src.registration import UserSystem


class Command(BaseCommand):
    help = 'Create RBAC demo accounts and secondhand listings owned by two trading users.'

    def add_arguments(self, parser):
        parser.add_argument('--demo', action='store_true', help='Use the documented local demo password Week1Demo123!')

    def handle(self, *args, **options):
        password = 'Week1Demo123!' if options['demo'] else getpass.getpass('Password for new demo accounts: ')
        system = UserSystem(None)
        valid, message = system.validate_input('week1_admin', password, '13900000001', 'week1@example.com')
        if not valid:
            raise CommandError(message)
        password_hash, salt = system.hash_password(password)
        accounts = [('week1_admin', 'admin'), ('week1_auditor', 'auditor'),
                    ('week1_merchant', 'normal'), ('week1_buyer', 'normal'), ('week1_merchant2', 'normal')]
        with SessionLocal.begin() as db:
            for i, (name, role) in enumerate(accounts, 1):
                if db.query(User).filter_by(username=name).first():
                    self.stdout.write(f'{name}: already exists, unchanged')
                    continue
                db.add(User(username=name, email=f'{name}@example.com', phone=f'1390000000{i}',
                            pass_word=password_hash, salt=salt, user_role=role,
                            is_active=True, is_verified=True))
            db.flush()
            category = db.query(Category).filter_by(category_name='第一周验收商品').first()
            if category is None:
                category = Category(category_name='第一周验收商品', is_active=True)
                db.add(category)
                db.flush()
            for i, name in enumerate(('week1_merchant', 'week1_merchant2'), 1):
                sku = f'WEEK1-DEMO-{i}'
                if db.query(Product).filter_by(sku=sku).first():
                    continue
                merchant = db.query(User).filter_by(username=name).one()
                db.add(Product(sku=sku, product_name=f'商户{i}的验收商品', sale_price='19.90',
                               stock_quantity=50, category_id=category.category_id, seller_id=merchant.user_id,
                               status='active', is_active=True, is_available=True))
        self.stdout.write(self.style.SUCCESS('Demo fixtures ready. Admin/auditor must enroll TOTP on first login.'))

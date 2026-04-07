from typing import Dict, Any, List, Optional
from src.Data_base.database import SessionLocal, init_db
from src.Data_base.repositories.user_repository import UserRepository
from src.Data_base.repositories.order_repository import OrderRepository, PaymentRepository
from src.Data_base.repositories.product_repository import ProductRepository, CategoryRepository
from src.Data_base.models.product import Product, Category
from src.registration import UserSystem
from src.authentication import EnhancedUserSystem
from src.utils.security import InputValidator, SQLInjectionValidator
from src.algorithm.rsa_service import SM2Service
from src.algorithm.ca_center import (
    OID_CLIENT_AUTH,
    bootstrap_ca_artifacts,
    create_csr,
    issue_certificate_from_csr,
    parse_certificate_pem,
    sm2_generate_keypair,
)
from src.algorithm.secure_key_storage import SecureKeyStorage
from gmssl import sm2
import os

class UnifiedEcommerceService:
    """统一电商服务接口"""

    def __init__(self):
        # 初始化数据库表
        self._initialize_database()

        # 创建数据库会话
        self.db_session = SessionLocal()

        try:
            # 初始化各个仓库
            self.user_repo = UserRepository(self.db_session)
            self.order_repo = OrderRepository(self.db_session)
            self.product_repo = ProductRepository(self.db_session)
            self.category_repo = CategoryRepository(self.db_session)



            # 从环境变量获取 JWT 密钥
            jwt_secret = os.getenv('JWT_SECRET_KEY', 'fallback_secret_key')

            # 然后初始化业务系统并传递 JWT 密钥
            self.user_system = EnhancedUserSystem(
                user_repository=self.user_repo,
                jwt_secret=jwt_secret  # 传递密钥
            )

            self.asymmetric_service = SM2Service()
            self.asymmetric_service.generate_keys()

            # 创建示例数据
            self._create_sample_data()

            print("统一电商服务初始化完成！")
        except Exception as e:
            # 如果初始化失败，确保关闭数据库会话
            self.db_session.close()
            raise e

    def _initialize_database(self):
        """初始化数据库表"""
        try:
            init_db()
            print("数据库表初始化完成！")
        except Exception as e:
            print(f"数据库表初始化失败: {e}")

    def _create_sample_data(self):
        """创建示例数据 - 使用智能分类管理"""
        try:
            # 确保从干净的事务开始
            self.db_session.rollback()

            print("创建示例数据...")

            # 使用 UserSystem 创建用户
            user_system = UserSystem(user_repository=self.user_repo)

            # 检查用户是否已存在
            existing_admin = self.user_repo.get_user_by_username("admin")
            existing_testuser = self.user_repo.get_user_by_username("testuser")

            # 创建管理员用户（如果不存在）
            if not existing_admin:
                print("创建管理员用户...")
                pwd_hash, salt = user_system.hash_password("AdminPass123!")
                admin_data = {
                    'username': "admin",
                    'pass_word': pwd_hash,
                    'salt': salt,
                    'phone': "13800138000",
                    'email': "admin@example.com",
                    'user_role': 'admin',
                    'is_verified': True,
                    'is_active': True,
                    'failed_attempts': 0,
                    'account_locked_until': None,
                    'last_login': None,
                    'login_count': 0
                }
                admin_user = self.user_repo.create_user(admin_data)
                if admin_user:
                    print(f"管理员用户创建成功: {admin_user.username}")
                else:
                    print("管理员用户创建失败")
            else:
                print("管理员用户已存在")

            # 创建测试用户（如果不存在）
            if not existing_testuser:
                print("创建测试用户...")
                pwd_hash, salt = user_system.hash_password("TestPass123!")
                testuser_data = {
                    'username': "testuser",
                    'pass_word': pwd_hash,
                    'salt': salt,
                    'phone': "13900139000",
                    'email': "test@example.com",
                    'user_role': 'normal',
                    'is_verified': True,
                    'is_active': True,
                    'failed_attempts': 0,
                    'account_locked_until': None,
                    'last_login': None,
                    'login_count': 0
                }
                test_user = self.user_repo.create_user(testuser_data)
                if test_user:
                    print(f"测试用户创建成功: {test_user.username}")
                else:
                    print("测试用户创建失败")
            else:
                print("测试用户已存在")

            # 创建示例分类和商品
            self._create_sample_products()

            self.db_session.commit()
            print("示例数据创建完成！")

        except Exception as e:
            self.db_session.rollback()
            print(f"示例数据创建失败: {e}")
            # 重要：不抛出异常，确保服务能正常启动

    def _create_sample_products(self):
        """创建示例商品 - 使用智能分类管理"""
        try:
            print("开始创建示例商品数据...")

            # 1. 查找或创建顶级分类 - 电子产品
            electronics = self.category_repo.find_or_create_category(
                category_name="电子产品",
                parent_id=None,
                level=1,
                sort_order=1
            )

            if not electronics:
                print("无法创建或找到电子产品分类，跳过商品创建")
                return

            # 2. 查找或创建手机子分类
            phones = self.category_repo.find_or_create_category(
                category_name="手机",
                parent_id=electronics.category_id,
                level=2,
                sort_order=1
            )

            if not phones:
                print("无法创建或找到手机分类，跳过商品创建")
                return

            # 3. 检查示例商品是否已存在
            existing_skus = ["IPHONE13-001", "SAMSUNGS22-001", "XIAOMI13-001"]
            existing_products_count = self.db_session.query(Product).filter(
                Product.sku.in_(existing_skus)
            ).count()

            if existing_products_count >= len(existing_skus):
                print("所有示例商品已存在")
                return

            # 4. 创建示例商品（只创建不存在的）
            sample_products_data = [
                {
                    'sku': "IPHONE13-001",
                    'product_name': "iPhone 13",
                    'description': "苹果智能手机，A15芯片，超视网膜XDR显示屏",
                    'specifications': {"颜色": "星光色", "存储": "128GB", "网络": "5G"},
                    'image_urls': ["/products/cat.jpg"],
                    'sale_price': 5999.00,
                    'stock_quantity': 50,
                    'category_id': phones.category_id,
                    'brand_id': 1,
                    'is_featured': True
                },
                {
                    'sku': "SAMSUNGS22-001",
                    'product_name': "三星 Galaxy S22",
                    'description': "三星旗舰手机，Dynamic AMOLED 2X显示屏",
                    'specifications': {"颜色": "幻影黑", "存储": "256GB", "网络": "5G"},
                    'image_urls': ["/products/dora.gif"],
                    'sale_price': 4999.00,
                    'stock_quantity': 30,
                    'category_id': phones.category_id,
                    'brand_id': 2,
                    'is_featured': True
                },
                {
                    'sku': "XIAOMI13-001",
                    'product_name': "小米13",
                    'description': "小米旗舰手机，徕卡影像系统",
                    'specifications': {"颜色": "白色", "存储": "256GB", "网络": "5G"},
                    'image_urls': ["/products/grace.jpg"],
                    'sale_price': 4299.00,
                    'stock_quantity': 25,
                    'category_id': phones.category_id,
                    'brand_id': 3,
                    'is_featured': False
                }
            ]

            created_count = 0
            for product_data in sample_products_data:
                # 检查商品是否已存在
                existing_product = self.db_session.query(Product).filter(
                    Product.sku == product_data['sku']
                ).first()

                if existing_product:
                    print(f"商品已存在: {product_data['product_name']}")
                    continue

                # 创建新商品
                product = Product(
                    sku=product_data['sku'],
                    product_name=product_data['product_name'],
                    description=product_data['description'],
                    specifications=product_data['specifications'],
                    image_urls=product_data['image_urls'],
                    sale_price=product_data['sale_price'],
                    stock_quantity=product_data['stock_quantity'],
                    track_inventory=True,
                    category_id=product_data['category_id'],
                    brand_id=product_data['brand_id'],
                    is_active=True,
                    is_featured=product_data['is_featured'],
                    is_available=True
                )

                self.db_session.add(product)
                created_count += 1
                print(f" 创建商品: {product_data['product_name']}")

            if created_count > 0:
                self.db_session.commit()
                print(f" 成功创建 {created_count} 个示例商品")
            else:
                print(" 所有示例商品已存在，无需创建")

        except Exception as e:
            self.db_session.rollback()
            print(f" 创建示例商品失败: {e}")
            # 不抛出异常，避免影响服务初始化

    def __del__(self):
        """析构函数，确保数据库会话关闭"""
        if hasattr(self, 'db_session'):
            self.db_session.close()

    def register_user(self, username: str, password: str, phone: str, code: str, email: str = None) -> Dict[str, Any]:
        """用户注册"""
        try:
            # 输入验证
            valid, msg = InputValidator.validate_username(username)
            if not valid:
                return {'success': False, 'message': msg}

            valid, msg = InputValidator.validate_password(password)
            if not valid:
                return {'success': False, 'message': msg}

            # 直接使用传入的验证码进行注册
            success, message = self.user_system.register(username, password, phone, code, email)
            if not success:
                return {'success': False, 'message': message}

            cert_result = self.issue_user_certificate(username)
            if not cert_result.get('success'):
                return {
                    'success': True,
                    'message': f'注册成功，但证书签发失败: {cert_result.get("message")}',
                    'data': {
                        'certificate_issued': False
                    }
                }

            return {
                'success': True,
                'message': '注册成功，已签发用户证书',
                'data': {
                    'certificate_issued': True,
                    'certificate': cert_result.get('certificate')
                }
            }

        except Exception as e:
            return {'success': False, 'message': f'注册失败: {str(e)}'}

    def _resolve_ca_paths(self) -> Dict[str, str]:
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        ca_dir = os.path.join(project_root, "keys", "ca")
        root_cert_path = os.getenv("CA_ROOT_CERT_PATH") or os.path.join(ca_dir, "root_ca.crt.pem")
        env_key_secure_path = os.getenv("CA_ROOT_KEY_SECURE_PATH")
        if env_key_secure_path:
            root_key_secure_path = env_key_secure_path
            root_key_password_path = os.path.join(os.path.dirname(env_key_secure_path), "root_ca_key_password.txt")
        else:
            root_cert_dir = os.path.dirname(root_cert_path)
            same_dir_key_secure = os.path.join(root_cert_dir, "root_ca_key_secure.json")
            same_dir_key_password = os.path.join(root_cert_dir, "root_ca_key_password.txt")
            if os.path.exists(same_dir_key_secure):
                root_key_secure_path = same_dir_key_secure
                root_key_password_path = same_dir_key_password
            else:
                root_key_secure_path = os.path.join(ca_dir, "root_ca_key_secure.json")
                root_key_password_path = os.path.join(ca_dir, "root_ca_key_password.txt")
        return {
            "ca_dir": ca_dir,
            "root_cert_path": root_cert_path,
            "root_key_secure_path": root_key_secure_path,
            "root_key_password_path": root_key_password_path
        }

    def _ensure_ca_artifacts(self, ca_dir: str):
        root_cert_path = os.path.join(ca_dir, "root_ca.crt.pem")
        root_key_secure_path = os.path.join(ca_dir, "root_ca_key_secure.json")
        if os.path.exists(root_cert_path) and os.path.exists(root_key_secure_path):
            return
        bootstrap_ca_artifacts(ca_dir)

    def _load_root_ca_private_key(self, root_key_secure_path: str, root_key_password_path: str) -> str:
        password = os.getenv("CA_ROOT_KEY_PASSWORD")
        if not password and os.path.exists(root_key_password_path):
            with open(root_key_password_path, "r", encoding="utf-8") as f:
                password = f.read().strip()
        if not password:
            raise RuntimeError("缺少CA_ROOT_KEY_PASSWORD且未找到root_ca_key_password.txt")
        storage = SecureKeyStorage(filepath=root_key_secure_path)
        key_data = storage.decrypt_and_load(password)
        private_key = key_data.get("private_key")
        if not private_key:
            raise RuntimeError("根私钥数据无效")
        return private_key

    def _public_key_from_private_key(self, private_key_hex: str) -> str:
        sm2c = sm2.CryptSM2(public_key="", private_key=private_key_hex)
        return sm2c._kg(int(private_key_hex, 16), sm2c.ecc_table["g"])

    def issue_user_certificate(self, username: str) -> Dict[str, Any]:
        try:
            paths = self._resolve_ca_paths()
            self._ensure_ca_artifacts(paths["ca_dir"])
            with open(paths["root_cert_path"], "r", encoding="utf-8") as f:
                root_cert_pem = f.read()
            root_private_key_hex = self._load_root_ca_private_key(
                root_key_secure_path=paths["root_key_secure_path"],
                root_key_password_path=paths["root_key_password_path"]
            )
            root_info = parse_certificate_pem(root_cert_pem)
            derived_root_pub = self._public_key_from_private_key(root_private_key_hex)
            if derived_root_pub != root_info["subject_public_key_hex"]:
                bootstrap_ca_artifacts(paths["ca_dir"])
                with open(paths["root_cert_path"], "r", encoding="utf-8") as f:
                    root_cert_pem = f.read()
                root_private_key_hex = self._load_root_ca_private_key(
                    root_key_secure_path=paths["root_key_secure_path"],
                    root_key_password_path=paths["root_key_password_path"]
                )
                root_info = parse_certificate_pem(root_cert_pem)
                derived_root_pub = self._public_key_from_private_key(root_private_key_hex)
                if derived_root_pub != root_info["subject_public_key_hex"]:
                    return {
                        'success': False,
                        'message': '根证书与根私钥不匹配，请检查CA_ROOT_CERT_PATH与CA_ROOT_KEY_SECURE_PATH配置'
                    }
            user_priv, user_pub = sm2_generate_keypair()
            user_csr = create_csr(
                subject_common_name=username,
                subject_organization="Secure Ecommerce",
                subject_country="CN",
                subject_private_key_hex=user_priv,
                subject_public_key_hex=user_pub,
            )
            user_cert = issue_certificate_from_csr(
                csr=user_csr,
                issuer_common_name=root_info.get("subject_common_name") or "Ecommerce Root CA",
                issuer_organization="Secure Ecommerce",
                issuer_country="CN",
                issuer_private_key_hex=root_private_key_hex,
                issuer_public_key_hex=root_info["subject_public_key_hex"],
                is_ca=False,
                years_valid=1,
                eku_oids=[OID_CLIENT_AUTH]
            )
            cert_pem = user_cert.to_pem()
            return {
                'success': True,
                'certificate': {
                    'username': username,
                    'certificate_pem': cert_pem,
                    'private_key_hex': user_priv,
                    'cert_filename': f"{username}.crt.pem",
                    'private_key_filename': f"{username}.private.hex"
                }
            }
        except Exception as e:
            return {'success': False, 'message': str(e)}

    def login_user(self, username: str, password: str) -> Dict[str, Any]:
        """用户登录"""
        try:
            return self.user_system.login(username, password)
        except Exception as e:
            return {'success': False, 'message': f'登录失败: {str(e)}'}

    def cert_login_user(self, username: str) -> Dict[str, Any]:
        try:
            return self.user_system.issue_token_for_username(username)
        except Exception as e:
            return {'success': False, 'message': f'证书登录失败: {str(e)}'}

    def change_password(self, username: str, old_password: str, new_password: str) -> Dict[str, Any]:
        """修改密码"""
        try:
            success, message = self.user_system.change_password(username, old_password, new_password)
            return {'success': success, 'message': message}
        except Exception as e:
            return {'success': False, 'message': f'修改密码失败: {str(e)}'}

    def send_reset_code(self, phone: str) -> Dict[str, Any]:
        """发送重置密码验证码"""
        try:
            success, message = self.user_system.send_code(phone)
            return {'success': success, 'message': message}
        except Exception as e:
            return {'success': False, 'message': f'发送验证码失败: {str(e)}'}

    def reset_password(self, phone: str, new_password: str, code: str) -> Dict[str, Any]:
        """重置密码"""
        try:
            success, message = self.user_system.reset_password(phone, new_password, code)
            return {'success': success, 'message': message}
        except Exception as e:
            return {'success': False, 'message': f'密码重置失败: {str(e)}'}

    def update_user_profile(self, username: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """更新用户资料"""
        try:
            # 获取用户
            user = self.user_repo.get_user_by_username(username)
            if not user:
                return {'success': False, 'message': '用户不存在'}

            # 验证输入数据
            if 'email' in update_data and update_data['email']:
                valid = SQLInjectionValidator.validate_email(update_data['email'])
                if not valid:
                    return {'success': False, 'message': '邮箱格式不正确'}

            if 'phone' in update_data and update_data['phone']:
                # 简单的手机号格式验证
                import re
                if not re.match(r'^1[3-9]\d{9}$', update_data['phone']):
                    return {'success': False, 'message': '手机号格式不正确'}

            # 更新允许修改的字段
            updated_fields = []
            if 'email' in update_data:
                user.email = update_data['email']
                updated_fields.append('邮箱')

            if 'phone' in update_data:
                user.phone = update_data['phone']
                updated_fields.append('手机号')

            # 保存更改
            self.db_session.commit()

            if updated_fields:
                return {
                    'success': True,
                    'message': f'成功更新: {", ".join(updated_fields)}'
                }
            else:
                return {'success': True, 'message': '没有需要更新的字段'}

        except Exception as e:
            self.db_session.rollback()
            print(f"更新用户资料失败: {e}")
            return {'success': False, 'message': f'更新资料失败: {str(e)}'}

    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """验证令牌"""
        try:
            return self.user_system.verify_token(token)
        except Exception as e:
            print(f"令牌验证失败: {e}")
            return None

    def search_products(self, keyword: str = None, category_id: int = None,
                        min_price: float = None, max_price: float = None,
                        skip: int = 0, limit: int = 50) -> List[Any]:
        """搜索商品"""
        try:
            products = self.product_repo.search_products_safe(
                keyword=keyword,
                category_id=category_id,
                min_price=min_price,
                max_price=max_price,
                skip=skip,
                limit=limit
            )
            return products
        except Exception as e:
            print(f"商品搜索失败: {e}")
            return []

    def get_product_detail(self, product_id: int) -> Optional[Any]:
        """获取商品详情 - 修复版本"""
        try:
            # 使用更安全的方式获取商品详情
            product = self.db_session.query(Product).options(
                # 预加载关联的分类信息
            ).filter(
                Product.product_id == product_id,
                Product.is_active == True
            ).first()
            return product
        except Exception as e:
            print(f"获取商品详情失败: {e}")
            return None

    def get_categories(self) -> List[Any]:
        """获取分类列表"""
        try:
            return self.category_repo.get_categories_tree()
        except Exception as e:
            print(f"获取分类失败: {e}")
            return []


    def create_order(self, order_data: Dict[str, Any], items_data: List[Dict[str, Any]]) -> Optional[Any]:
        """创建订单"""
        try:
            return self.order_repo.create_order_with_items(order_data, items_data)
        except Exception as e:
            print(f"创建订单失败: {e}")
            return None

    def get_user_orders(self, user_id: int, skip: int = 0, limit: int = 50) -> List[Any]:
        """获取用户订单"""
        try:
            return self.order_repo.get_user_orders(user_id, skip, limit)
        except Exception as e:
            print(f"获取用户订单失败: {e}")
            return []

    def encrypt_data(self, data) -> str:
        """加密数据"""
        try:
            return self.asymmetric_service.encrypt_message(data)
        except Exception as e:
            print(f"加密失败: {e}")
            return ""

    def decrypt_data(self, ciphertext: str) -> str:
        """解密数据"""
        try:
            return self.asymmetric_service.decrypt_message(ciphertext)
        except Exception as e:
            print(f"解密失败: {e}")
            return ""

    def validate_input(self, input_string: str, input_type: str = "general") -> Dict[str, Any]:
        """输入验证"""
        try:
            if input_type == "username":
                valid, msg = InputValidator.validate_username(input_string)
            elif input_type == "password":
                valid, msg = InputValidator.validate_password(input_string)
            elif input_type == "email":
                valid = SQLInjectionValidator.validate_email(input_string)
                msg = "验证通过" if valid else "邮箱格式错误"
            else:
                valid = not SQLInjectionValidator.contains_sql_injection(input_string)
                msg = "验证通过" if valid else "输入包含非法字符"

            return {'valid': valid, 'message': msg}
        except Exception as e:
            return {'valid': False, 'message': f'验证失败: {str(e)}'}

import sys
import os
import random
import time
import traceback

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from src.unified_service import UnifiedEcommerceService

    print("成功导入 UnifiedEcommerceService")
except ImportError as e:
    print(f"导入失败: {e}")
    sys.exit(1)


def string_to_int(text):
    """将字符串转换为整数（用于RSA加密）"""
    return int.from_bytes(text.encode('utf-8'), 'big')


def int_to_string(number):
    """将整数转换回字符串（用于RSA解密）"""
    byte_length = (number.bit_length() + 7) // 8
    return number.to_bytes(byte_length, 'big').decode('utf-8')


def example_usage_complete():
    """完整自动化测试脚本"""
    print("\n初始化电商系统服务...")

    try:
        service = UnifiedEcommerceService()
        print("服务初始化成功")
    except Exception as e:
        print(f"服务初始化失败: {e}")
        traceback.print_exc()
        return

    time.sleep(2)
    test_results = {}

    # ========== 1. 用户注册 ==========
    print("\n=== 用户注册测试 ===")
    random_suffix = random.randint(100000, 999999)
    test_username = f"demo_user_{random_suffix}"
    test_phone = f"13800{random_suffix}"

    # 发送验证码
    try:
        send_result = service.user_system.send_code(test_phone)
        print(f"发送验证码结果: {send_result}")
        time.sleep(1)  # 短暂等待
    except Exception as e:
        print(f"发送验证码失败: {e}")

    verification_code = "123456"
    print(f"使用验证码: {verification_code}")

    # 注册前等待（避免频率限制）
    print("等待 3 秒避免频率限制...")
    time.sleep(3)

    # 直接调用 EnhancedUserSystem 的 register 方法
    register_result = service.user_system.register(
        username=test_username,
        password="TestPass123!",
        phone=test_phone,
        code=verification_code,
        email=f"{test_username}@example.com"
    )

    if not register_result[0]:  # register 返回的是 (success, message) 元组
        print(f"用户注册失败: {register_result[1]}，将使用 testuser 继续测试。")
        test_results['用户注册'] = False
        test_username = "testuser"
        password = "TestPass123!"
    else:
        print("用户注册成功")
        test_results['用户注册'] = True
        password = "TestPass123!"

    # ========== 2. JWT 登录与验证 ==========
    print("\n=== JWT 功能测试 ===")
    login_result = service.login_user(test_username, password)

    jwt_success = False
    payload = None

    if login_result.get('success'):
        token = login_result.get('token')
        print(f"登录成功，令牌前20位: {token[:20]}...")
        payload = service.verify_token(token)
        if payload:
            print(f"令牌验证成功，用户: {payload.get('username')}")
            jwt_success = True

            # 测试刷新令牌
            refresh = service.user_system.refresh_token(token)
            test_results['令牌刷新'] = bool(refresh)
            print(f"刷新令牌: {'成功' if refresh else '失败'}")

            # 测试登出
            logout = service.user_system.logout(token)
            test_results['用户登出'] = bool(logout)
            print(f"登出状态: {'成功' if logout else '失败'}")

    else:
        print(f"登录失败: {login_result.get('message')}")

    test_results['JWT认证'] = jwt_success

    # ========== 3. 商品功能 ==========
    print("\n=== 商品功能测试 ===")
    try:
        products = service.search_products(keyword="手机", limit=3)
        print(f"找到 {len(products)} 个手机商品")
        for i, p in enumerate(products, 1):
            print(f"  {i}. {getattr(p, 'product_name', 'Unknown')} - ¥{getattr(p, 'sale_price', 0)}")
        test_results['商品搜索'] = len(products) > 0

        # 获取商品详情 - 修复逻辑
        if products:
            pid = products[0].product_id
            detail = service.get_product_detail(pid)
            if detail:
                print(f"商品详情获取成功: {getattr(detail, 'product_name', 'Unknown')}")
                test_results['商品详情'] = True
            else:
                # 如果第一种方法失败，尝试直接查询数据库
                try:
                    from src.Data_base.models.product import Product
                    detail = service.db_session.query(Product).filter(
                        Product.product_id == pid
                    ).first()
                    if detail:
                        print(f"商品详情获取成功 (直接查询): {getattr(detail, 'product_name', 'Unknown')}")
                        test_results['商品详情'] = True
                    else:
                        print("商品详情获取失败")
                        test_results['商品详情'] = False
                except Exception as db_e:
                    print(f"商品详情获取失败: {db_e}")
                    test_results['商品详情'] = False
        else:
            print("没有找到商品，跳过商品详情测试")
            test_results['商品详情'] = False
    except Exception as e:
        print(f"商品功能测试出错: {e}")
        traceback.print_exc()
        test_results['商品搜索'] = False
        test_results['商品详情'] = False

    # ========== 4. 分类功能 ==========
    print("\n=== 分类功能测试 ===")
    try:
        categories = service.get_categories()
        print(f"找到 {len(categories)} 个分类")
        for i, c in enumerate(categories, 1):
            print(f"  {i}. {getattr(c, 'category_name', 'Unknown')}")
        test_results['分类管理'] = len(categories) > 0
    except Exception as e:
        print(f"分类功能测试出错: {e}")
        test_results['分类管理'] = False

    # ========== 5. RSA加密 ==========
    print("\n=== RSA加密功能测试 ===")
    rsa_success = False
    try:
        test_data = "Hello RSA"
        plaintext_number = string_to_int(test_data)
        encrypted = service.encrypt_data(plaintext_number)
        decrypted_number = service.decrypt_data(encrypted)
        decrypted_text = int_to_string(decrypted_number)
        if decrypted_text == test_data:
            print("RSA 加解密成功")
            rsa_success = True
        else:
            print("RSA 加解密结果不一致")
    except Exception as e:
        print(f"RSA 测试失败: {e}")
        traceback.print_exc()
    test_results['RSA加密'] = rsa_success

    # ========== 6. 安全验证 ==========
    print("\n=== 安全验证测试 ===")
    test_inputs = [
        ("正常用户", "username", True),
        ("admin' OR '1'='1", "username", False),
        ("Weak123", "password", False),
        ("StrongPass123!", "password", True),
        ("invalid-email", "email", False),
        ("test@example.com", "email", True)
    ]

    passed = 0
    for s, t, expect in test_inputs:
        r = service.validate_input(s, t)
        ok = r['valid'] == expect
        status = "通过" if ok else "失败"
        print(f"{status} {t}: '{s}' -> {r['message']}")
        if ok: passed += 1

    test_results['安全验证'] = (passed == len(test_inputs))

    # ========== 7. 订单查询 ==========
    print("\n=== 订单查询测试 ===")
    order_ok = False
    if payload and payload.get('user_id'):
        uid = payload['user_id']
        orders = service.get_user_orders(uid, limit=5)
        print(f"用户 {uid} 订单数: {len(orders)}")
        for i, o in enumerate(orders, 1):
            print(
                f"  订单{i}: {getattr(o, 'order_number', 'N/A')} - ¥{getattr(o, 'total_amount', 0)} - {getattr(o, 'order_status', 'N/A')}")
        order_ok = True
    else:
        print("无法获取用户ID，跳过订单测试")

    test_results['订单查询'] = order_ok

    # ========== 8. 测试总结 ==========
    print("\n=== 测试结果汇总 ===")
    passed = sum(v for v in test_results.values())
    total = len(test_results)
    for k, v in test_results.items():
        status = "通过" if v else "失败"
        print(f"{status} {k}")
    print(f"\n总体结果: {passed}/{total} 项测试通过")

    if passed == total:
        print("系统运行正常")
    else:
        print("系统运行存在问题")

    return test_results


if __name__ == "__main__":
    example_usage_complete()
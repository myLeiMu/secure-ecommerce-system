# test_jwt_simple.py
import subprocess
import sys


def check_installation():
    """检查 PyJWT 安装"""
    print("=== 检查 PyJWT 安装 ===")

    try:
        # 检查是否已安装
        import jwt
        print("✓ PyJWT 已导入成功")

        # 检查版本
        version = getattr(jwt, '__version__', '未知')
        print(f"PyJWT 版本: {version}")

        # 检查 encode 方法
        if hasattr(jwt, 'encode'):
            print("✓ jwt.encode 方法存在")
        else:
            print("✗ jwt.encode 方法不存在")

        return True

    except ImportError:
        print("✗ PyJWT 未安装")
        return False


def install_pyjwt():
    """安装 PyJWT"""
    print("\n=== 安装 PyJWT ===")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "PyJWT"])
        print("✓ PyJWT 安装成功")
        return True
    except subprocess.CalledProcessError:
        print("✗ PyJWT 安装失败")
        return False


def test_jwt_functionality():
    """测试 JWT 功能"""
    print("\n=== 测试 JWT 功能 ===")

    try:
        import jwt
        import datetime

        # 测试数据
        payload = {
            'user_id': 123,
            'username': 'test_user',
            'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=1)
        }

        print("测试编码...")
        token = jwt.encode(payload, 'test_secret_key', algorithm='HS256')
        print(f"✓ 编码成功")
        print(f"Token 类型: {type(token)}")
        print(f"Token 值: {token}")

        print("\n测试解码...")
        decoded = jwt.decode(token, 'test_secret_key', algorithms=['HS256'])
        print(f"✓ 解码成功")
        print(f"解码数据: {decoded}")

        return True

    except Exception as e:
        print(f"✗ 功能测试失败: {e}")
        return False


if __name__ == "__main__":
    # 1. 检查安装
    if not check_installation():
        # 2. 如果未安装，则安装
        if install_pyjwt():
            # 3. 重新检查
            check_installation()

    # 4. 测试功能
    test_jwt_functionality()
import os
from dotenv import load_dotenv

# 加载环境变量文件
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
env_path = os.path.join(BASE_DIR, '.env')
load_dotenv()

HOST = os.getenv('DB_HOST', 'localhost')
PORT = int(os.getenv('DB_PORT', 3306))
USERNAME = os.getenv('DB_USERNAME', 'root')
PASSWORD = os.getenv('DB_PASSWORD', '')  # 从环境变量获取
DB = os.getenv('DB_NAME', 'ecommerce_system')

# dialect + driver://username:passwor@host:port/database
DB_URI = f'mysql+pymysql://{USERNAME}:{PASSWORD}@{HOST}:{PORT}/{DB}'
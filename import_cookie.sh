#!/bin/bash

# GLM Coding Bot - Cookie 导入脚本
# 使用方法: ./import_cookie.sh "你的Cookie字符串"

if [ -z "$1" ]; then
  echo "使用方法: $0 \"你的Cookie字符串\""
  echo ""
  echo "示例:"
  echo "  $0 \"key1=value1; key2=value2; key3=value3\""
  exit 1
fi

COOKIE_STRING="$1"

# 创建临时文件
echo "$COOKIE_STRING" > /tmp/cookie_import.txt

# 复制到 Docker 容器
docker cp /tmp/cookie_import.txt glm-web-1:/tmp/cookie.txt
docker cp /home/reggie/vscode_folder/GLM/scripts/do_import.py glm-web-1:/app/do_import.py

# 在容器中运行 Python 导入脚本
docker compose exec -T web python3 << 'EOF'
import sys
import json
from app.database import SessionLocal
from app.models import Account

def parse_cookie_string(cookie_string):
    cookies = []
    for part in cookie_string.split(';'):
        part = part.strip()
        if '=' in part:
            name, value = part.split('=', 1)
            name = name.strip()
            value = value.strip()
            if name:
                cookies.append({
                    'name': name,
                    'value': value,
                    'domain': 'bigmodel.cn',
                    'path': '/',
                    'httpOnly': False,
                    'secure': True
                })
    return cookies

print("=" * 70)
print("导入 Cookie")
print("=" * 70)

# 从文件读取
with open('/tmp/cookie.txt', 'r', encoding='utf-8') as f:
    cookie_string = f.read().strip()

db = SessionLocal()
try:
    account = db.query(Account).filter(Account.id == 1).first()
    if not account:
        print("\n✗ 账户 1 不存在")
        sys.exit(1)

    cookies = parse_cookie_string(cookie_string)
    print(f"\n✓ 解析到 {len(cookies)} 个 Cookie:")
    for i, cookie in enumerate(cookies[:10]):
        print(f"  - {cookie['name']}")
    if len(cookies) > 10:
        print(f"  ...还有 {len(cookies) - 10} 个")

    if 'bigmodel_token_production' in cookie_string:
        print("\n✓ 找到认证 Token!")

    account.cookie = json.dumps(cookies, ensure_ascii=False)
    db.commit()

    print(f"\n✓ 账户 1 更新成功!")
    print(f"  用户名: {account.username}")
    print(f"  状态: {account.status}")

finally:
    db.close()
EOF

echo ""
echo "✓ Cookie 导入完成!"

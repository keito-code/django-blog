# api_test.py - 認証API総合テスト

import json
import urllib.request
import urllib.error
import time

BASE_URL = "http://localhost:8000/api/v1/auth"

def print_section(title):
    """セクション表示"""
    print(f"\n{'='*60}")
    print(f" {title}")
    print('='*60)

def make_request(endpoint, data=None, token=None, method="POST"):
    """APIリクエストを送信"""
    url = f"{BASE_URL}/{endpoint}/"
    
    headers = {'Content-Type': 'application/json'}
    if token:
        headers['Authorization'] = f'Bearer {token}'
    
    req_data = json.dumps(data).encode('utf-8') if data else None
    
    req = urllib.request.Request(
        url,
        data=req_data,
        headers=headers,
        method=method
    )
    
    try:
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode('utf-8'))
            return True, result
    except urllib.error.HTTPError as e:
        error_body = json.loads(e.read().decode('utf-8'))
        return False, error_body
    except Exception as e:
        return False, str(e)

def test_registration():
    """1. 新規登録テスト"""
    print_section("1. 新規登録テスト")
    
    # テストユーザー情報（タイムスタンプで一意性確保）
    timestamp = str(int(time.time()))
    test_user = {
        "lastName": "田中",
        "firstName": "太郎",
        "email": f"tanaka{timestamp}@example.com",
        "username": f"tanaka_{timestamp}",
        "password": "TestPass123!",
        "passwordConfirmation": "TestPass123!"
    }
    
    print(f"登録データ: {test_user['username']}")
    success, result = make_request("register", test_user)
    
    if success:
        print("✅ 登録成功!")
        print(f"  - ユーザーID: {result['user']['id']}")
        print(f"  - メール: {result['user']['email']}")
        print(f"  - スタッフ権限: {result['user']['isStaff']}")
        return test_user['username'], test_user['password'], result
    else:
        print(f"❌ 登録失敗: {result}")
        return None, None, None

def test_login(username, password):
    """2. ログインテスト"""
    print_section("2. ログインテスト")
    
    login_data = {
        "username": username,
        "password": password
    }
    
    print(f"ログイン試行: {username}")
    success, result = make_request("login", login_data)
    
    if success:
        print("✅ ログイン成功!")
        print(f"  - アクセストークン: {result['access'][:20]}...")
        print(f"  - リフレッシュトークン: {result['refresh'][:20]}...")
        return result['access'], result['refresh']
    else:
        print(f"❌ ログイン失敗: {result}")
        return None, None

def test_user_info(access_token):
    """3. ユーザー情報取得テスト"""
    print_section("3. ユーザー情報取得テスト")
    
    success, result = make_request("user", token=access_token, method="GET")
    
    if success:
        print("✅ ユーザー情報取得成功!")
        print(f"  - ユーザー名: {result['username']}")
        print(f"  - メール: {result['email']}")
        print(f"  - 姓名: {result['lastName']} {result['firstName']}")
        return True
    else:
        print(f"❌ 取得失敗: {result}")
        return False

def test_token_verify(access_token):
    """4. トークン検証テスト"""
    print_section("4. トークン検証テスト")
    
    verify_data = {"token": access_token}
    success, result = make_request("verify", verify_data)
    
    if success:
        print("✅ トークン有効!")
        if 'user' in result:
            print(f"  - ユーザー: {result['user']['username']}")
        return True
    else:
        print(f"❌ トークン無効: {result}")
        return False

def test_logout(access_token, refresh_token):
    """5. ログアウトテスト"""
    print_section("5. ログアウトテスト")
    
    logout_data = {"refresh": refresh_token}
    success, result = make_request("logout", logout_data, token=access_token)
    
    if success:
        print("✅ ログアウト成功!")
        print(f"  - メッセージ: {result.get('detail', 'ログアウトしました')}")
        return True
    else:
        print(f"❌ ログアウト失敗: {result}")
        return False

def test_validation():
    """6. バリデーションテスト"""
    print_section("6. バリデーションテスト")
    
    # パスワード不一致
    print("\n▶ パスワード不一致テスト:")
    invalid_data = {
        "username": "invalid_user",
        "email": "invalid@example.com",
        "password": "TestPass123!",
        "passwordConfirmation": "DifferentPass123!"
    }
    success, result = make_request("register", invalid_data)
    if not success:
        print(f"  ✅ 期待通りエラー: {result.get('password', result)}")
    
    # 弱いパスワード
    print("\n▶ 弱いパスワードテスト:")
    weak_data = {
        "username": "weak_user",
        "email": "weak@example.com",
        "password": "123",
        "passwordConfirmation": "123"
    }
    success, result = make_request("register", weak_data)
    if not success:
        print(f"  ✅ 期待通りエラー: {result.get('password', result)}")

def test_admin_restriction():
    """7. 管理者制限テスト"""
    print_section("7. 管理者制限テスト")
    
    print("▶ 管理者アカウントでのログイン試行:")
    admin_data = {
        "username": "admin",
        "password": "admin_password"
    }
    success, result = make_request("login", admin_data)
    
    if not success:
        if '管理者' in str(result) or 'Admin' in str(result):
            print(f"  ✅ 期待通り拒否: {result.get('detail', result)}")
        else:
            print(f"  ⚠️  別のエラー: {result}")

def run_all_tests():
    """すべてのテストを実行"""
    print("\n" + "="*60)
    print(" Django認証API総合テスト開始")
    print("="*60)
    
    # 1. 新規登録
    username, password, reg_result = test_registration()
    if not username:
        print("\n⚠️  登録失敗のため、後続テストをスキップ")
        return
    
    # 2. ログイン
    access_token, refresh_token = test_login(username, password)
    if not access_token:
        print("\n⚠️  ログイン失敗のため、後続テストをスキップ")
        return
    
    # 3. ユーザー情報取得
    test_user_info(access_token)
    
    # 4. トークン検証
    test_token_verify(access_token)
    
    # 5. ログアウト
    test_logout(access_token, refresh_token)
    
    # 6. バリデーション
    test_validation()
    
    # 7. 管理者制限
    test_admin_restriction()
    
    print("\n" + "="*60)
    print(" テスト完了！")
    print("="*60)

if __name__ == "__main__":
    run_all_tests()

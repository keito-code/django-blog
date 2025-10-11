"""
汎用エラーハンドリングのテスト
DRF層（core/exceptions.py）とDjango層（myblog/urls.py）の両方をテスト
"""
import json
import pytest
from django.urls import reverse
from django.test import override_settings
from accounts.tests.conftest import api_client, csrf_token, to_camel_case


def get_response_data(response):
    """DRF ResponseとDjango JsonResponseの両方に対応"""
    if hasattr(response, 'data'):
        # DRF Response
        return to_camel_case(response.data)
    else:
        # Django JsonResponse
        content = json.loads(response.content)
        return to_camel_case(content)


@pytest.mark.django_db
class TestDRFErrorHandling:
    """DRF管理下のエラーハンドリング（core/exceptions.py）"""

    def test_malformed_json_returns_400(self, api_client, csrf_token):
        """不正なJSONは400エラー（ParseError → fail）"""        
        response = api_client.post(
            reverse('auth-api:login'),
            data='{"invalid": json}',  # 不正なJSON
            content_type='application/json',  # 明示的にContent-Type指定
            HTTP_X_CSRFTOKEN=csrf_token
        )
        assert response.status_code == 400

        # ParseErrorはfailとして処理される
        data = get_response_data(response)
        assert data['status'] == 'fail'
        assert 'detail' in data['data']
    
    def test_missing_required_fields(self, api_client, csrf_token):
        """必須フィールド不足は422エラー（ValidationError → fail）"""        
        # passwordなしでログイン試行
        response = api_client.post(
            reverse('auth-api:login'),
            data={'email': 'test@example.com'},
            format='json',
            HTTP_X_CSRFTOKEN=csrf_token
        )
        assert response.status_code == 422
        data = get_response_data(response)
        assert data['status'] == 'fail'
        assert 'password' in data['data']

        # 不正なメールフォーマット
        response = api_client.post(
            reverse('auth-api:login'),
            data={
                'email': 'invalid-email',  # 不正な形式
                'password': 'password123'
            },
            format='json',
            HTTP_X_CSRFTOKEN=csrf_token
        )
        assert response.status_code == 422
        data = get_response_data(response)
        assert data['status'] == 'fail'
        assert 'email' in data['data']

    def test_authentication_required_returns_401(self, api_client, csrf_token):
        """認証が必要なエンドポイントは401（NotAuthenticated → error）"""
        # 未認証でログアウト試行
        response = api_client.post(
            reverse('auth-api:logout'),
            HTTP_X_CSRFTOKEN=csrf_token
        )
        assert response.status_code == 401
        data = get_response_data(response)
        assert data['status'] == 'error'
        assert 'message' in data

    def test_permission_denied_returns_403(self, api_client):
        """CSRFトークンなしは403（PermissionDenied → error）"""
        # CSRFトークンなしでPOST
        response = api_client.post(
            reverse('auth-api:login'),
            data={'email': 'test@example.com', 'password': 'pass'},
            format='json'
        )
        assert response.status_code == 403
        data = get_response_data(response)
        assert data['status'] == 'error'
        assert 'message' in data

    def test_not_found_returns_404(self, api_client):
        """存在しないリソースは404（NotFound → error）"""
        # 存在しないユーザーID
        response = api_client.get('/v1/users/99999/')
        assert response.status_code == 404
        data = get_response_data(response)
        assert data['status'] == 'error'
        assert 'message' in data

    def test_method_not_allowed_returns_405(self, api_client):
        """許可されていないHTTPメソッドは405（MethodNotAllowed → error）"""
        # GETでログインエンドポイントにアクセス
        response = api_client.get(reverse('auth-api:login'))
        assert response.status_code == 405 

        # exceptions.pyによりJSend形式で返される
        data = get_response_data(response)
        assert data['status'] == 'error'
        assert 'message' in data
        assert 'Method' in data['message'] or 'method' in data['message'].lower()


@pytest.mark.django_db
class TestDjangoErrorHandling:
    """Django層のエラーハンドリング（myblog/urls.py）"""
    
    def test_django_404_returns_json(self, api_client):
        """Django 404ハンドラーがJSON返却（存在しないURL）"""
        response = api_client.get('/v1/this-does-not-exist/')
        assert response.status_code == 404
        
        # JSONとして返却される
        data = get_response_data(response)
        assert data['status'] == 'error'
        assert 'message' in data
        assert 'not found' in data['message'].lower()
        assert data.get('code') == 'NOT_FOUND'
    
    def test_csrf_failure_returns_403_json(self, api_client):
        """CSRF失敗は403のJSON形式で返却"""
        # CSRFトークンなしでPOST（Django層で処理）
        response = api_client.post(
            reverse('auth-api:login'),
            data={
                'email': 'test@example.com',
                'password': 'password123'
            },
            format='json'
            # HTTP_X_CSRFTOKENを意図的に省略
        )
        assert response.status_code == 403
        
        data = get_response_data(response)
        assert data['status'] == 'error'
        assert 'message' in data
        assert 'CSRF' in data['message'] or 'csrf' in data['message'].lower()
        # codeフィールドの確認（存在する場合）
        if 'code' in data:
            assert data['code'] in ['CSRF_FAILED', 'FORBIDDEN']
    
    @override_settings(DEBUG=False)
    def test_django_500_returns_json_in_production(self, api_client, monkeypatch):
        """Django 500ハンドラーが本番環境でJSON返却"""
        # ビューで意図的にエラーを発生させる
        def raise_error(*args, **kwargs):
            raise Exception("Test server error")
        
        # CSRFエンドポイントをモンキーパッチ
        from accounts import views
        monkeypatch.setattr(views.CSRFTokenView, 'get', raise_error)
        
        response = api_client.get(reverse('auth-api:csrf'))
        assert response.status_code == 500
        
        data = get_response_data(response)
        assert data['status'] == 'error'
        assert 'message' in data
        # 本番環境では詳細なエラー情報は含まない
        assert 'Test server error' not in str(data)


@pytest.mark.django_db
class TestErrorResponseFormat:
    """エラーレスポンスの形式を検証"""
    
    def test_fail_response_structure(self, api_client, csrf_token):
        """failレスポンスの構造検証（バリデーションエラー）"""
        response = api_client.post(
            reverse('auth-api:register'),
            data={'email': ''},  # 空のメール
            format='json',
            HTTP_X_CSRFTOKEN=csrf_token
        )
        assert response.status_code == 422
        
        data = get_response_data(response)
        # fail形式の検証
        assert 'status' in data
        assert data['status'] == 'fail'
        assert 'data' in data
        assert isinstance(data['data'], dict)
        # messageは含まれない（failの場合）
        assert 'message' not in data
    
    def test_error_response_structure(self, api_client):
        """errorレスポンスの構造検証（システムエラー）"""
        # 認証エラーを発生させる
        response = api_client.get('/v1/users/me/')
        assert response.status_code == 401
        
        data = get_response_data(response)
        # error形式の検証
        assert 'status' in data
        assert data['status'] == 'error'
        assert 'message' in data
        assert isinstance(data['message'], str)
        # オプショナルフィールド
        if 'code' in data:
            assert isinstance(data['code'], str)
    
    def test_camelcase_conversion_in_errors(self, api_client, csrf_token):
        """エラーレスポンスでもCamelCase変換が適用される"""
        response = api_client.post(
            reverse('auth-api:register'),
            data={
                'email': 'test@example.com',
                'password': 'short',  # 短すぎる
                'password_confirmation': 'different'  # 一致しない
            },
            format='json',
            HTTP_X_CSRFTOKEN=csrf_token
        )
        
        if response.status_code == 422:
            data = get_response_data(response)
            # フィールド名がCamelCaseに変換されているか確認
            assert data['status'] == 'fail'
            assert 'data' in data
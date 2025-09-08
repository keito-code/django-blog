import pytest
from django.contrib.auth import get_user_model
from accounts.serializers import (
    RegisterSerializer,
    PublicUserSerializer,
)

User = get_user_model()


@pytest.mark.django_db  
class TestRegisterSerializer:
    """RegisterSerializerの統合テスト（DB使用）"""

    def test_valid_registration_data(self):
        """正常な登録データの検証"""
        data = {
            'email': 'valid@example.com',
            'username': 'validuser',
            'password': 'ValidPass123!',
            'password_confirmation': 'ValidPass123!',
        }
        
        serializer = RegisterSerializer(data=data)
        assert serializer.is_valid()
        
        validated = serializer.validated_data
        assert validated['email'] == 'valid@example.com'
        assert validated['username'] == 'validuser'
        assert 'password' in validated
    
    def test_password_mismatch(self):
        """パスワード不一致のバリデーション"""
        data = {
            'email': 'test@example.com',
            'username': 'testuser',
            'password': 'Pass123!',
            'password_confirmation': 'Different123!',
        }

        serializer = RegisterSerializer(data=data)
        assert not serializer.is_valid()
        assert 'password' in serializer.errors
        assert 'Password confirmation does not match' in serializer.errors['password'][0]
    
    def test_duplicate_email_validation(self, test_user):
        """メール重複チェック（DB必要）"""
        data = {
            'email': test_user.email,  # 既存のメール
            'username': 'newuser',
            'password': 'Pass123!',
            'password_confirmation': 'Pass123!',
        }
        
        serializer = RegisterSerializer(data=data)
        assert not serializer.is_valid()
        assert 'email' in serializer.errors
        assert 'Registration failed' in str(serializer.errors['email'])
    
    def test_create_user(self):
        """ユーザー作成のテスト"""
        data = {
            'email': 'created@example.com',
            'username': 'createduser',
            'password': 'Pass123!',
            'password_confirmation': 'Pass123!',
        }
        
        serializer = RegisterSerializer(data=data)
        assert serializer.is_valid()
        
        user = serializer.save()
        assert user.email == 'created@example.com'
        assert user.check_password('Pass123!')
        assert User.objects.filter(email='created@example.com').exists()


class TestPublicUserSerializer:
    """PublicUserSerializerのテスト（フィールド確認はDB不要）"""
    
    def test_declared_fields(self):
        """フィールド定義の確認"""
        serializer = PublicUserSerializer()
        fields = set(serializer.fields.keys())
        
        # 必要なフィールド
        assert {'id', 'username', 'email', 'date_joined'}.issubset(fields)
        
        # 除外すべきフィールド
        assert 'password' not in fields
        assert 'is_staff' not in fields
        assert 'is_superuser' not in fields
    
    @pytest.mark.django_db
    def test_serialize_user(self, test_user):
        """ユーザーのシリアライズ"""
        serializer = PublicUserSerializer(test_user)
        data = serializer.data
        
        assert data['id'] == test_user.id
        assert data['email'] == test_user.email
        assert 'is_staff' not in data  # セキュリティ確認
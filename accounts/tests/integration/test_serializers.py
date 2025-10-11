import pytest
from django.contrib.auth import get_user_model
from core.serializers import SuccessResponseSerializer
from accounts.serializers import (
    RegisterSerializer,
    PublicUserSerializer,
    PrivateUserSerializer,
    UpdateUserSerializer,
    AdminUpdateUserSerializer,
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
        assert 'password_confirmation' in serializer.errors
        assert 'Password confirmation does not match' in serializer.errors['password_confirmation'][0]
    
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

    def test_email_normalization(self):
        """メールアドレスの正規化（空白除去・小文字化）"""
        data = {
            'email': '  TEST@EXAMPLE.COM  ',  # 空白と大文字
            'username': 'testuser',
            'password': 'Pass123!',
            'password_confirmation': 'Pass123!'
        }
        serializer = RegisterSerializer(data=data)
        assert serializer.is_valid()
        assert serializer.validated_data['email'] == 'test@example.com'

    def test_username_case_sensitive_duplicate_check(self, test_user):
        """ユーザー名の大文字小文字を区別しない重複チェック"""
        data = {
            'email': 'new@example.com',
            'username': test_user.username.upper(),  # 大文字に変換
            'password': 'Pass123!',
            'password_confirmation': 'Pass123!'
        }
        serializer = RegisterSerializer(data=data)
        assert not serializer.is_valid()
        assert 'username' in serializer.errors
        assert 'Registration failed' in str(serializer.errors['username'])
    
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
        assert fields == {'id', 'date_joined'}
        
        # 除外すべきフィールド
        assert 'email' not in fields
        assert 'password' not in fields
        assert 'is_staff' not in fields
        assert 'is_superuser' not in fields
        assert 'username' not in fields
    
    @pytest.mark.django_db
    def test_serialize_user(self, test_user):
        """ユーザーのシリアライズ"""
        serializer = PublicUserSerializer(test_user)
        data = serializer.data
        
        assert data['id'] == test_user.id
        assert 'date_joined' in data
        assert isinstance(data['date_joined'], str)
        assert 'email' not in data
        assert 'is_staff' not in data  # セキュリティ確認

class TestPrivateUserSerializer:
    """PrivateUserSerializerのテスト（本人用）"""
    
    def test_declared_fields(self):
        """フィールド定義の確認"""
        serializer = PrivateUserSerializer()
        fields = set(serializer.fields.keys())
        
        # 本人用なのでemailも含む
        assert fields == {'id', 'username', 'email', 'date_joined'}
        
        # 除外すべきフィールド
        assert 'password' not in fields
        assert 'is_staff' not in fields
    
    @pytest.mark.django_db
    def test_serialize_user(self, test_user):
        """ユーザーのシリアライズ（本人用）"""
        serializer = PrivateUserSerializer(test_user)
        data = serializer.data
        
        assert data['id'] == test_user.id
        assert data['username'] == test_user.username
        assert data['email'] == test_user.email  # 本人なのでメール含む
        assert 'date_joined' in data
        assert 'password' not in data

@pytest.mark.django_db
class TestUpdateUserSerializer:
    """UpdateUserSerializerのテスト"""
    
    def test_update_without_duplicate(self, test_user):
        """重複なしでの更新"""
        serializer = UpdateUserSerializer(
            test_user,
            data={'email': 'newemail@example.com'},
            partial=True
        )
        assert serializer.is_valid()
        assert serializer.validated_data['email'] == 'newemail@example.com'
    
    def test_update_with_duplicate_email(self, test_user, another_user):
        """他ユーザーと重複するメールアドレスへの更新"""        
        serializer = UpdateUserSerializer(
            test_user,
            data={'email': another_user.email},
            partial=True
        )

        assert not serializer.is_valid()
        assert 'email' in serializer.errors
        assert 'Update failed' in str(serializer.errors['email'])

    def test_email_normalization_on_update(self, test_user):
        """更新時のメールアドレス正規化"""
        
        serializer = UpdateUserSerializer(
            test_user,
            data={'email': '  UPDATED@EXAMPLE.COM  '},
            partial=True
        )
        assert serializer.is_valid()
        assert serializer.validated_data['email'] == 'updated@example.com'

@pytest.mark.django_db
class TestAdminUpdateUserSerializer:
    """管理者用更新シリアライザーのテスト"""
    
    def test_admin_can_update_is_active(self, test_user):
        """is_activeフィールドの更新"""
        serializer = AdminUpdateUserSerializer(
            test_user,
            data={'is_active': False},
            partial=True
        )
        assert serializer.is_valid()
        assert 'is_active' in serializer.validated_data
        assert serializer.validated_data['is_active'] is False

    def test_admin_can_update_is_staff(self, test_user):
        """is_staffフィールドの更新"""
        
        serializer = AdminUpdateUserSerializer(
            test_user,
            data={'is_staff': True},
            partial=True
        )
        assert serializer.is_valid()
        assert 'is_staff' in serializer.validated_data
        assert serializer.validated_data['is_staff'] is True

    def test_admin_fields_available(self):
        """管理者用フィールドが含まれることの確認"""
        
        serializer = AdminUpdateUserSerializer()
        fields = set(serializer.fields.keys())
        
        # 管理者用フィールドが含まれる
        assert 'is_active' in fields
        assert 'is_staff' in fields
        assert 'username' in fields
        assert 'email' in fields

class TestDocumentationSerializers:
    """APIドキュメント用シリアライザーの基本確認"""
    
    def test_success_response_structure(self):
        """成功レスポンスの構造"""
        serializer = SuccessResponseSerializer()
        assert 'status' in serializer.fields
        assert 'data' in serializer.fields
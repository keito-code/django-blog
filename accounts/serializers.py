from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password

User = get_user_model()


class LoginSerializer(serializers.Serializer):
    """ログイン用シリアライザー"""
    email = serializers.EmailField(required=True)
    password = serializers.CharField(required=True, write_only=True)


class RegisterSerializer(serializers.Serializer):
    """ユーザー登録用シリアライザー"""
    email = serializers.EmailField(required=True)
    username = serializers.CharField(required=True, max_length=150)
    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password]
    )
    password_confirmation = serializers.CharField(
        write_only=True,
        required=True
    )
    
    def validate(self, attrs):
        """パスワード一致確認"""
        if attrs['password'] != attrs['password_confirmation']:
            # セキュリティ: 一般的なエラーメッセージ
            raise serializers.ValidationError(
                {"password": "Password confirmation does not match"}
            )
        return attrs
    
    def validate_username(self, value):
        """ユーザー名の重複チェック"""
        if User.objects.filter(username=value).exists():
            # セキュリティ: 詳細を明かさない
            raise serializers.ValidationError("Registration failed")
        return value
    
    def validate_email(self, value):
        """メールアドレスの重複チェック"""
        if User.objects.filter(email=value).exists():
            # セキュリティ: 詳細を明かさない
            raise serializers.ValidationError("Registration failed")
        return value
    
    def create(self, validated_data):
        """ユーザー作成"""
        validated_data.pop('password_confirmation')  # 不要なので削除
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password']
        )
        return user


class PublicUserSerializer(serializers.ModelSerializer):
    """公開用ユーザー情報"""
    class Meta:
        model = User
        fields = ('id', 'username')
        read_only_fields = fields


class PrivateUserSerializer(serializers.ModelSerializer):
    """本人用ユーザー情報"""
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'date_joined')
        read_only_fields = fields

class UpdateUserSerializer(serializers.ModelSerializer):
    """プロフィール更新用"""
    class Meta:
        model = User
        fields = ('username', 'email')  

class AdminUserSerializer(serializers.ModelSerializer):
    """管理者用ユーザー情報"""
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'date_joined', 
                 'is_active')
        read_only_fields = ('id', 'date_joined', 'is_staff', 'is_superuser')
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework.validators import UniqueValidator

User = get_user_model()


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 既存のフィールドのラベルを変更（上書きではなく修正）
        self.fields['username'].label = 'ユーザー名'
        self.fields['password'].label = 'パスワード'
        self.fields['password'].style = {'input_type': 'password'}

    def validate(self, attrs):
        data = super().validate(attrs)
        data['user'] = UserSerializer(self.user).data
        return data

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['username'] = user.username
        token['email'] = user.email
        return token

class PublicUserSerializer(serializers.ModelSerializer):
    """一般公開用のユーザー情報シリアライザー（セキュアバージョン）"""
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name', 'date_joined')
        read_only_fields = ('id', 'date_joined')
        # is_staffは意図的に除外


class PrivateUserSerializer(serializers.ModelSerializer):
    """プライベート用のユーザー情報シリアライザー（自分の情報を見る時）"""
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name', 
                 'date_joined', 'last_login', 'is_active')
        read_only_fields = ('id', 'date_joined', 'last_login', 'is_active')
        # is_staffは含めない


class AdminUserSerializer(serializers.ModelSerializer):
    """管理者用のユーザー情報シリアライザー（管理画面でのみ使用）"""
    is_staff = serializers.BooleanField(read_only=True)
    is_superuser = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name', 
                 'date_joined', 'last_login', 'is_active', 'is_staff', 'is_superuser')
        read_only_fields = ('id', 'date_joined', 'last_login', 'is_staff', 'is_superuser')


# 後方互換性のため（既存のコードが動くように）
UserSerializer = PublicUserSerializer

class RegisterSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(
        required=True,
        label='メールアドレス',
        validators=[UniqueValidator(queryset=User.objects.all(), message="このメールアドレスは既に登録されています。")],
        help_text='ログインに使用します'
    )
    password = serializers.CharField(
        write_only=True,
        required=True,
        label='パスワード',
        validators=[validate_password],
        style={'input_type': 'password'},
        help_text='8文字以上で設定してください'
    )
    password_confirmation = serializers.CharField(
        write_only=True,
        required=True,
        label='パスワード (確認) ',
        style={'input_type': 'password'},
        help_text='同じパスワードを入力してください'
    )

    class Meta:
        model = User
        fields = ('last_name', 'first_name', 'email', 'username', 'password', 'password_confirmation')

        # モデルフィールドのラベルを日本語化
        labels = {
            'last_name': '姓',
            'first_name': '名',
            'username': 'ユーザー名',
        }

        extra_kwargs = {
            'first_name': {'required': False},  # 名は任意
            'last_name': {'required': False},   # 姓は任意
        }

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirmation']:
            raise serializers.ValidationError({"password": "パスワードが一致しません。"})
        return attrs

    def create(self, validated_data):
        validated_data.pop('password_confirmation')
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data.get('email', ''),
            password=validated_data['password'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', '')
        )
        return user
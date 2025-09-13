from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password

User = get_user_model()

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        required=True,
        write_only=True, 
        validators=[validate_password]
    )
    password_confirmation = serializers.CharField(
        write_only=True, 
        required=True
    )

    class Meta:
        model = User
        fields = ['email', 'username', 'password', 'password_confirmation']
        extra_kwargs = {
            'email': {'required': True},
            'username': {'required': True}
        }
    
    def validate_email(self, value):
        # 前後の空白削除 + 小文字化
        normalized = value.strip().lower()

         # 大文字小文字を区別せず重複チェック
        if User.objects.filter(email__iexact=normalized).exists():
            raise serializers.ValidationError("Registration failed")
        return normalized

    def validate_username(self, value):
        if User.objects.filter(username__iexact=value).exists():
            # セキュリティ: 詳細を明かさない
            raise serializers.ValidationError("Registration failed")
        return value

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirmation']:
            # セキュリティ: 一般的なエラーメッセージ
            raise serializers.ValidationError(
                {"password_confirmation": "Password confirmation does not match"}
            )

        # クリーンなデータを準備
        attrs.pop('password_confirmation') # DBに保存不要なフィールドを削除
        return attrs
        
    def create(self, validated_data):
        return User.objects.create_user(**validated_data) # 展開して渡す

class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    password = serializers.CharField(required=True, write_only=True)

class PublicUserSerializer(serializers.ModelSerializer):

    class Meta:
        model = User
        fields = ('id', 'username', 'date_joined')
        read_only_fields = fields


class PrivateUserSerializer(serializers.ModelSerializer):

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'date_joined')
        read_only_fields = fields

class UpdateUserSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(required=False)

    class Meta:
        model = User
        fields = ('username', 'email')  

    def validate_email(self, value):
        normalized = value.strip().lower()
        if User.objects.filter(email__iexact=normalized).exclude(pk=self.instance.pk).exists():
            raise serializers.ValidationError("Update failed. Please check your input and try again.")
        return normalized

    def validate_username(self, value):
        if User.objects.filter(username__iexact=value).exclude(pk=self.instance.pk).exists():
            raise serializers.ValidationError("Update failed. Please check your input and try again.")
        return value

class AdminUserSerializer(serializers.ModelSerializer):

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'date_joined', 'is_active')
        read_only_fields = fields

class AdminUpdateUserSerializer(serializers.ModelSerializer):

    class Meta:
        model = User
        fields = ('username', 'email', 'is_active', 'is_staff')

    def validate_email(self, value):
        normalized = value.strip().lower()
        if User.objects.filter(email__iexact=normalized).exclude(pk=self.instance.pk).exists():
            raise serializers.ValidationError("Update failed. Please check your input and try again.")
        return normalized
    
    def validate_username(self, value):
        if User.objects.filter(username__iexact=value).exclude(pk=self.instance.pk).exists():
            raise serializers.ValidationError("Update failed. Please check your input and try again.")
        return value

# APIドキュメント用
class SuccessResponseSerializer(serializers.Serializer):
    """データなしの成功レスポンス"""
    status = serializers.CharField(read_only=True, default="success")
    data = serializers.Field(read_only=True, allow_null=True)

class FailResponseSerializer(serializers.Serializer):
    """
    ステータスが "fail" のレスポンスボディを表すシリアライザー
    (主にバリデーションエラー用 - 422 Unprocessable Entity)
    """
    status = serializers.CharField(read_only=True, default="fail")
    data = serializers.DictField(
        child=serializers.ListField(child=serializers.CharField()),
        read_only=True,
        help_text='フィールド名をキーとしたエラーメッセージのリスト'
    )

class ErrorResponseSerializer(serializers.Serializer):
    """
    ステータスが "error" のレスポンスボディを表すシリアライザー
    (クライアントエラー・サーバーエラー用 - 4xx, 5xx)
    """
    status = serializers.CharField(read_only=True, default="error")
    message = serializers.CharField(read_only=True)

class AdminUserResponseSerializer(serializers.Serializer):
    """管理者情報の取得、更新レスポンスが共通なのでまとめる"""
    status = serializers.CharField(read_only=True, default="success")
    data = AdminUserSerializer(read_only=True)

class CSRFTokenSerializer(serializers.Serializer):
    csrf_token = serializers.CharField(read_only=True)

class CSRFTokenResponseSerializer(serializers.Serializer):
    status = serializers.CharField(read_only=True, default="success")
    data = CSRFTokenSerializer(read_only=True)

class LoginSuccessDataSerializer(serializers.Serializer):
    user = PublicUserSerializer(read_only=True)

class LoginSuccessResponseSerializer(serializers.Serializer):
    status = serializers.CharField(read_only=True, default="success")
    data = LoginSuccessDataSerializer(read_only=True)

class RegisterSuccessDataSerializer(serializers.Serializer):
    user = PublicUserSerializer(read_only=True)

class RegisterSuccessResponseSerializer(serializers.Serializer):
    status = serializers.CharField(read_only=True, default="success")
    data = RegisterSuccessDataSerializer(read_only=True)

class PrivateUserResponseSerializer(serializers.Serializer):
    status = serializers.CharField(read_only=True, default="success")
    data = PrivateUserSerializer(read_only=True)

class UpdateUserResponseSerializer(serializers.Serializer):
    status = serializers.CharField(read_only=True, default="success")
    data = PrivateUserSerializer(read_only=True)

class VerifyTokenSuccessDataSerializer(serializers.Serializer):
    valid = serializers.BooleanField(read_only=True, default=True)

class VerifyTokenSuccessResponseSerializer(serializers.Serializer):
    status = serializers.CharField(read_only=True, default="success")
    data = VerifyTokenSuccessDataSerializer(read_only=True)




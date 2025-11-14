"""
共通レスポンスSerializer定義
全アプリケーションで使用するJSend形式のレスポンスSerializer
"""
from rest_framework import serializers

class SuccessResponseSerializer(serializers.Serializer):
    """
    JSend成功レスポンス（データなし）
    使用例: ログアウト、削除完了など
    """
    status = serializers.CharField(read_only=True, default="success")
    data = serializers.JSONField(allow_null=True, default=None, read_only=True)

class FailResponseSerializer(serializers.Serializer):
    """
    JSend failレスポンス（バリデーションエラー）
    HTTPステータス: 422 Unprocessable Entity
    使用例: フォーム入力エラー、バリデーション失敗
    """
    status = serializers.CharField(read_only=True, default="fail")
    data = serializers.JSONField(
        read_only=True,
    )

class ErrorResponseSerializer(serializers.Serializer):
    """
    JSend errorレスポンス（システムエラー・権限エラーなど）
    HTTPステータス: 4xx, 5xx
    使用例: 認証エラー、権限不足、サーバーエラー
    """
    status = serializers.CharField(read_only=True, default="error")
    message = serializers.CharField(read_only=True)
    code = serializers.CharField(required=False, read_only=True)
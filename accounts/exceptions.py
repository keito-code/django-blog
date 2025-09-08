from rest_framework.views import exception_handler
from rest_framework.exceptions import ParseError
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from .responses import ResponseFormatter

def custom_exception_handler(exc, context):
    # DRFのデフォルトハンドラーを呼ぶ
    response = exception_handler(exc, context)
    
    if response is not None:
        # SimpleJWTのトークンエラー
        if isinstance(exc, (InvalidToken, TokenError)):
            response.data = ResponseFormatter.unauthorized(
                message="Invalid or expired token"
            )

        # JSONパースエラー
        if isinstance(exc, ParseError):
            response.data = ResponseFormatter.validation_error(
                errors="Invalid JSON format"
            )

    return response
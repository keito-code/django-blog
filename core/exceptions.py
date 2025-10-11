from rest_framework.views import exception_handler
from django.core.exceptions import PermissionDenied
from django.http import Http404
from core.responses import ResponseFormatter 
from rest_framework.exceptions import (
    ValidationError,
    ParseError, 
    MethodNotAllowed,
    Throttled
)

def custom_exception_handler(exc, context):
    """
    DRF例外を JSend形式 に統一するカスタムハンドラ
    """

    # バリデーションエラー -> 422
    if isinstance(exc, ValidationError):
        return ResponseFormatter.validation_error(exc.detail)

    # JSONパースエラー -> 400
    if isinstance(exc, ParseError):
        return ResponseFormatter.fail(
            data={'detail': str(exc.detail)},
            status_code=400
        )

    # メソッド不許可 -> 405
    if isinstance(exc, MethodNotAllowed):
        return ResponseFormatter.method_not_allowed(
            str(exc.detail) if hasattr(exc, 'detail') else 'Method not allowed'
        )

    # レート制限 -> 429
    if isinstance(exc, Throttled):
        return ResponseFormatter.too_many_requests(
            str(exc.detail) if hasattr(exc, 'detail') else 'Too many requests'
        )

    # 上記以外の場合、DRFのデフォルトハンドラを呼び出す
    response = exception_handler(exc, context)

    # DRFが処理できない例外をここで処理
    if response is None:
        if isinstance(exc, PermissionDenied):
            return ResponseFormatter.forbidden(str(exc) or "Permission denied.")
        
        if isinstance(exc, Http404):
            return ResponseFormatter.not_found(str(exc) or "Resource not found.")
        
        # 予期せぬエラーは500として返す
        return ResponseFormatter.server_error() 

    # その他のDRFエラーをカスタム形式に変換
    detail = response.data.get('detail', None)

    if response.status_code == 401:
        return ResponseFormatter.unauthorized(detail or "Authentication required.")
        
    elif response.status_code == 403:
        return ResponseFormatter.forbidden(detail or "Access denied.")
        
    elif response.status_code == 404:
        return ResponseFormatter.not_found(detail or "Resource not found.")
    
    else:
        return ResponseFormatter.error(
            message=detail or "An error occurred.",
            status_code=response.status_code
        )


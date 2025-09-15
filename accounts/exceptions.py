
from rest_framework.views import exception_handler
from django.core.exceptions import PermissionDenied
from django.http import Http404
from accounts.responses import ResponseFormatter 

def custom_exception_handler(exc, context):
    """
    全てのDRF例外を JSend形式 に統一するカスタムハンドラ（改善版）
    """
    # まずDRFのデフォルトハンドラを呼び出す
    response = exception_handler(exc, context)

    # DRFが処理できない例外をここで処理
    if response is None:
        if isinstance(exc, PermissionDenied):
            return ResponseFormatter.forbidden(str(exc) or "Permission denied.")
        
        if isinstance(exc, Http404):
            return ResponseFormatter.not_found(str(exc) or "Resource not found.")
        
        # 予期せぬエラーは500として返す
        return ResponseFormatter.server_error() # デフォルトメッセージを使う

    # DRFが生成したレスポンスをカスタム形式に変換
    # DRFの具体的なエラーメッセージを活かす
    detail = response.data.get('detail', None)

    if response.status_code == 400:
        # バリデーションエラーはresponse.dataに詳細が含まれる
        return ResponseFormatter.validation_error(response.data)
    
    elif response.status_code == 401:
        return ResponseFormatter.unauthorized(detail or "Authentication required.")
        
    elif response.status_code == 403:
        return ResponseFormatter.forbidden(detail or "Access denied.")
        
    elif response.status_code == 404:
        return ResponseFormatter.not_found(detail or "Resource not found.")
    
    else:
        # 405 Method Not Allowed や 429 Throttled など、その他のエラー
        return ResponseFormatter.error(
            message=detail or "An error occurred.",
            status_code=response.status_code
        )


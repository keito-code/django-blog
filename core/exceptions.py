import logging
from rest_framework.views import exception_handler
from django.http import Http404
from core.responses import ResponseFormatter 
from rest_framework.exceptions import (
    ValidationError,
    ParseError, 
    MethodNotAllowed,
    Throttled
)

logger = logging.getLogger(__name__)

def custom_exception_handler(exc, context):
    """
    DRF例外を JSend形式 に統一する。
    fail: データ検証エラーのみ(422)
    error: システムエラー・処理エラー(401,403,404,405,429,500等)
    """

    # "fail" に分類する例外(データ検証エラーのみ)
    if isinstance(exc, (ValidationError, ParseError)):
        
        # ValidationErrorは詳細なエラーdictをそのままdataとして使用
        if isinstance(exc, ValidationError):
            return ResponseFormatter.validation_error(data=exc.detail)

        # ParseErrorもfailとして扱う（JSONパースエラー等）
        if isinstance(exc, ParseError):
            detail_message = str(exc.detail) if hasattr(exc, 'detail') else str(exc)
            return ResponseFormatter.fail(
                data={'detail': detail_message}, 
                status_code=400
            )

    # "error" に分類する例外（システムエラー）
    if isinstance(exc, MethodNotAllowed):
        detail_message = str(exc.detail) if hasattr(exc, 'detail') else "Method not allowed"
        return ResponseFormatter.method_not_allowed(message=detail_message)
    
    if isinstance(exc, Throttled):
        detail_message = str(exc.detail) if hasattr(exc, 'detail') else "Too many requests"
        return ResponseFormatter.too_many_requests(message=detail_message)

    # 上記以外はDRFのデフォルトハンドラを呼び出す
    response = exception_handler(exc, context)

    # DRFが処理できない例外をここで処理
    if response is None:        
        if isinstance(exc, Http404):
            return ResponseFormatter.not_found() # デフォルトメッセージを使用
        
        # 予期せぬエラーは500として返す
        logger.exception(exc)
        return ResponseFormatter.server_error() 

    # その他のDRFエラーをカスタム形式に変換
    detail = response.data.get('detail', None)

    if response.status_code == 401:
        return ResponseFormatter.unauthorized(message=detail)
        
    elif response.status_code == 403:
        return ResponseFormatter.forbidden(message=detail)
        
    elif response.status_code == 404:
        return ResponseFormatter.not_found(message=detail)
    
    else:
        return ResponseFormatter.error(
            message=detail or "An error occurred.",
            status_code=response.status_code
        )


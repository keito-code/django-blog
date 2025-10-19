from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView
from drf_spectacular.views import SpectacularAPIView
from myblog.views import RelaxedSpectacularSwaggerView, RelaxedSpectacularRedocView
from django.http import JsonResponse
from djangorestframework_camel_case.util import camelize


urlpatterns = [
    # Root redirects to API documentation
    path('', RedirectView.as_view(pattern_name='swagger-ui', permanent=False), name='home'),

    # Admin panel (for category management, etc.)
    path(f'{settings.ADMIN_URL}', admin.site.urls),

    # API endpoints
    path('v1/auth/', include(('accounts.urls_auth', 'auth'), namespace='auth-api')),
    path('v1/users/', include(('accounts.urls_users', 'users'), namespace='users-api')),
    path('v1/posts/', include(('blog.urls_posts', 'posts'), namespace='posts-api')),
    path('v1/categories/', include(('blog.urls_categories', 'categories'), namespace='categories-api')),

    # API documentation
    path('v1/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('v1/schema/swagger-ui/', RelaxedSpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('v1/schema/redoc/', RelaxedSpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# ===============================
# 統一エラーハンドラー（Django層）
# JSend形式 + CamelCase変換
# ===============================

def create_error_response(message, code=None, status_code=500):
    """
    統一されたエラーレスポンスを生成
    JSend形式でCamelCase変換を適用
    """
    response_data = {
        'status': 'error',
        'message': message
    }
    if code:
        response_data['code'] = code
    
    # CamelCase変換を適用（Next.jsとの統一性のため）
    camelized_data = camelize(response_data)
    
    return JsonResponse(camelized_data, status=status_code)

def custom_404_handler(request, exception=None):
    """URLルーティングエラー（存在しないエンドポイント）"""
    return create_error_response(
        message=f'Endpoint not found: {request.path}',
        code='NOT_FOUND',
        status_code=404
    )


def custom_500_handler(request):
    """サーバーエラー(DRF外での予期しないエラー)"""
    return create_error_response(
        message='Internal server error occurred',
        code='SERVER_ERROR',
        status_code=500
    )


def custom_403_handler(request, exception=None):
    """権限エラー（Django層でのアクセス拒否）"""
    return create_error_response(
        message='Permission denied',
        code='FORBIDDEN',
        status_code=403
    )


def custom_400_handler(request, exception=None):
    """不正なリクエスト（URLパースエラー等）"""
    return create_error_response(
        message='Bad request',
        code='BAD_REQUEST',
        status_code=400
    )


def csrf_failure_handler(request, reason=""):
    """CSRF検証失敗時のハンドラー"""
    return create_error_response(
        message=f'CSRF verification failed: {reason}',
        code='CSRF_FAILED',
        status_code=403
    )


# Djangoのデフォルトハンドラーを上書き
handler400 = custom_400_handler
handler403 = custom_403_handler
handler404 = custom_404_handler
handler500 = custom_500_handler
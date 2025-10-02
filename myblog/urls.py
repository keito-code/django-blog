from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import SpectacularAPIView
from myblog.views import RelaxedSpectacularSwaggerView, RelaxedSpectacularRedocView, HomeView
from core.responses import ResponseFormatter


urlpatterns = [
    path('', HomeView.as_view(), name='home'),
    path(f'{settings.ADMIN_URL}', admin.site.urls), 

    # Web用（後で削除予定）
    path('accounts/', include(('accounts.urls_web', 'accounts'), namespace='accounts-web')),
    path('blog/', include(('blog.urls', 'blog-web'), namespace='blog-web')),

    path('v1/auth/', include(('accounts.urls_auth', 'auth'), namespace='auth-api')),
    path('v1/users/', include(('accounts.urls_users', 'users'), namespace='users-api')),
    path('v1/posts/', include(('blog.urls_posts', 'posts'), namespace='posts-api')),
    path('v1/categories/', include(('blog.urls_categories', 'categories'), namespace='categories-api')),

    path('v1/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('v1/schema/swagger-ui/', RelaxedSpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('v1/schema/redoc/', RelaxedSpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# ===============================
# カスタムエラーハンドラー
# ===============================

def custom_404_handler(request, exception=None):
    """URLルーティングエラー（存在しないエンドポイント）"""
    return ResponseFormatter.not_found(
        message=f"Endpoint not found: {request.path}"
    )


def custom_500_handler(request):
    """サーバーエラー（DRF外での予期しないエラー）"""
    return ResponseFormatter.server_error(
        message="Internal server error occurred"
    )


def custom_403_handler(request, exception=None):
    """権限エラー（Django層でのアクセス拒否）"""
    return ResponseFormatter.forbidden(
        message="Permission denied"
    )


def custom_400_handler(request, exception=None):
    """不正なリクエスト（URLパースエラー等）"""
    return ResponseFormatter.error(
        message="Bad request",
        code="BAD_REQUEST",
        status_code=400
    )


def csrf_failure_handler(request, reason=""):
    """
    CSRF検証失敗時のハンドラー
    Django層で発生するため、ここで処理
    """
    return ResponseFormatter.forbidden(
        message=f"CSRF verification failed: {reason}"
    )


# Djangoのデフォルトハンドラーを上書き
handler400 = custom_400_handler
handler403 = custom_403_handler
handler404 = custom_404_handler
handler500 = custom_500_handler
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import SpectacularAPIView
from myblog.views import RelaxedSpectacularSwaggerView, RelaxedSpectacularRedocView, HomeView


urlpatterns = [
    path('', HomeView.as_view(), name='home'),
    path(f'{settings.ADMIN_URL}', admin.site.urls), # 動的な管理画面URL
    path('accounts/', include(('accounts.urls_web', 'accounts'), namespace='accounts-web')),
    # ブログのWeb画面は /blog/ 以下に配置
    path('blog/', include(('blog.urls', 'blog-web'), namespace='blog-web')),
    # ブログのAPIは /api/v1/blog/ 以下に配置
    path('api/v1/blog/', include(('blog.api.v1.urls', 'blog-api'), namespace='blog-api')),
    # 認証APIは /api/v1/auth/ 以下に配置
    path('api/v1/auth/', include(('accounts.urls', 'accounts'), namespace='accounts')),
    # APIドキュメント
    path('api/v1/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/v1/schema/swagger-ui/', RelaxedSpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/v1/schema/redoc/', RelaxedSpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
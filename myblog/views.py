from csp.decorators import csp
from drf_spectacular.views import SpectacularSwaggerView, SpectacularRedocView
from django.utils.decorators import method_decorator
from django.shortcuts import render

# ホームページ用の最小限CSP（インラインスタイルのみ許可）
home_csp_decorator = csp({
    'default-src': ["'none'"],
    'style-src': ["'unsafe-inline'"],
})

@home_csp_decorator 
def home_view(request):
    """
    APIドキュメント選択ページ
    Swagger UIとReDocへのリンクを提供
    """
    return render(request, 'home.html')

# APIドキュメント用CSP（Swagger UI/ReDocの動作に必要）
api_docs_csp_decorator = csp({
    'default-src': ["'none'"],
    'script-src': ["'self'", "'unsafe-inline'", "https://cdn.jsdelivr.net"],
    'style-src': ["'self'", "'unsafe-inline'", "https://fonts.googleapis.com", "https://cdn.jsdelivr.net"],
    'font-src': ["'self'", "https://fonts.gstatic.com"],
    'img-src': ["'self'", "data:", "https://cdn.redoc.ly", "https://cdn.jsdelivr.net"],
    'connect-src': ["'self'"],
    'worker-src': ["'self'", "blob:"],
})

@method_decorator(api_docs_csp_decorator, name='dispatch')
class RelaxedSpectacularSwaggerView(SpectacularSwaggerView):
    """
    CSPを緩和したSwagger UIビュー
    """
    pass

@method_decorator(api_docs_csp_decorator, name='dispatch')
class RelaxedSpectacularRedocView(SpectacularRedocView):
    """
    CSPを緩和したReDocビュー
    """
    pass
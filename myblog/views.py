from csp.decorators import csp
from drf_spectacular.views import SpectacularSwaggerView, SpectacularRedocView
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView

# APIドキュメントページにのみ適用する、緩和されたCSPポリシーを定義します。
# 'unsafe-inline'はSwagger UIなどが動作するために必要です。
# サイトの他の部分のCSP設定には影響しません。
custom_csp_decorator = csp({
    'script-src': ["'self'", "'unsafe-inline'", "https://cdn.jsdelivr.net"],  
    'style-src': ["'self'", "'unsafe-inline'", "https://cdn.jsdelivr.net", "https://fonts.googleapis.com"], 
    'font-src': ["'self'", "https://fonts.gstatic.com"],
    'worker-src': ["'self'", "blob:"]
})

# drf-spectacularの標準ビューを継承し、カスタムCSPデコレータを適用したビュー
@method_decorator(custom_csp_decorator, name='dispatch')
class RelaxedSpectacularSwaggerView(SpectacularSwaggerView):
    """
    CSPを緩和したSwagger UIビュー
    """
    pass

@method_decorator(custom_csp_decorator, name='dispatch')
class RelaxedSpectacularRedocView(SpectacularRedocView):
    """
    CSPを緩和したReDocビュー
    """
    pass


class HomeView(TemplateView):
    """
    仮のトップページ - 開発者ポータル
    将来的にフロントエンドアプリケーションに置き換えられる予定
    """
    template_name = 'home.html'
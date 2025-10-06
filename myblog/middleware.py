class CacheControlMiddleware:
    """APIエンドポイント別にキャッシュ制御"""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        response = self.get_response(request)

        # API以外は何もしない
        if not request.path.startswith('/v1/'):
            return response
        
        # ========== APIドキュメント ==========
        if any(keyword in request.path for keyword in ['schema', 'swagger', 'redoc']):
            response['Cache-Control'] = 'public, max-age=86400'  # 24時間
            return response
        
        # ========== 認証・機密情報 ==========
        if request.path.startswith('/v1/auth/'):
            response['Cache-Control'] = 'no-store, private'
            return response

        # ========== OPTIONS（CORSプリフライト） ==========
        if request.method == 'OPTIONS':
            response['Cache-Control'] = 'public, max-age=86400'
            return response
        
        # ========== GET/HEADリクエストのみキャッシュ ==========
        if request.method in ['GET', 'HEAD'] :
            # 下書き一覧（認証状態で変わる）
            if request.GET.get('status') == 'draft':
                response['Cache-Control'] = 'private, max-age=60'
                response['Vary'] = 'Cookie'
                return response
            
            # 記事詳細（認証状態で変わる: 自分の下書きも表示）
            # パス例: /v1/posts/123/
            if '/posts/' in request.path and request.path.rstrip('/').count('/') == 3:
                response['Cache-Control'] = 'public, max-age=3600, stale-while-revalidate=86400'
                response['Vary'] = 'Cookie'  # 認証状態で分離
                return response
            
            # 記事一覧・カテゴリ（認証状態に関わらず同じ）
            if any(keyword in request.path for keyword in ['posts', 'categories']):
                response['Cache-Control'] = 'public, max-age=3600, stale-while-revalidate=86400'
                return response
            
            # その他のGET
            response['Cache-Control'] = 'no-cache'
            return response
        
        # ========== POST/PUT/DELETE/PATCH ==========
        response['Cache-Control'] = 'no-store'
        return response
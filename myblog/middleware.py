class CacheControlMiddleware:
    """
    APIエンドポイント別にキャッシュ制御
    
    設計原則:
    - GET /v1/posts/ は常に公開記事のみ（status パラメータは無視される）
    - GET /v1/posts/{slug}/ は認証状態で挙動変更（公開 or 公開+自分の下書き）
    - GET /v1/users/me/posts/ で下書き含む自分の記事一覧を取得
    - Vary: Origin, Accepts を削除してCloudflareキャッシュを有効化
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        response = self.get_response(request)

        # API以外は何もしない
        if not request.path.startswith('/v1/'):
            return response
        
        # ========== APIドキュメント ==========
        if any(keyword in request.path for keyword in ['schema', 'swagger', 'redoc']):
            response['Cache-Control'] = 'public, max-age=86400'
            self._clean_vary_header(response)
            return response
        
        # ========== 認証・機密情報 ==========
        if request.path.startswith('/v1/auth/'):
            response['Cache-Control'] = 'no-store, private'
            return response

        # ========== ユーザー情報 ==========
        if '/users/' in request.path:
            response['Cache-Control'] = 'no-store, private'
            return response

        # ========== OPTIONS（CORSプリフライト） ==========
        if request.method == 'OPTIONS':
            response['Cache-Control'] = 'public, max-age=86400'
            return response

        # ========== GET/HEAD リクエスト ==========
        if request.method in ['GET', 'HEAD']:
            if '/posts/' in request.path and request.path.rstrip('/').count('/') == 3:
                if hasattr(request, 'user') and request.user.is_authenticated:
                    # 認証済み: 下書き表示の可能性 → private（CDNキャッシュなし）
                    response['Cache-Control'] = 'private, max-age=86400'
                else:
                    # 未認証: 公開記事のみ → public（CDNキャッシュ可）
                    response['Cache-Control'] = 'public, max-age=86400, s-maxage=180, stale-while-revalidate=86400'
                
                # Vary: Cookie のみに設定
                response['Vary'] = 'Cookie'
                return response
            
            # 記事一覧・カテゴリ（公開記事のみ）
            if any(keyword in request.path for keyword in ['posts', 'categories']):
                response['Cache-Control'] = 'public, max-age=86400, s-maxage=180, stale-while-revalidate=86400'
                # Vary ヘッダーを完全にクリーンアップ
                self._clean_vary_header(response)
                return response
            
            # その他のGET
            response['Cache-Control'] = 'no-cache'
            return response
            
        # ========== POST/PUT/DELETE/PATCH ==========
        response['Cache-Control'] = 'no-store'
        return response

    def _clean_vary_header(self, response):
        """
        CDN キャッシュを妨げる Vary ヘッダーを削除
        
        削除対象:
        - Origin: CORS関連、CDNキャッシュを無効化
        - Accept: DRF が追加、通常は不要
        
        保持するもの:
        - Cookie: 認証状態の分離に必要（記事詳細のみ）
        - Accept-Encoding: Cloudflare が自動処理
        """
        if 'Vary' not in response:
            return
        
        vary_values = [v.strip() for v in response['Vary'].split(',')]
        
        # Origin と Accept を除外
        vary_values = [
            v for v in vary_values 
            if v.lower() not in ['origin', 'accept']
        ]
        
        if vary_values:
            response['Vary'] = ', '.join(vary_values)
        else:
            # すべて削除された場合は Vary ヘッダー自体を削除
            del response['Vary']
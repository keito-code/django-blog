"""
認証サービス層（SimpleJWT版）
ビジネスロジックをシンプルに実装
"""
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from django.contrib.auth import authenticate, get_user_model
import logging

logger = logging.getLogger(__name__)
User = get_user_model()


class AuthService:
    """
    認証関連のビジネスロジックを扱うサービス層。

    各メソッドは、処理の結果として常に辞書を返す。
    辞書には必ず 'ok' (True/False) キーが含まれ、処理の成否を示す。
    これはビュー層への内部的な報告であり、最終的なHTTPレスポンスの形式とは独立している。
    """

    def register(self, username, email, password):
        """
        ユーザーを作成し、トークンを生成して辞書として返す
        """
        # ユーザー作成
        user = User.objects.create_user(
            username=username,
            email=email, 
            password=password
        )
        
        # トークン生成
        refresh_obj = RefreshToken.for_user(user)
        
        # ビューが使いやすいように、結果を辞書に整形して返す
        return {
            'ok': True,
            'user': user,
            'tokens': {
                'access': str(refresh_obj.access_token),
                'refresh': str(refresh_obj)
            }
        }
    
    def login(self, email, password, request=None):
        """
        ユーザーを認証し、結果を辞書で返す
        """
        # authenticateはユーザーオブジェクトかNoneを返す
        user = authenticate(request=request, email=email, password=password)
        
        # 認証失敗（ユーザーが存在しない、またはパスワードが違う）
        if user is None:
            logger.warning(f"ログイン失敗: {email}")
            return {'ok': False, 'error': 'Authentication failed'}
            
        if not user.is_active:
            logger.warning(f"非アクティブユーザーのログイン試行: {email}")
            return {'ok': False, 'error': 'User account is inactive'}
        
        refresh_obj = RefreshToken.for_user(user)
        
        logger.info(f"ログイン成功: {email}")
        return {
            'ok': True,
            'user': user,
            'tokens': {
                'access': str(refresh_obj.access_token),
                'refresh': str(refresh_obj)
            }
        }

    def logout(self, refresh_token: str) -> dict:
        """
        ログアウト処理（トークンをブラックリスト登録）
        結果を辞書で返す
        """
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
            logger.info("ログアウト成功: トークンをブラックリストに登録しました。")
            return {'ok': True}
        except TokenError:
            # トークン自体が既に無効な場合。クライアントはログアウト状態になれば良いので、
            # サーバー側では成功として扱っても問題ない。
            logger.debug("ログアウト試行: 既に無効なトークンが提供されました。")
            return {'ok': True}
        except Exception as e:
            # データベースエラーなど、予期せぬ問題が発生した場合。
            # これは問題なので、明確にエラーログを残し、失敗したことを伝える。
            logger.error(f"トークンのブラックリスト登録中に予期せぬエラーが発生: {e}", exc_info=True)
            return {'ok': False, 'error': 'Logout process failed due to a server issue'}
    
    def refresh_tokens(self, refresh_token: str) -> dict:
        """
        トークンをリフレッシュし、結果を辞書で返す
        """
        try:
            old_refresh = RefreshToken(refresh_token)

            # 常にブラックリストに追加
            old_refresh.blacklist()

            # 常に新しいリフレッシュトークンを生成
            # Note: 既存トークンを更新(old_refresh.set_jti(), set_exp())する方法もあるが、
            #       新しいオブジェクトを生成する方が意図が明確で分かりやすい。
            new_refresh = RefreshToken.for_user(old_refresh.user)

            return {
                'ok': True,
                'tokens': {
                    'access': str(new_refresh.access_token),
                    'refresh': str(new_refresh)
                }
            }
                
        except Exception as e:
            logger.warning(f"トークンリフレッシュ失敗: {e}")
            return {'ok': False, 'error': 'Invalid or expired refresh token'}
    
    def verify_token(self, token: str) -> dict:
        """
        アクセストークンを検証し、結果を辞書で返す
        """
        try:
            # AccessTokenオブジェクトに変換を試みる
            # 失敗するとTokenErrorが発生
            AccessToken(token)
            return {'ok': True}
        except TokenError as e:
            # 期限切れ、偽造、ブラックリストなど、無効なトークン
            logger.debug(f"トークン検証失敗: {e}")
            return {'ok': False, 'error': 'Token is invalid or expired'}

class UserService:
    """ユーザー管理関連のビジネスロジック"""
        
    def update_user(self, user: User, validated_data: dict) -> User:
        """
        バリデーション済みのデータでユーザー情報を更新する
        """
        for field, value in validated_data.items():
            setattr(user, field, value)
                
        user.save()
        logger.info(f"ユーザー更新: {user.email}")
        return user
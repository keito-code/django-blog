"""
認証認可のビジネスロジック層

Viewから呼ばれるビジネスロジックを実装する。
JWTトークンの生成・検証、ユーザー管理などを担当。
"""

from typing import Optional, Tuple
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password, check_password
import jwt
import datetime
from django.conf import settings

User = get_user_model()


class AuthService:
    """認証関連のビジネスロジック"""
    
    def login(self, email: str, password: str) -> Optional[Tuple[User, str, str]]:
        """
        ユーザーログイン処理
        
        Args:
            email: メールアドレス
            password: パスワード
            
        Returns:
            成功時: (user, access_token, refresh_token)のタプル
            失敗時: None
        """
        try:
            # ユーザー取得
            user = User.objects.get(email=email)
            
            # パスワード検証
            if not user.check_password(password):
                return None
            
            # トークン生成
            token_service = TokenService()
            access_token = token_service.generate_access_token(user)
            refresh_token = token_service.generate_refresh_token(user)
            
            return (user, access_token, refresh_token)
            
        except User.DoesNotExist:
            return None
    
    def logout(self, refresh_token: str) -> bool:
        """
        ログアウト処理（トークンの無効化）
        
        Args:
            refresh_token: リフレッシュトークン
            
        Returns:
            成功時: True
            失敗時: False
        """
        # 実際の実装では、トークンをブラックリストに追加するなどの処理を行う
        # 現時点ではスタブなので常にTrueを返す
        return True
    
    def refresh_tokens(self, refresh_token: str) -> Optional[Tuple[str, str]]:
        """
        トークンのリフレッシュ処理
        
        Args:
            refresh_token: 現在のリフレッシュトークン
            
        Returns:
            成功時: (new_access_token, new_refresh_token)のタプル
            失敗時: None
        """
        token_service = TokenService()
        
        # リフレッシュトークンの検証
        user_id = token_service.verify_refresh_token(refresh_token)
        if user_id is None:
            return None
        
        try:
            user = User.objects.get(id=user_id)
            
            # 新しいトークンを生成
            new_access_token = token_service.generate_access_token(user)
            new_refresh_token = token_service.generate_refresh_token(user)
            
            return (new_access_token, new_refresh_token)
            
        except User.DoesNotExist:
            return None


class UserService:
    """ユーザー管理のビジネスロジック"""
    
    def create_user(self, email: str, password: str, username: str) -> User:
        """
        新規ユーザー作成
        
        Args:
            email: メールアドレス
            password: パスワード
            username: ユーザー名
            
        Returns:
            作成されたユーザー
            
        Raises:
            ValueError: メールアドレスまたはユーザー名が既に存在する場合
        """
        # 重複チェック
        if User.objects.filter(email=email).exists():
            raise ValueError("Email already exists")
        
        if User.objects.filter(username=username).exists():
            raise ValueError("Username already exists")
        
        # ユーザー作成
        user = User.objects.create_user(
            email=email,
            username=username,
            password=password
        )
        
        return user
    
    def update_user(self, user: User, **kwargs) -> User:
        """
        ユーザー情報更新
        
        Args:
            user: 更新対象のユーザー
            **kwargs: 更新するフィールド
            
        Returns:
            更新されたユーザー
        """
        for field, value in kwargs.items():
            if hasattr(user, field):
                setattr(user, field, value)
        
        user.save()
        return user


class TokenService:
    """JWTトークン管理のビジネスロジック"""
    
    def __init__(self):
        self.secret_key = settings.SECRET_KEY
        self.algorithm = 'HS256'
    
    def generate_access_token(self, user: User) -> str:
        """
        アクセストークン生成
        
        Args:
            user: ユーザーオブジェクト
            
        Returns:
            JWTアクセストークン
        """
        payload = {
            'user_id': user.id,
            'email': user.email,
            'exp': datetime.datetime.utcnow() + datetime.timedelta(
                seconds=settings.AUTH_COOKIE_ACCESS_MAX_AGE
            ),
            'iat': datetime.datetime.utcnow(),
            'type': 'access'
        }
        
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
    
    def generate_refresh_token(self, user: User) -> str:
        """
        リフレッシュトークン生成
        
        Args:
            user: ユーザーオブジェクト
            
        Returns:
            JWTリフレッシュトークン
        """
        payload = {
            'user_id': user.id,
            'exp': datetime.datetime.utcnow() + datetime.timedelta(
                seconds=settings.AUTH_COOKIE_REFRESH_MAX_AGE
            ),
            'iat': datetime.datetime.utcnow(),
            'type': 'refresh'
        }
        
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
    
    def verify_access_token(self, token: str) -> Optional[int]:
        """
        アクセストークンの検証
        
        Args:
            token: JWTトークン
            
        Returns:
            成功時: user_id
            失敗時: None
        """
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            
            if payload.get('type') != 'access':
                return None
                
            return payload.get('user_id')
            
        except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
            return None
    
    def verify_refresh_token(self, token: str) -> Optional[int]:
        """
        リフレッシュトークンの検証
        
        Args:
            token: JWTトークン
            
        Returns:
            成功時: user_id
            失敗時: None
        """
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            
            if payload.get('type') != 'refresh':
                return None
                
            return payload.get('user_id')
            
        except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
            return None
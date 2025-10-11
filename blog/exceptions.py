class BlogException(Exception):
    """ブログアプリの基底例外"""
    pass

class BlogPermissionError(BlogException):
    """権限エラー"""
    pass

class BlogNotFoundError(BlogException):
    """リソースが見つからないエラー"""
    pass

class BlogValidationError(BlogException):
    """バリデーションエラー"""
    pass

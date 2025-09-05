class BlogException(Exception):
    """ブログアプリの基底例外"""
    pass

class BlogPermissionError(BlogException):
    """権限エラー"""
    pass


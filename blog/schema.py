"""
drf-spectacular用のカスタムスキーマクラス
JSend形式のページネーションを正しく認識させる
"""
from drf_spectacular.openapi import AutoSchema


class JSendAutoSchema(AutoSchema):
    """
    DRFのデフォルトページネーション構造 {count, next, previous, results} を
    無効化し、明示的に指定されたレスポンスシリアライザーを使用する
    """
    
    def _is_list_view(self, serializer=None):
        """
        JSendResponseMixin.list() を使っている場合は、
        カスタムページネーションを使用しているため False を返す
        """
        if hasattr(self.view, 'resource_name'):
            return False
        return super()._is_list_view(serializer)
    
    def _get_paginated_response_schema(self, serializer):
        """
        JSend形式の場合は None を返してデフォルトのページネーションを無効化
        """
        if hasattr(self.view, 'resource_name'):
            return None
        return super()._get_paginated_response_schema(serializer)
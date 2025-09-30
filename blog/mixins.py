"""
ViewSetのレスポンスをJSend形式に統一するMixin
ResponseFormatterを活用して一貫性のあるレスポンスを実現
"""
from rest_framework import status
from core.responses import ResponseFormatter


class JSendResponseMixin:
    """
    ViewSetのレスポンスをJSend形式でラップするMixin
    リソース名を適切に設定してレスポンスを整形
    """
    
    # ViewSetでこれらの属性を定義する
    resource_name = 'results'  # デフォルト（複数形）
    resource_name_singular = 'result'  # デフォルト（単数形）
    
    def list(self, request, *args, **kwargs):
        """一覧取得時は複数形でラップ（ページネーション対応）"""
        queryset = self.filter_queryset(self.get_queryset())
        
        # ページネーションあり
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            # ページネーションのget_paginated_responseを使用
            return self.get_paginated_response(serializer.data)
        
        # ページネーションなし
        serializer = self.get_serializer(queryset, many=True)
        return ResponseFormatter.success({
            self.resource_name: serializer.data
        })
    
    def retrieve(self, request, *args, **kwargs):
        """詳細取得時は単数形でラップ"""
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return ResponseFormatter.success({
            self.resource_name_singular: serializer.data
        })
    
    def create(self, request, *args, **kwargs):
        """作成時は単数形でラップ"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        
        # 201 Createdで返す
        return ResponseFormatter.created({
            self.resource_name_singular: serializer.data
        })
    
    def update(self, request, *args, **kwargs):
        """更新時は単数形でラップ"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        
        if getattr(instance, '_prefetched_objects_cache', None):
            instance._prefetched_objects_cache = {}
            
        return ResponseFormatter.success({
            self.resource_name_singular: serializer.data
        })
    
    def partial_update(self, request, *args, **kwargs):
        """部分更新時も単数形でラップ"""
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)
    
    def destroy(self, request, *args, **kwargs):
        """削除時はメッセージを返す"""
        instance = self.get_object()
        self.perform_destroy(instance)
        
        # 204ではなく200でメッセージを返す（JSend形式）
        return ResponseFormatter.success({
            'message': f'{self.resource_name_singular.capitalize()} deleted successfully'
        })
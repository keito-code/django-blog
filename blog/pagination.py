from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class CustomPageNumberPagination(PageNumberPagination):
    """
    カスタムページネーション
    
    Note: page_size_query_paramを'pageSize'にしているのは、
    DRFのcamelCase変換が効かないケースへの対応
    """
    page_size = 10
    page_size_query_param = 'pageSize'  # 意図的にcamelCase
    max_page_size = 100
    
    def get_paginated_response(self, data):
        """
        レスポンス形式をカスタマイズ
        フロントエンド（Next.js）で使いやすい形式に
        """
        return Response({
            'count': self.page.paginator.count,
            'next': self.get_next_link(),
            'previous': self.get_previous_link(),
            'currentPage': self.page.number,  # camelCase
            'totalPages': self.page.paginator.num_pages,  # camelCase
            'pageSize': self.get_page_size(self.request),  # camelCase
            'results': data
        })



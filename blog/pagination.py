from rest_framework.pagination import PageNumberPagination
from core.responses import ResponseFormatter

class CustomPageNumberPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'pageSize'
    max_page_size = 100

    def get_paginated_response(self, data):
        """
        JSend形式でページネーションレスポンスを返す
        ViewSetのresource_nameを使用
        """
        # ViewSetからリソース名を取得（デフォルト: 'results'）
        view = self.request.parser_context.get('view') if hasattr(self.request, 'parser_context') else None
        resource_name = getattr(view, 'resource_name', 'results') if view else 'results'

        # 実際に使用されたページサイズを取得
        # self.page.paginator.per_pageが実際のページサイズ
        actual_page_size = self.page.paginator.per_page
        
        # JSend形式でラップ
        return ResponseFormatter.success({
            resource_name: data,
            'pagination': {
                'count': self.page.paginator.count,
                'page': self.page.number,
                'pageSize': actual_page_size,
                'totalPages': self.page.paginator.num_pages,
                'next': self.get_next_link(),
                'previous': self.get_previous_link()
            }
        })
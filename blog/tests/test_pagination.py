import pytest
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase, APIClient
from blog.models import Post
from blog.pagination import CustomPageNumberPagination

User = get_user_model()


class TestCustomPageNumberPagination(TestCase):
    """ページネーションクラスの単体テスト"""
    
    def test_default_page_size(self):
        """デフォルトのページサイズが10であること"""
        pagination = CustomPageNumberPagination()
        self.assertEqual(pagination.page_size, 10)
    
    def test_page_size_query_param(self):
        """pageSizeパラメータ名がcamelCaseであること"""
        pagination = CustomPageNumberPagination()
        self.assertEqual(pagination.page_size_query_param, 'pageSize')
    
    def test_max_page_size(self):
        """最大ページサイズが100であること"""
        pagination = CustomPageNumberPagination()
        self.assertEqual(pagination.max_page_size, 100)


class TestPostPaginationAPI(APITestCase):
    """PostViewSetのページネーション統合テスト"""
    
    def setUp(self):
        """テストデータの準備"""
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        
        # 15個の記事を作成（ページネーションテスト用）
        for i in range(15):
            Post.objects.create(
                title=f'Test Post {i+1}',
                slug=f'test-post-{i+1}',
                content=f'Content {i+1}',
                author=self.user,
                status='published'
            )
    
    def test_pagination_response_format(self):
        """ページネーションレスポンスの形式を確認"""
        response = self.client.get('/api/v1/blog/posts/')
        self.assertEqual(response.status_code, 200)
        
        # 新しいフィールドが存在することを確認
        data = response.json()
        self.assertIn('currentPage', data)
        self.assertIn('totalPages', data)
        self.assertIn('pageSize', data)
        self.assertIn('results', data)
        self.assertIn('count', data)
        
        # 値の妥当性を確認
        self.assertEqual(data['currentPage'], 1)
        self.assertEqual(data['totalPages'], 2)  # 15件/10件 = 2ページ
        self.assertEqual(data['pageSize'], 10)
        self.assertEqual(data['count'], 15)
        self.assertEqual(len(data['results']), 10)  # 1ページ目は10件
    
    def test_custom_page_size(self):
        """カスタムページサイズが動作すること"""
        response = self.client.get('/api/v1/blog/posts/?pageSize=5')
        data = response.json()
        
        self.assertEqual(data['pageSize'], 5)
        self.assertEqual(data['totalPages'], 3)  # 15件/5件 = 3ページ
        self.assertEqual(len(data['results']), 5)
    
    def test_page_navigation(self):
        """ページ遷移が正しく動作すること"""
        # 2ページ目を取得
        response = self.client.get('/api/v1/blog/posts/?page=2')
        data = response.json()
        
        self.assertEqual(data['currentPage'], 2)
        self.assertEqual(len(data['results']), 5)  # 2ページ目は5件（15-10=5）
    
    def test_max_page_size_limit(self):
        """最大ページサイズ制限が動作すること"""
        response = self.client.get('/api/v1/blog/posts/?pageSize=200')
        data = response.json()
        
        # 100件を超えないこと
        self.assertEqual(data['pageSize'], 100)


# pytest用のマーカー（オプション）
pytestmark = [
    pytest.mark.django_db,  # データベースアクセスを許可
    pytest.mark.api,         # APIテストとしてマーク
]
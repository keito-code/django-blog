"""
blog/tests/integration/test_api_categories.py

CategoryViewSetの統合テスト
- カテゴリーのCRUD操作
- 管理者権限の確認
- カテゴリーごとの投稿一覧
"""

import pytest
from rest_framework import status
from django.contrib.auth import get_user_model
from blog.models import Post, Category
from blog.tests.conftest import to_camel_case

User = get_user_model()


@pytest.mark.django_db
class TestCategoryAPI:
    """CategoryViewSetの統合テスト"""
    
    def test_list_categories_anonymous(self, api_client, category):
        """未認証ユーザーでもカテゴリー一覧は閲覧可能"""
        # 投稿を追加してpost_countをテスト
        Post.objects.create(
            title='Published',
            content='Content',
            author=User.objects.create_user(email='test2@example.com', username='test2'),
            category=category,
            status='published'
        )
        Post.objects.create(
            title='Draft',
            content='Content',
            author=User.objects.create_user(email='test3@example.com', username='test3'),
            category=category,
            status='draft'
        )
        
        response = api_client.get('/v1/categories/')
        data = to_camel_case(response.data)
        
        assert response.status_code == status.HTTP_200_OK
        assert data['status'] == 'success'
        assert 'categories' in data['data']
        
        # ページネーションなし
        categories = data['data']['categories']
        assert len(categories) == 1
        assert categories[0]['name'] == 'Technology'
        assert categories[0]['postCount'] == 1  # 公開記事のみカウント
    
    def test_create_category_as_admin(self, admin_client, category_data):
        """管理者はカテゴリー作成可能"""
        response = admin_client.post('/v1/categories/', category_data)
        data = to_camel_case(response.data)
        
        assert response.status_code == status.HTTP_201_CREATED
        assert data['status'] == 'success'
        assert data['data']['category']['name'] == 'New Category'
        assert data['data']['category']['slug']  # 自動生成
        
        # DBに保存されているか確認
        category = Category.objects.get(name='New Category')
        assert category.slug == 'new-category'
    
    def test_create_category_as_normal_user(self, authenticated_client, category_data):
        """一般ユーザーはカテゴリー作成不可"""
        response = authenticated_client.post('/v1/categories/', category_data)
        data = to_camel_case(response.data)
        
        # 認証済みだが権限不足なので403
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert data['status'] == 'error'
        
        assert not Category.objects.filter(name='New Category').exists()
    
    def test_create_category_anonymous(self, api_client, category_data):
        """未認証ユーザーはカテゴリー作成不可"""
        response = api_client.post('/v1/categories/', category_data)
        data = to_camel_case(response.data)
        
        # 未認証なので401
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert data['status'] == 'error'
    
    def test_retrieve_category(self, api_client, category):
        """カテゴリー詳細は誰でも閲覧可能"""
        response = api_client.get(f'/v1/categories/{category.slug}/')
        data = to_camel_case(response.data)
        
        assert response.status_code == status.HTTP_200_OK
        assert data['status'] == 'success'
        assert data['data']['category']['name'] == 'Technology'
        assert data['data']['category']['id'] == category.id
    
    def test_update_category_as_admin(self, admin_client, category):
        """管理者はカテゴリー更新可能"""
        response = admin_client.patch(
            f'/v1/categories/{category.slug}/',
            {'name': 'Updated Category'}
        )
        data = to_camel_case(response.data)
        
        assert response.status_code == status.HTTP_200_OK
        assert data['status'] == 'success'
        assert data['data']['category']['name'] == 'Updated Category'
        # slugは変更されない
        assert data['data']['category']['slug'] == 'technology'
        
        category.refresh_from_db()
        assert category.name == 'Updated Category'
        assert category.slug == 'technology'
    
    def test_update_category_as_normal_user(self, authenticated_client, category):
        """一般ユーザーはカテゴリー更新不可"""
        response = authenticated_client.patch(
            f'/v1/categories/{category.slug}/',
            {'name': 'Hacked'}
        )
        data = to_camel_case(response.data)
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert data['status'] == 'error'
        
        category.refresh_from_db()
        assert category.name == 'Technology'
    
    def test_delete_category_as_admin(self, admin_client, category):
        """管理者はカテゴリー削除可能"""
        response = admin_client.delete(f'/v1/categories/{category.slug}/')
        data = to_camel_case(response.data)
        
        # 削除成功は200を返す
        assert response.status_code == status.HTTP_200_OK
        assert data['status'] == 'success'
        assert data['data'] is None
        
        assert not Category.objects.filter(slug=category.slug).exists()
    
    def test_delete_category_as_normal_user(self, authenticated_client, category):
        """一般ユーザーはカテゴリー削除不可"""
        response = authenticated_client.delete(f'/v1/categories/{category.slug}/')
        data = to_camel_case(response.data)
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert data['status'] == 'error'
        
        assert Category.objects.filter(slug=category.slug).exists()
    
    def test_category_posts_action(self, api_client, category, user):
        """カテゴリーに属する投稿一覧を取得"""
        # カテゴリーに属する投稿を作成
        Post.objects.create(
            title='Cat Post 1',
            content='Content',
            author=user,
            category=category,
            status='published'
        )
        Post.objects.create(
            title='Cat Post 2',
            content='Content',
            author=user,
            category=category,
            status='published'
        )
        Post.objects.create(
            title='Cat Draft',
            content='Content',
            author=user,
            category=category,
            status='draft'  # 下書きは表示されない
        )
        
        # 別カテゴリーの投稿
        other_category = Category.objects.create(name='Other')
        Post.objects.create(
            title='Other Post',
            content='Content',
            author=user,
            category=other_category,
            status='published'
        )
        
        response = api_client.get(f'/v1/categories/{category.slug}/posts/')
        data = to_camel_case(response.data)
        
        assert response.status_code == status.HTTP_200_OK
        assert data['status'] == 'success'
        assert 'posts' in data['data']
        assert 'pagination' in data['data']  # postsアクションはページネーション有効
        
        posts = data['data']['posts']
        assert len(posts) == 2  # 公開記事のみ
        
        titles = [p['title'] for p in posts]
        assert 'Cat Post 1' in titles
        assert 'Cat Post 2' in titles
        assert 'Cat Draft' not in titles
        assert 'Other Post' not in titles
    
    def test_category_posts_pagination(self, api_client, category, user):
        """カテゴリーの投稿一覧のページネーション"""
        # 複数の投稿を作成
        for i in range(15):
            Post.objects.create(
                title=f'Post {i}',
                content='Content',
                author=user,
                category=category,
                status='published'
            )
        
        response = api_client.get(
            f'/v1/categories/{category.slug}/posts/?pageSize=5'
        )
        data = to_camel_case(response.data)
        
        assert response.status_code == status.HTTP_200_OK
        assert len(data['data']['posts']) == 5
        assert data['data']['pagination']['count'] == 15
        assert data['data']['pagination']['totalPages'] == 3
    
    def test_category_posts_nonexistent(self, api_client):
        """存在しないカテゴリーの投稿一覧"""
        response = api_client.get('/v1/categories/nonexistent/posts/')
        data = to_camel_case(response.data)
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert data['status'] == 'error'
    
    def test_multiple_categories_with_counts(self, api_client, user):
        """複数カテゴリーとpost_countの確認"""
        # カテゴリー作成
        cat1 = Category.objects.create(name='Cat1')
        cat2 = Category.objects.create(name='Cat2')
        cat3 = Category.objects.create(name='Cat3')
        
        # 各カテゴリーに投稿を作成
        for i in range(3):
            Post.objects.create(
                title=f'Cat1 Post {i}',
                content='Content',
                author=user,
                category=cat1,
                status='published'
            )
        
        for i in range(2):
            Post.objects.create(
                title=f'Cat2 Post {i}',
                content='Content',
                author=user,
                category=cat2,
                status='published'
            )
        
        # cat3には下書きのみ
        Post.objects.create(
            title='Cat3 Draft',
            content='Content',
            author=user,
            category=cat3,
            status='draft'
        )
        
        response = api_client.get('/v1/categories/')
        data = to_camel_case(response.data)
        
        categories = data['data']['categories']
        
        # カテゴリー数の確認
        assert len(categories) >= 3
        
        # post_countの確認
        cat_dict = {c['name']: c['postCount'] for c in categories}
        assert cat_dict['Cat1'] == 3
        assert cat_dict['Cat2'] == 2
        assert cat_dict['Cat3'] == 0  # 下書きはカウントされない
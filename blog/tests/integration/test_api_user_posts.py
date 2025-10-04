"""
blog/tests/integration/test_api_user_posts.py

UserPostListViewの統合テスト
- /v1/users/me/posts/ エンドポイントのテスト
- 認証必須の確認
- 自分の投稿のみ取得できることの確認
"""

import pytest
from rest_framework import status
from django.contrib.auth import get_user_model
from blog.models import Post
from blog.tests.conftest import to_camel_case

User = get_user_model()


@pytest.mark.django_db
class TestUserPostsAPI:
    """UserPostListViewの統合テスト"""
    
    def test_user_posts_without_auth(self, api_client):
        """未認証ユーザーはアクセス不可"""
        response = api_client.get('/v1/users/me/posts/')
        data = to_camel_case(response.data)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert data['status'] == 'error'
        assert 'message' in data
    
    def test_user_posts_with_auth(self, authenticated_client, category):
        """認証済みユーザーは自分の投稿一覧を取得可能"""
        # 自分の投稿を作成
        my_published = Post.objects.create(
            title='My Published Post',
            content='Content',
            author=authenticated_client.user,
            category=category,
            status='published'
        )
        my_draft = Post.objects.create(
            title='My Draft Post',
            content='Content',
            author=authenticated_client.user,
            category=category,
            status='draft'
        )
        
        # 他人の投稿を作成
        other_user = User.objects.create_user(
            email='another@example.com',
            username='another'
        )
        other_post = Post.objects.create(
            title='Other User Post',
            content='Content',
            author=other_user,
            category=category,
            status='published'
        )
        
        response = authenticated_client.get('/v1/users/me/posts/')
        data = to_camel_case(response.data)
        
        assert response.status_code == status.HTTP_200_OK
        assert data['status'] == 'success'
        assert 'posts' in data['data']
        assert 'pagination' in data['data']
        
        posts = data['data']['posts']
        titles = [p['title'] for p in posts]
        
        # 自分の投稿（公開・下書き両方）は見える
        assert 'My Published Post' in titles
        assert 'My Draft Post' in titles
        # 他人の投稿は見えない
        assert 'Other User Post' not in titles
    
    def test_user_posts_empty(self, authenticated_client):
        """投稿がない場合は空のリスト"""
        response = authenticated_client.get('/v1/users/me/posts/')
        data = to_camel_case(response.data)
        
        assert response.status_code == status.HTTP_200_OK
        assert data['status'] == 'success'
        assert data['data']['posts'] == []
        assert data['data']['pagination']['count'] == 0
    
    def test_user_posts_ordering(self, authenticated_client, category):
        """デフォルトは作成日時の降順"""
        # 時系列で投稿を作成
        post1 = Post.objects.create(
            title='Old Post',
            content='Content',
            author=authenticated_client.user,
            category=category,
            status='published'
        )
        post2 = Post.objects.create(
            title='New Post',
            content='Content',
            author=authenticated_client.user,
            category=category,
            status='published'
        )
        
        response = authenticated_client.get('/v1/users/me/posts/')
        data = to_camel_case(response.data)
        
        posts = data['data']['posts']
        # 新しい投稿が先に来る
        assert posts[0]['title'] == 'New Post'
        assert posts[1]['title'] == 'Old Post'
    
    def test_user_posts_with_ordering_param(self, authenticated_client, category):
        """orderingパラメータで並び替え可能"""
        # 投稿を作成
        post1 = Post.objects.create(
            title='A Post',
            content='Content',
            author=authenticated_client.user,
            category=category,
            status='published'
        )
        post2 = Post.objects.create(
            title='B Post',
            content='Content',
            author=authenticated_client.user,
            category=category,
            status='published'
        )
        
        # 作成日時の昇順（古い順）
        response = authenticated_client.get('/v1/users/me/posts/?ordering=created_at')
        data = to_camel_case(response.data)
        
        posts = data['data']['posts']
        assert posts[0]['title'] == 'A Post'
        assert posts[1]['title'] == 'B Post'
    
    def test_user_posts_pagination(self, authenticated_client, category):
        """ページネーション動作確認"""
        # 複数の投稿を作成
        for i in range(15):
            Post.objects.create(
                title=f'Post {i:02d}',
                content='Content',
                author=authenticated_client.user,
                category=category,
                status='published'
            )
        
        # ページサイズ5で取得
        response = authenticated_client.get('/v1/users/me/posts/?pageSize=5')
        data = to_camel_case(response.data)
        
        assert response.status_code == status.HTTP_200_OK
        assert len(data['data']['posts']) == 5
        assert data['data']['pagination']['count'] == 15
        assert data['data']['pagination']['totalPages'] == 3
        assert data['data']['pagination']['currentPage'] == 1
        assert data['data']['pagination']['pageSize'] == 5
        assert data['data']['pagination']['next'] is not None
        assert data['data']['pagination']['previous'] is None
        
        # 2ページ目
        response = authenticated_client.get('/v1/users/me/posts/?page=2&pageSize=5')
        data = to_camel_case(response.data)
        
        assert len(data['data']['posts']) == 5
        assert data['data']['pagination']['currentPage'] == 2
        assert data['data']['pagination']['previous'] is not None
        assert data['data']['pagination']['next'] is not None
    
    def test_user_posts_includes_category(self, authenticated_client, category):
        """投稿にカテゴリー情報が含まれる"""
        post = Post.objects.create(
            title='Post with Category',
            content='Content',
            author=authenticated_client.user,
            category=category,
            status='published'
        )
        
        response = authenticated_client.get('/v1/users/me/posts/')
        data = to_camel_case(response.data)
        
        posts = data['data']['posts']
        assert posts[0]['category']['id'] == category.id
        assert posts[0]['category']['name'] == 'Technology'
        assert 'postCount' in posts[0]['category']
    
    def test_user_posts_author_name_format(self, authenticated_client, category):
        """author_nameが適切にフォーマットされている"""
        post = Post.objects.create(
            title='Test Post',
            content='Content',
            author=authenticated_client.user,
            category=category,
            status='published'
        )
        
        response = authenticated_client.get('/v1/users/me/posts/')
        data = to_camel_case(response.data)
        
        posts = data['data']['posts']
        # プライバシー保護のため匿名化されている
        assert posts[0]['authorName'] == f'Author{authenticated_client.user.id}'
    
    def test_user_posts_field_names_camelcase(self, authenticated_client, category):
        """フィールド名がCamelCaseに変換されている"""
        post = Post.objects.create(
            title='Test Post',
            content='Content',
            author=authenticated_client.user,
            category=category,
            status='published'
        )
        
        response = authenticated_client.get('/v1/users/me/posts/')
        data = to_camel_case(response.data)
        
        post_data = data['data']['posts'][0]
        
        # CamelCase確認
        assert 'createdAt' in post_data
        assert 'updatedAt' in post_data
        assert 'authorName' in post_data
        
        # snake_caseが残っていないことを確認
        assert 'created_at' not in post_data
        assert 'updated_at' not in post_data
        assert 'author_name' not in post_data
    
    def test_user_posts_different_users(self, api_client, user, other_user, category):
        """異なるユーザーは異なる投稿一覧を取得"""
        # user1の投稿
        user1_post = Post.objects.create(
            title='User1 Post',
            content='Content',
            author=user,
            category=category,
            status='published'
        )
        
        # user2の投稿
        user2_post = Post.objects.create(
            title='User2 Post',
            content='Content',
            author=other_user,
            category=category,
            status='published'
        )
        
        # user1でアクセス
        api_client.force_authenticate(user=user)
        response = api_client.get('/v1/users/me/posts/')
        data = to_camel_case(response.data)
        
        posts = data['data']['posts']
        assert len(posts) == 1
        assert posts[0]['title'] == 'User1 Post'
        
        # user2でアクセス
        api_client.force_authenticate(user=other_user)
        response = api_client.get('/v1/users/me/posts/')
        data = to_camel_case(response.data)
        
        posts = data['data']['posts']
        assert len(posts) == 1
        assert posts[0]['title'] == 'User2 Post'
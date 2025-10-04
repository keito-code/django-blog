"""
blog/tests/integration/test_api_posts.py

PostViewSetの統合テスト
- APIClientを使用した実際のHTTPリクエスト/レスポンスのテスト
- JSend形式とCamelCase変換の検証
- 認証、権限、フィルタリングの動作確認
"""

import pytest
from rest_framework import status
from django.contrib.auth import get_user_model
from blog.models import Category, Post
from blog.tests.conftest import to_camel_case

User = get_user_model()


@pytest.mark.django_db
class TestPostAPI:
    """PostViewSetの統合テスト"""
    
    def test_list_posts_anonymous(self, api_client, post, draft_post):
        """未認証ユーザーは公開記事のみ閲覧可能"""
        response = api_client.get('/v1/posts/')
        data = to_camel_case(response.data)
        
        assert response.status_code == status.HTTP_200_OK
        assert data['status'] == 'success'
        assert 'posts' in data['data']
        assert 'pagination' in data['data']
        
        # 公開記事のみ表示される
        posts = data['data']['posts']
        assert len(posts) == 1
        assert posts[0]['title'] == 'Test Post'
        assert posts[0]['status'] == 'published'

    def test_list_posts_only_published_for_all_users(self, authenticated_client, post, draft_post, other_user):
        """一覧は認証状態に関わらず公開記事のみ表示"""
        # 他人の公開投稿と下書きを作成
        Post.objects.create(
            title='Other Published',
            content='Content',
            author=other_user,
            status='published'
        )
        Post.objects.create(
            title='Other Draft',
            content='Content',
            author=other_user,
            status='draft'
        )
        
        response = authenticated_client.get('/v1/posts/')
        data = to_camel_case(response.data)
        
        assert response.status_code == status.HTTP_200_OK
        
        posts = data['data']['posts']
        titles = [p['title'] for p in posts]
        
        # 公開記事のみ表示
        assert 'Test Post' in titles
        assert 'Other Published' in titles
        # すべての下書きは見えない（自分も他人も）
        assert 'Draft Post' not in titles
        assert 'Other Draft' not in titles

    def test_can_retrieve_own_draft_directly(self, authenticated_client, draft_post):
        """直接URLアクセスでは自分の下書きを閲覧可能"""
        response = authenticated_client.get(f'/v1/posts/{draft_post.slug}/')
        data = to_camel_case(response.data)
        
        assert response.status_code == status.HTTP_200_OK
        assert data['data']['post']['title'] == 'Draft Post'
        assert data['data']['post']['status'] == 'draft'
    
    
    def test_create_post_without_auth(self, api_client, create_post_data):
        """未認証ユーザーは投稿作成不可"""
        response = api_client.post('/v1/posts/', create_post_data)
        data = to_camel_case(response.data)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert data['status'] == 'error'
        assert 'message' in data
    
    def test_create_post_success(self, authenticated_client, create_post_data, category):
        """認証済みユーザーは投稿作成可能"""
        create_post_data['category_id'] = category.id
        
        response = authenticated_client.post('/v1/posts/', create_post_data)
        data = to_camel_case(response.data)
        
        assert response.status_code == status.HTTP_201_CREATED
        assert data['status'] == 'success'
        assert data['data']['post']['title'] == 'New Post Title'
        assert data['data']['post']['status'] == 'draft'
        if 'category' in data['data']['post']:
            assert data['data']['post']['category']['id'] == category.id
        
        # DBに保存されているか確認
        post = Post.objects.get(title='New Post Title')
        assert post.author == authenticated_client.user
        assert post.slug  # 自動生成されている
    
    def test_retrieve_published_post(self, api_client, post):
        """公開記事は誰でも閲覧可能"""
        response = api_client.get(f'/v1/posts/{post.slug}/')
        data = to_camel_case(response.data)
        
        assert response.status_code == status.HTTP_200_OK
        assert data['status'] == 'success'
        assert data['data']['post']['title'] == 'Test Post'
        assert data['data']['post']['content'] == 'This is test content.'
        assert 'authorName' in data['data']['post']  # CamelCase確認
    
    def test_retrieve_draft_by_author(self, authenticated_client, draft_post):
        """下書きは作者のみ閲覧可能"""
        response = authenticated_client.get(f'/v1/posts/{draft_post.slug}/')
        data = to_camel_case(response.data)
        
        assert response.status_code == status.HTTP_200_OK
        assert data['status'] == 'success'
        assert data['data']['post']['title'] == 'Draft Post'
    
    def test_retrieve_draft_by_other_user(self, api_client, draft_post, other_user):
        """他人の下書きは閲覧不可"""
        api_client.force_authenticate(user=other_user)
        
        response = api_client.get(f'/v1/posts/{draft_post.slug}/')
        data = to_camel_case(response.data)
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert data['status'] == 'error'
    
    def test_update_post_by_author(self, authenticated_client, draft_post, update_post_data):
        """作者は自分の投稿を更新可能"""
        response = authenticated_client.patch(
            f'/v1/posts/{draft_post.slug}/',
            update_post_data
        )
        data = to_camel_case(response.data)
        
        assert response.status_code == status.HTTP_200_OK
        assert data['status'] == 'success'
        assert data['data']['post']['title'] == 'Updated Post Title'
        
        draft_post.refresh_from_db()
        assert draft_post.title == 'Updated Post Title'
    
    def test_update_post_by_other_user(self, api_client, post, other_user, update_post_data):
        """他人の投稿は更新不可"""
        api_client.force_authenticate(user=other_user)
        
        response = api_client.patch(
            f'/v1/posts/{post.slug}/',
            update_post_data
        )
        data = to_camel_case(response.data)
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert data['status'] == 'error'
        
        post.refresh_from_db()
        assert post.title == 'Test Post'  # 変更されていない
    
    def test_publish_post(self, authenticated_client, draft_post):
        """下書きを公開に変更"""
        response = authenticated_client.patch(
            f'/v1/posts/{draft_post.slug}/',
            {'status': 'published'}
        )
        data = to_camel_case(response.data)
        
        assert response.status_code == status.HTTP_200_OK
        assert data['status'] == 'success'
        assert data['data']['post']['status'] == 'published'
        
        draft_post.refresh_from_db()
        assert draft_post.status == 'published'
    
    def test_unpublish_post(self, authenticated_client, post):
        """公開記事を下書きに戻す"""
        response = authenticated_client.patch(
            f'/v1/posts/{post.slug}/',
            {'status': 'draft'}
        )
        data = to_camel_case(response.data)
        
        assert response.status_code == status.HTTP_200_OK
        assert data['status'] == 'success'
        assert data['data']['post']['status'] == 'draft'
        
        post.refresh_from_db()
        assert post.status == 'draft'
    
    def test_invalid_status_change(self, authenticated_client, post):
        """不正なステータス値はエラー"""
        response = authenticated_client.patch(
            f'/v1/posts/{post.slug}/',
            {'status': 'invalid'}
        )
        data = to_camel_case(response.data)
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert data['status'] == 'fail'
        assert 'status' in data['data']
    
    def test_same_status_ignored(self, authenticated_client, post):
        """同じステータスへの変更は無視される"""
        response = authenticated_client.patch(
            f'/v1/posts/{post.slug}/',
            {'status': 'published', 'title': 'New Title'}
        )
        data = to_camel_case(response.data)
        
        assert response.status_code == status.HTTP_200_OK
        assert data['status'] == 'success'
        assert data['data']['post']['title'] == 'New Title'
        assert data['data']['post']['status'] == 'published'
    
    def test_delete_post_by_author(self, authenticated_client, draft_post):
        """作者は自分の投稿を削除可能"""
        response = authenticated_client.delete(f'/v1/posts/{draft_post.slug}/')
        data = to_camel_case(response.data)
        
        # 削除成功は200を返す（204ではない）
        assert response.status_code == status.HTTP_200_OK
        assert data['status'] == 'success'
        assert data['data'] is None
        
        assert not Post.objects.filter(slug=draft_post.slug).exists()
    
    def test_delete_post_by_other_user(self, api_client, post, other_user):
        """他人の投稿は削除不可"""
        api_client.force_authenticate(user=other_user)
        
        response = api_client.delete(f'/v1/posts/{post.slug}/')
        data = to_camel_case(response.data)
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert data['status'] == 'error'
        
        assert Post.objects.filter(slug=post.slug).exists()
    
    def test_filter_by_category(self, authenticated_client, post, category):
        """カテゴリーでフィルタリング"""
        # 別カテゴリーの投稿を作成
        other_category = Category.objects.create(name='Other')
        Post.objects.create(
            title='Other Post',
            content='Content',
            author=authenticated_client.user,
            category=other_category,
            status='published'
        )
        
        response = authenticated_client.get(
            f'/v1/posts/?category={category.id}'
        )
        data = to_camel_case(response.data)
        
        assert response.status_code == status.HTTP_200_OK
        posts = data['data']['posts']
        assert len(posts) == 1
        assert posts[0]['category']['id'] == category.id
    
    def test_search_posts(self, api_client, post):
        """タイトルと内容で検索"""
        # 検索用の投稿を追加
        Post.objects.create(
            title='Python Tutorial',
            content='Learn Django',
            author=post.author,
            status='published'
        )
        
        response = api_client.get('/v1/posts/?search=Python')
        data = to_camel_case(response.data)
        
        assert response.status_code == status.HTTP_200_OK
        posts = data['data']['posts']
        assert len(posts) == 1
        assert 'Python' in posts[0]['title']
    
    def test_ordering(self, api_client, user):
        """作成日時で並び替え"""
        # 複数の投稿を作成
        post1 = Post.objects.create(
            title='First Post',
            content='Content',
            author=user,
            status='published'
        )
        post2 = Post.objects.create(
            title='Second Post',
            content='Content',
            author=user,
            status='published'
        )
        
        # デフォルトは新しい順
        response = api_client.get('/v1/posts/')
        data = to_camel_case(response.data)
        
        posts = data['data']['posts']
        assert posts[0]['title'] == 'Second Post'
        assert posts[1]['title'] == 'First Post'
        
        # 古い順に変更
        response = api_client.get('/v1/posts/?ordering=created_at')
        data = to_camel_case(response.data)
        
        posts = data['data']['posts']
        assert posts[0]['title'] == 'First Post'
        assert posts[1]['title'] == 'Second Post'
    
    def test_pagination(self, api_client, user):
        """ページネーション動作確認"""
        # 複数の投稿を作成
        for i in range(15):
            Post.objects.create(
                title=f'Post {i}',
                content='Content',
                author=user,
                status='published'
            )
        
        response = api_client.get('/v1/posts/?pageSize=5')
        data = to_camel_case(response.data)
        
        assert response.status_code == status.HTTP_200_OK
        assert len(data['data']['posts']) == 5
        assert data['data']['pagination']['count'] == 15
        assert data['data']['pagination']['totalPages'] == 3
        assert data['data']['pagination']['page'] == 1
        assert data['data']['pagination']['next'] is not None
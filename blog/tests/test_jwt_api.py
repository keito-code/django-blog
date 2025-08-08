import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from blog.models import Post

User = get_user_model()


@pytest.fixture
def api_client():
    """APIクライアントのフィクスチャ"""
    return APIClient()


@pytest.fixture
def user(db):
    """テスト用ユーザーのフィクスチャ"""
    return User.objects.create_user(
        username='testuser',
        email='test@example.com',
        password='testpass123'
    )


@pytest.fixture
def another_user(db):
    """別のテスト用ユーザーのフィクスチャ"""
    return User.objects.create_user(
        username='anotheruser',
        email='another@example.com',
        password='anotherpass123'
    )


@pytest.fixture
def authenticated_client(api_client, user):
    """認証済みAPIクライアントのフィクスチャ"""
    refresh = RefreshToken.for_user(user)
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    api_client.user = user
    return api_client


@pytest.fixture
def post(user):
    """テスト用ブログ記事のフィクスチャ"""
    return Post.objects.create(
        title='Test Post',
        content='Test content',
        author=user,
        status='published'
    )


@pytest.fixture
def draft_post(user):
    """下書きブログ記事のフィクスチャ"""
    return Post.objects.create(
        title='Draft Post',
        content='Draft content',
        author=user,
        status='draft'
    )


@pytest.mark.django_db
class TestJWTAuthentication:
    """JWT認証のテスト"""
    
    def test_obtain_token_success(self, api_client, user):
        """正しい認証情報でトークンを取得できる"""
        url = reverse('blog-api:token_obtain_pair')
        data = {
            'username': 'testuser',
            'password': 'testpass123'
        }
        response = api_client.post(url, data)
        
        assert response.status_code == status.HTTP_200_OK
        assert 'access' in response.data
        assert 'refresh' in response.data
    
    def test_obtain_token_invalid_credentials(self, api_client):
        """無効な認証情報ではトークンを取得できない"""
        url = reverse('blog-api:token_obtain_pair')
        data = {
            'username': 'wronguser',
            'password': 'wrongpass'
        }
        response = api_client.post(url, data)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_refresh_token(self, api_client, user):
        """リフレッシュトークンで新しいアクセストークンを取得できる"""
        refresh = RefreshToken.for_user(user)
        url = reverse('blog-api:token_refresh')
        data = {'refresh': str(refresh)}
        
        response = api_client.post(url, data)
        
        assert response.status_code == status.HTTP_200_OK
        assert 'access' in response.data
    
    def test_invalid_refresh_token(self, api_client):
        """無効なリフレッシュトークンではエラーになる"""
        url = reverse('blog-api:token_refresh')
        data = {'refresh': 'invalid-token'}
        
        response = api_client.post(url, data)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestPostAPI:
    """ブログ記事APIのテスト"""
    
    def test_list_posts_unauthenticated(self, api_client, post):
        """未認証でも公開記事一覧を取得できる"""
        url = reverse('blog-api:post-list')
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 1
        assert response.data['results'][0]['title'] == 'Test Post'
    
    def test_list_posts_authenticated(self, authenticated_client, post, draft_post):
        """認証済みユーザーは自分の下書きも取得できる"""
        url = reverse('blog-api:post-list')
        response = authenticated_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 2
    
    def test_retrieve_post_unauthenticated(self, api_client, post):
        """未認証でも公開記事の詳細を取得できる"""
        url = reverse('blog-api:post-detail', kwargs={'pk': post.pk})
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['title'] == 'Test Post'
    
    def test_retrieve_draft_post_unauthenticated(self, api_client, draft_post):
        """未認証では下書き記事にアクセスできない"""
        url = reverse('blog-api:post-detail', kwargs={'pk': draft_post.pk})
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    def test_create_post_authenticated(self, authenticated_client):
        """認証済みユーザーは記事を作成できる"""
        url = reverse('blog-api:post-list')
        data = {
            'title': 'New Post',
            'content': 'New content',
            'status': 'published'
        }
        response = authenticated_client.post(url, data)
        
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['title'] == 'New Post'
        assert response.data['author'] == authenticated_client.user.username
    
    def test_create_post_unauthenticated(self, api_client):
        """未認証では記事を作成できない"""
        url = reverse('blog-api:post-list')
        data = {
            'title': 'New Post',
            'content': 'New content',
            'status': 'published'
        }
        response = api_client.post(url, data)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_update_own_post(self, authenticated_client, post):
        """著者は自分の記事を更新できる"""
        url = reverse('blog-api:post-detail', kwargs={'pk': post.pk})
        data = {
            'title': 'Updated Post',
            'content': 'Updated content',
            'status': 'published'
        }
        response = authenticated_client.put(url, data)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['title'] == 'Updated Post'
    
    def test_update_others_post(self, api_client, another_user, post):
        """他のユーザーの記事は更新できない"""
        refresh = RefreshToken.for_user(another_user)
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
        
        url = reverse('blog-api:post-detail', kwargs={'pk': post.pk})
        data = {
            'title': 'Updated Post',
            'content': 'Updated content',
            'status': 'published'
        }
        response = api_client.put(url, data)
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    def test_partial_update_own_post(self, authenticated_client, post):
        """著者は自分の記事を部分更新できる"""
        url = reverse('blog-api:post-detail', kwargs={'pk': post.pk})
        data = {'title': 'Partially Updated Post'}
        response = authenticated_client.patch(url, data)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['title'] == 'Partially Updated Post'
        assert response.data['content'] == 'Test content'  # 変更されていない
    
    def test_delete_own_post(self, authenticated_client, post):
        """著者は自分の記事を削除できる"""
        url = reverse('blog-api:post-detail', kwargs={'pk': post.pk})
        response = authenticated_client.delete(url)
        
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert Post.objects.filter(pk=post.pk).count() == 0
    
    def test_delete_others_post(self, api_client, another_user, post):
        """他のユーザーの記事は削除できない"""
        refresh = RefreshToken.for_user(another_user)
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
        
        url = reverse('blog-api:post-detail', kwargs={'pk': post.pk})
        response = api_client.delete(url)
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert Post.objects.filter(pk=post.pk).exists()


@pytest.mark.django_db
class TestPostFiltering:
    """記事フィルタリングのテスト"""
    
    @pytest.fixture
    def multiple_posts(self, user, another_user):
        """複数の記事を作成するフィクスチャ"""
        posts = []
        posts.append(Post.objects.create(
            title='User1 Post 1',
            content='Content 1',
            author=user,
            status='published'
        ))
        posts.append(Post.objects.create(
            title='User1 Post 2',
            content='Content 2',
            author=user,
            status='draft'
        ))
        posts.append(Post.objects.create(
            title='User2 Post 1',
            content='Content 3',
            author=another_user,
            status='published'
        ))
        return posts
    
    def test_filter_by_status(self, authenticated_client, multiple_posts):
        """ステータスでフィルタリングできる"""
        url = reverse('blog-api:post-list')
        response = authenticated_client.get(url, {'status': 'published'})
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 2
        for post in response.data['results']:
            assert post['status'] == 'published'
    
    def test_filter_by_author(self, authenticated_client, multiple_posts, user):
        """著者でフィルタリングできる"""
        url = reverse('blog-api:post-list')
        response = authenticated_client.get(url, {'author': user.id})
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 2
        for post in response.data['results']:
            assert post['author'] == user.username
    
    def test_search_posts(self, authenticated_client, multiple_posts):
        """タイトルと内容で検索できる"""
        url = reverse('blog-api:post-list')
        response = authenticated_client.get(url, {'search': 'User1'})
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 2
        for post in response.data['results']:
            assert 'User1' in post['title']
    
    def test_ordering(self, authenticated_client, multiple_posts):
        """作成日時でソートできる"""
        url = reverse('blog-api:post-list')
        response = authenticated_client.get(url, {'ordering': '-created'})
        
        assert response.status_code == status.HTTP_200_OK
        results = response.data['results']
        for i in range(len(results) - 1):
            assert results[i]['created'] >= results[i + 1]['created']


@pytest.mark.django_db
class TestPagination:
    """ページネーションのテスト"""
    
    @pytest.fixture
    def many_posts(self, user):
        """多数の記事を作成するフィクスチャ"""
        posts = []
        for i in range(15):
            posts.append(Post.objects.create(
                title=f'Post {i}',
                content=f'Content {i}',
                author=user,
                status='published'
            ))
        return posts
    
    def test_pagination(self, api_client, many_posts):
        """ページネーションが機能する"""
        url = reverse('blog-api:post-list')
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert 'count' in response.data
        assert 'next' in response.data
        assert 'previous' in response.data
        assert 'results' in response.data
        assert len(response.data['results']) == 10  # デフォルトのページサイズ
    
    def test_page_size(self, api_client, many_posts):
        """ページサイズを指定できる"""
        url = reverse('blog-api:post-list')
        response = api_client.get(url, {'page_size': 5})
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 5
import pytest
from django.urls import reverse
from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient
from blog.models import Post


@pytest.mark.django_db
class TestPostListAPI:
    """記事一覧APIのテスト"""

    def setup_method(self):
        self.client = APIClient()
        self.url = reverse('blog-api:post-list')
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )

    def test_get_post_list_success(self):
        """記事一覧の取得が成功すること"""
        # 公開済み記事を作成
        Post.objects.create(
            title='公開記事1',
            author=self.user,
            content='テスト内容1',
            status='published'
        )
        Post.objects.create(
            title='公開記事2',
            author=self.user,
            content='テスト内容2',
            status='published'
        )

        response = self.client.get(self.url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 2
        assert len(response.data['results']) == 2

    def test_only_published_posts_shown(self):
        """公開済み記事のみ表示されること"""
        # 公開済み記事
        published_post = Post.objects.create(
            title='公開記事',
            author=self.user,
            content='公開内容',
            status='published'
        )
        # 下書き記事
        draft_post = Post.objects.create(
            title='下書き記事',
            author=self.user,
            content='下書き内容',
            status='draft'
        )

        response = self.client.get(self.url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 1
        assert response.data['results'][0]['title'] == '公開記事'

    def test_posts_ordered_by_publish_date(self):
        """記事が公開日時の降順で並ぶこと"""
        # 古い記事
        old_post = Post.objects.create(
            title='古い記事',
            author=self.user,
            content='古い内容',
            status='published',
            publish=timezone.now() - timezone.timedelta(days=1)
        )
        # 新しい記事
        new_post = Post.objects.create(
            title='新しい記事',
            author=self.user,
            content='新しい内容',
            status='published',
            publish=timezone.now()
        )

        response = self.client.get(self.url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['results'][0]['title'] == '新しい記事'
        assert response.data['results'][1]['title'] == '古い記事'

    def test_pagination(self):
        """ページネーションが正しく動作すること"""
        # 15件の記事を作成
        for i in range(15):
            Post.objects.create(
                title=f'記事{i+1}',
                author=self.user,
                content=f'内容{i+1}',
                status='published'
            )

        # 1ページ目
        response = self.client.get(self.url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 15
        assert len(response.data['results']) == 10
        assert response.data['next'] is not None
        assert response.data['previous'] is None

        # 2ページ目
        response = self.client.get(self.url, {'page': 2})
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 5
        assert response.data['next'] is None
        assert response.data['previous'] is not None

    def test_empty_list(self):
        """記事が0件の場合も正常にレスポンスすること"""
        response = self.client.get(self.url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 0
        assert response.data['results'] == []


@pytest.mark.django_db
class TestPostDetailAPI:
    """記事詳細APIのテスト"""

    def setup_method(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )

    def test_get_published_post_detail(self):
        """公開済み記事の詳細が取得できること"""
        post = Post.objects.create(
            title='テスト記事',
            author=self.user,
            content='テスト内容',
            status='published'
        )
        url = reverse('blog-api:post-detail', kwargs={'slug': post.slug})

        response = self.client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['id'] == post.id
        assert response.data['title'] == 'テスト記事'
        assert response.data['content'] == 'テスト内容'
        assert response.data['author']['username'] == self.user.username
        assert 'publish' in response.data
        assert 'slug' in response.data

    def test_draft_post_not_found(self):
        """下書き記事は404エラーになること"""
        post = Post.objects.create(
            title='下書き記事',
            author=self.user,
            content='下書き内容',
            status='draft'
        )
        url = reverse('blog-api:post-detail', kwargs={'slug': post.slug})

        response = self.client.get(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_nonexistent_post_not_found(self):
        """存在しない記事は404エラーになること"""
        url = reverse('blog-api:post-detail', kwargs={'slug': 'non-existent-slug'})

        response = self.client.get(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_post_with_comments(self):
        """コメント付き記事の詳細が取得できること"""
        post = Post.objects.create(
            title='コメント付き記事',
            author=self.user,
            content='コメントテスト',
            status='published'
        )
        # コメントを追加
        post.comments.create(
            name='コメント投稿者',
            email='test@example.com',
            body='テストコメント',
            active=True
        )

        url = reverse('blog-api:post-detail', kwargs={'slug': post.slug})
        response = self.client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert 'comments' in response.data
        assert len(response.data['comments']) == 1
        assert response.data['comments'][0]['name'] == 'コメント投稿者'
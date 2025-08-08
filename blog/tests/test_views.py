import pytest
from django.urls import reverse
from django.test import Client
from django.contrib.auth import get_user_model
from blog.models import Post, Comment, CSPViolation
import json

User = get_user_model()


@pytest.mark.django_db
class TestPostListView:
    
    def test_post_list_view_status_code(self):
        """記事一覧ページが正しく表示されることをテスト"""
        client = Client()
        url = reverse('blog-web:post_list')
        response = client.get(url)
        
        assert response.status_code == 200
    
    def test_post_list_shows_only_published(self):
        """公開済みの記事のみ表示されることをテスト"""
        client = Client()
        user = User.objects.create_user(username='testuser')
        
        # 公開済みと下書きの記事を作成
        published_post = Post.objects.create(
            title='公開済み記事',
            slug='published-post',
            author=user,
            content='公開済みの内容',
            status='published'
        )
        
        draft_post = Post.objects.create(
            title='下書き記事',
            slug='draft-post',
            author=user,
            content='下書きの内容',
            status='draft'
        )
        
        # 記事一覧を取得
        url = reverse('blog-web:post_list')
        response = client.get(url)
        
        # 公開済みは表示、下書きは非表示
        assert published_post.title in response.content.decode()
        assert draft_post.title not in response.content.decode()
    
    def test_post_list_pagination(self):
        """ページネーションが機能することをテスト"""
        client = Client()
        user = User.objects.create_user(username='testuser')
        
        # 15件の記事を作成
        for i in range(15):
            Post.objects.create(
                title=f'記事{i}',
                slug=f'post-{i}',
                author=user,
                content='内容',
                status='published'
            )
        
        # 最初のページ
        url = reverse('blog-web:post_list')
        response = client.get(url)
        
        # 10件表示されることを確認
        content = response.content.decode()
        assert content.count('<article') == 10 or content.count('class="post"') == 10
        
        # 2ページ目
        response = client.get(url + '?page=2')
        assert response.status_code == 200

@pytest.mark.django_db
class TestPostDetailView:
    
    def test_post_detail_view_published(self):
        """公開済み記事の詳細が表示されることをテスト"""
        client = Client()
        user = User.objects.create_user(username='testuser')
        
        post = Post.objects.create(
            title='テスト記事',
            slug='test-post',
            author=user,
            content='テスト内容',
            status='published'
        )
        
        url = reverse('blog-web:post_detail', kwargs={'slug': post.slug})
        response = client.get(url)
        
        assert response.status_code == 200
        assert post.title in response.content.decode()
        assert post.content in response.content.decode()
    
    def test_post_detail_view_draft_returns_404(self):
        """下書き記事は404を返すことをテスト"""
        client = Client()
        user = User.objects.create_user(username='testuser')
        
        post = Post.objects.create(
            title='下書き記事',
            slug='draft-post',
            author=user,
            content='下書き内容',
            status='draft'
        )
        
        url = reverse('blog-web:post_detail', kwargs={'slug': post.slug})
        response = client.get(url)

        assert response.status_code == 404   

@pytest.mark.django_db
class TestPostCreateView:
    
    def test_post_create_requires_login(self):
        """記事作成にはログインが必要なことをテスト"""
        client = Client()
        url = reverse('blog-web:post_create')
        response = client.get(url)
        
        # ログインページにリダイレクトされる
        assert response.status_code == 302
        assert '/accounts/login/' in response.url
    
    def test_post_create_get_with_login(self):
        """ログイン済みユーザーが記事作成フォームを表示できることをテスト"""
        client = Client()
        user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        client.login(username='testuser', password='testpass123')
        
        url = reverse('blog-web:post_create')
        response = client.get(url)
        
        assert response.status_code == 200
        assert 'form' in response.context
        assert '新規投稿' in response.content.decode()
    
    def test_post_create_post_with_login(self):
        """ログイン済みユーザーが記事を作成できることをテスト"""
        client = Client()
        user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        client.login(username='testuser', password='testpass123')
        
        url = reverse('blog-web:post_create')
        data = {
            'title': '新しい記事',
            'content': '記事の内容',
            'status': 'published'
        }
        
        response = client.post(url, data)
        
        # リダイレクトされる
        assert response.status_code == 302
        
        # 記事が作成されている
        post = Post.objects.get(title='新しい記事')
        assert post.author == user
        assert post.content == '記事の内容'
        assert post.status == 'published'
        assert post.slug != ''  # slugが自動生成されている


@pytest.mark.django_db
class TestPostUpdateView:
    
    def test_post_update_requires_login(self):
        """記事編集にはログインが必要なことをテスト"""
        client = Client()
        user = User.objects.create_user(username='author')
        post = Post.objects.create(
            title='既存記事',
            author=user,
            content='内容'
        )
        
        url = reverse('blog-web:post_update', kwargs={'pk': post.pk})
        response = client.get(url)
        
        assert response.status_code == 302
        assert 'login' in response.url

    def test_post_update_by_author(self):
        """作者本人が記事を編集できることをテスト"""
        client = Client()
        user = User.objects.create_user(
            username='author',
            password='testpass123'
        )
        post = Post.objects.create(
            title='元のタイトル',
            author=user,
            content='元の内容',
            status='draft'
        )
        
        client.login(username='author', password='testpass123')
        
        # GET: フォーム表示
        url = reverse('blog-web:post_update', kwargs={'pk': post.pk})
        response = client.get(url)
        assert response.status_code == 200
        assert '記事編集' in response.content.decode()
        
        # POST: 更新（必須フィールドを確認）
        data = {
            'title': '更新後のタイトル',
            'content': '更新後の内容',
            'status': 'draft',  # statusも必要かも
            'action': 'save'
        }
        response = client.post(url, data)
        
        # デバッグ情報
        if response.status_code == 200:
            # フォームエラーがある場合
            print("Form errors:", response.context.get('form').errors if 'form' in response.context else "No form")
        
        # 更新されているか確認
        post.refresh_from_db()
        assert post.title == '更新後のタイトル'
        assert post.content == '更新後の内容'
    
    def test_post_update_by_other_user(self):
        """他のユーザーは編集できないことをテスト"""
        client = Client()
        author = User.objects.create_user(username='author')
        other_user = User.objects.create_user(
            username='other',
            password='testpass123'
        )
        
        post = Post.objects.create(
            title='記事',
            author=author,
            content='内容'
        )
        
        client.login(username='other', password='testpass123')
        
        url = reverse('blog-web:post_update', kwargs={'pk': post.pk})
        response = client.get(url)
        
        # リダイレクトされる（権限エラー）
        assert response.status_code == 302
        assert response.url == reverse('blog-web:post_list')


@pytest.mark.django_db
class TestCommentPostView:
    
    def test_comment_form_displayed_on_post_detail(self):
        """記事詳細ページにコメントフォームが表示されることをテスト"""
        client = Client()
        user = User.objects.create_user(username='author')
        post = Post.objects.create(
            title='テスト記事',
            slug='test-post',
            author=user,
            content='内容',
            status='published'
        )
        
        url = reverse('blog-web:post_detail', kwargs={'slug': post.slug})
        response = client.get(url)
        
        assert response.status_code == 200
        assert 'comment_form' in response.context
        assert 'コメント' in response.content.decode()
    
    def test_comment_submission(self):
        """コメントが正しく投稿されることをテスト"""
        client = Client()
        user = User.objects.create_user(username='author')
        post = Post.objects.create(
            title='テスト記事',
            slug='test-post',
            author=user,
            content='内容',
            status='published'
        )
        
        # コメントを投稿
        url = reverse('blog-web:post_detail', kwargs={'slug': post.slug})
        comment_data = {
            'name': '山田太郎',
            'email': 'yamada@example.com',
            'body': 'とても参考になりました！'
        }
        
        response = client.post(url, data=comment_data)
        
        # リダイレクトされることを確認
        assert response.status_code == 302
        assert response.url == post.get_absolute_url()
        
        # コメントが保存されていることを確認
        comment = Comment.objects.get(post=post)
        assert comment.name == '山田太郎'
        assert comment.email == 'yamada@example.com'
        assert comment.body == 'とても参考になりました！'
        assert comment.active is True
    
    def test_comment_displayed_after_submission(self):
        """投稿されたコメントが表示されることをテスト"""
        client = Client()
        user = User.objects.create_user(username='author')
        post = Post.objects.create(
            title='テスト記事',
            slug='test-post',
            author=user,
            content='内容',
            status='published'
        )
        
        # コメントを作成
        comment = Comment.objects.create(
            post=post,
            name='コメント投稿者',
            email='commenter@example.com',
            body='素晴らしい記事です！',
            active=True
        )
        
        # 記事詳細ページを表示
        url = reverse('blog-web:post_detail', kwargs={'slug': post.slug})
        response = client.get(url)
        
        # コメントが表示されていることを確認
        assert response.status_code == 200
        assert 'コメント投稿者' in response.content.decode()
        assert '素晴らしい記事です！' in response.content.decode()
    
    def test_inactive_comment_not_displayed(self):
        """非アクティブなコメントは表示されないことをテスト"""
        client = Client()
        user = User.objects.create_user(username='author')
        post = Post.objects.create(
            title='テスト記事',
            slug='test-post',
            author=user,
            content='内容',
            status='published'
        )
        
        # 非アクティブなコメントを作成
        comment = Comment.objects.create(
            post=post,
            name='スパマー',
            email='spam@example.com',
            body='スパムコメント',
            active=False
        )
        
        # 記事詳細ページを表示
        url = reverse('blog-web:post_detail', kwargs={'slug': post.slug})
        response = client.get(url)
        
        # 非アクティブなコメントは表示されない
        assert response.status_code == 200
        assert 'スパマー' not in response.content.decode()
        assert 'スパムコメント' not in response.content.decode()


@pytest.mark.django_db
class TestPostSearchView:
    
    def test_search_form_displayed(self):
        """検索フォームが表示されることをテスト"""
        client = Client()
        url = reverse('blog-web:post_search')
        response = client.get(url)
        
        assert response.status_code == 200
        assert 'form' in response.context
        assert '検索' in response.content.decode()
    
    def test_search_by_title(self):
        """タイトルで検索できることをテスト"""
        client = Client()
        user = User.objects.create_user(username='author')
        
        # テスト用の記事を作成
        post1 = Post.objects.create(
            title='Django入門ガイド',
            author=user,
            content='Djangoの基礎を学びます',
            status='published'
        )
        post2 = Post.objects.create(
            title='React入門ガイド',
            author=user,
            content='Reactの基礎を学びます',
            status='published'
        )
        post3 = Post.objects.create(
            title='Python基礎',
            author=user,
            content='Pythonの基礎を学びます',
            status='published'
        )
        
        # "Django"で検索
        url = reverse('blog-web:post_search')
        response = client.get(url, {'query': 'Django'})
        
        assert response.status_code == 200
        assert 'Django入門ガイド' in response.content.decode()
        assert 'React入門ガイド' not in response.content.decode()
        assert 'Python基礎' not in response.content.decode()
    
    def test_search_by_content(self):
        """本文で検索できることをテスト"""
        client = Client()
        user = User.objects.create_user(username='author')
        
        post1 = Post.objects.create(
            title='記事1',
            author=user,
            content='テスト駆動開発について説明します',
            status='published'
        )
        post2 = Post.objects.create(
            title='記事2',
            author=user,
            content='デプロイ方法について説明します',
            status='published'
        )
        
        # "テスト駆動"で検索
        url = reverse('blog-web:post_search')
        response = client.get(url, {'query': 'テスト駆動'})
        
        assert response.status_code == 200
        assert '記事1' in response.content.decode()
        assert '記事2' not in response.content.decode()
    
    def test_search_only_published_posts(self):
        """公開済み記事のみ検索されることをテスト"""
        client = Client()
        user = User.objects.create_user(username='author')
        
        # 公開済みと下書きの記事を作成
        published = Post.objects.create(
            title='公開済みDjango記事',
            author=user,
            content='内容',
            status='published'
        )
        draft = Post.objects.create(
            title='下書きDjango記事',
            author=user,
            content='内容',
            status='draft'
        )
        
        # "Django"で検索
        url = reverse('blog-web:post_search')
        response = client.get(url, {'query': 'Django'})
        
        assert response.status_code == 200
        assert '公開済みDjango記事' in response.content.decode()
        assert '下書きDjango記事' not in response.content.decode()
    
    def test_search_no_results(self):
        """検索結果がない場合のテスト"""
        client = Client()
        
        url = reverse('blog-web:post_search')
        response = client.get(url, {'query': '存在しないキーワード'})
        
        assert response.status_code == 200
        # 検索結果が0件であることを確認
        assert len(response.context['posts']) == 0


@pytest.mark.django_db
class TestCSPReportView:
    
    def test_csp_report_valid_json(self):
        """有効なCSPレポートを処理できることをテスト"""
        client = Client()
        url = reverse('blog-web:csp_report')
        
        csp_data = {
            'csp-report': {
                'violated-directive': 'script-src',
                'blocked-uri': 'https://evil.com/bad.js',
                'document-uri': 'https://example.com/page',
                'line-number': 10,
                'column-number': 5,
                'source-file': 'https://example.com/app.js',
                'original-policy': "script-src 'self'"
            }
        }
        
        response = client.post(
            url,
            data=json.dumps(csp_data),
            content_type='application/json',
            HTTP_USER_AGENT='Mozilla/5.0',
            REMOTE_ADDR='192.168.1.1'
        )
        
        assert response.status_code == 204  # No Content
        
        # CSPViolationが保存されていることを確認
        violation = CSPViolation.objects.get()
        assert violation.directive == 'script-src'
        assert violation.blocked_uri == 'https://evil.com/bad.js'
        assert violation.document_uri == 'https://example.com/page'
        assert violation.line_number == 10
        assert violation.user_agent == 'Mozilla/5.0'
        assert violation.ip_address == '192.168.1.1'
    
    def test_csp_report_invalid_json(self):
        """無効なJSONの場合400エラーを返すことをテスト"""
        client = Client()
        url = reverse('blog-web:csp_report')
        
        response = client.post(
            url,
            data='invalid json',
            content_type='application/json'
        )
        
        assert response.status_code == 400
        assert CSPViolation.objects.count() == 0
    
    def test_csp_report_empty_json(self):
        """空のJSONでもエラーにならないことをテスト"""
        client = Client()
        url = reverse('blog-web:csp_report')
        
        response = client.post(
            url,
            data=json.dumps({}),
            content_type='application/json'
        )
        
        # 空のデータでも204を返す（レポートは保存される）
        assert response.status_code == 204
    
    def test_csp_report_with_proxy_headers(self):
        """プロキシ経由のIPアドレスが正しく記録されることをテスト"""
        client = Client()
        url = reverse('blog-web:csp_report')
        
        csp_data = {
            'csp-report': {
                'violated-directive': 'img-src',
                'blocked-uri': 'https://cdn.example.com/image.jpg',
                'document-uri': 'https://example.com/'
            }
        }
        
        response = client.post(
            url,
            data=json.dumps(csp_data),
            content_type='application/json',
            HTTP_X_FORWARDED_FOR='203.0.113.1, 198.51.100.1'
        )
        
        assert response.status_code == 204
        
        violation = CSPViolation.objects.get()
        # X-Forwarded-Forの最初のIPが記録される
        assert violation.ip_address == '203.0.113.1'


@pytest.mark.django_db
class TestPostDeleteView:
    
    def test_post_delete_requires_login(self):
        """記事削除にはログインが必要なことをテスト"""
        client = Client()
        user = User.objects.create_user(username='author')
        post = Post.objects.create(
            title='削除対象記事',
            author=user,
            content='内容'
        )
        
        url = reverse('blog-web:post_delete', kwargs={'pk': post.pk})
        response = client.get(url)
        
        assert response.status_code == 302
        assert 'login' in response.url
    
    def test_post_delete_confirmation_page(self):
        """削除確認ページが表示されることをテスト"""
        client = Client()
        user = User.objects.create_user(
            username='author',
            password='testpass123'
        )
        post = Post.objects.create(
            title='削除対象記事',
            author=user,
            content='内容'
        )
        
        client.login(username='author', password='testpass123')
        
        url = reverse('blog-web:post_delete', kwargs={'pk': post.pk})
        response = client.get(url)
        
        assert response.status_code == 200
        assert '削除' in response.content.decode()
        assert post.title in response.content.decode()
    
    def test_post_delete_by_author(self):
        """作者本人が記事を削除できることをテスト"""
        client = Client()
        user = User.objects.create_user(
            username='author',
            password='testpass123'
        )
        post = Post.objects.create(
            title='削除対象記事',
            author=user,
            content='内容'
        )
        
        client.login(username='author', password='testpass123')
        
        # 削除前に記事が存在することを確認
        assert Post.objects.filter(pk=post.pk).exists()
        
        # POST で削除実行
        url = reverse('blog-web:post_delete', kwargs={'pk': post.pk})
        response = client.post(url)
        
        # リダイレクトされることを確認
        assert response.status_code == 302
        assert response.url == reverse('blog-web:post_list')
        
        # 記事が削除されていることを確認
        assert not Post.objects.filter(pk=post.pk).exists()
    
    def test_post_delete_by_other_user(self):
        """他のユーザーは削除できないことをテスト"""
        client = Client()
        author = User.objects.create_user(username='author')
        other_user = User.objects.create_user(
            username='other',
            password='testpass123'
        )
        
        post = Post.objects.create(
            title='削除対象記事',
            author=author,
            content='内容'
        )
        
        client.login(username='other', password='testpass123')
        
        # GET: 削除ページへのアクセス
        url = reverse('blog-web:post_delete', kwargs={'pk': post.pk})
        response = client.get(url)
        
        # 権限エラーでリダイレクト
        assert response.status_code == 302
        assert response.url == reverse('blog-web:post_list')
        
        # 記事はまだ存在する
        assert Post.objects.filter(pk=post.pk).exists()
    
    def test_post_delete_by_staff(self):
        """管理者は他人の記事も削除できることをテスト"""
        client = Client()
        author = User.objects.create_user(username='author')
        staff_user = User.objects.create_user(
            username='staff',
            password='testpass123',
            is_staff=True
        )
        
        post = Post.objects.create(
            title='削除対象記事',
            author=author,
            content='内容'
        )
        
        client.login(username='staff', password='testpass123')
        
        # POST で削除実行
        url = reverse('blog-web:post_delete', kwargs={'pk': post.pk})
        response = client.post(url)
        
        # 削除成功
        assert response.status_code == 302
        assert not Post.objects.filter(pk=post.pk).exists()


@pytest.mark.django_db
class TestPostDraftListView:
    
    def test_draft_list_requires_login(self):
        """下書き一覧にはログインが必要なことをテスト"""
        client = Client()
        url = reverse('blog-web:post_draft_list')
        response = client.get(url)
        
        assert response.status_code == 302
        assert 'login' in response.url
    
    def test_draft_list_shows_only_own_drafts(self):
        """自分の下書きのみ表示されることをテスト"""
        client = Client()
        user1 = User.objects.create_user(
            username='user1',
            password='testpass123'
        )
        user2 = User.objects.create_user(username='user2')
        
        # user1の下書き
        draft1 = Post.objects.create(
            title='私の下書き1',
            author=user1,
            content='内容',
            status='draft'
        )
        draft2 = Post.objects.create(
            title='私の下書き2',
            author=user1,
            content='内容',
            status='draft'
        )
        
        # user1の公開済み記事（表示されないはず）
        published = Post.objects.create(
            title='私の公開記事',
            author=user1,
            content='内容',
            status='published'
        )
        
        # user2の下書き（表示されないはず）
        other_draft = Post.objects.create(
            title='他人の下書き',
            author=user2,
            content='内容',
            status='draft'
        )
        
        # user1でログイン
        client.login(username='user1', password='testpass123')
        
        url = reverse('blog-web:post_draft_list')
        response = client.get(url)
        
        assert response.status_code == 200
        # 自分の下書きは表示される
        assert '私の下書き1' in response.content.decode()
        assert '私の下書き2' in response.content.decode()
        # 公開済みは表示されない
        assert '私の公開記事' not in response.content.decode()
        # 他人の下書きは表示されない
        assert '他人の下書き' not in response.content.decode()
    
    def test_draft_list_empty(self):
        """下書きがない場合のテスト"""
        client = Client()
        user = User.objects.create_user(
            username='user',
            password='testpass123'
        )
        
        client.login(username='user', password='testpass123')
        
        url = reverse('blog-web:post_draft_list')
        response = client.get(url)
        
        assert response.status_code == 200
        assert len(response.context['posts']) == 0
    
    def test_post_delete_by_other_user(self):
        """他のユーザーは削除できないことをテスト"""
        client = Client()
        author = User.objects.create_user(username='author')
        other_user = User.objects.create_user(
            username='other',
            password='testpass123'
        )
        
        post = Post.objects.create(
            title='削除対象記事',
            author=author,
            content='内容'
        )
        
        client.login(username='other', password='testpass123')
        
        # GET: 削除ページへのアクセス
        url = reverse('blog-web:post_delete', kwargs={'pk': post.pk})
        response = client.get(url)
        
        # 権限エラーでリダイレクト
        assert response.status_code == 302
        assert response.url == reverse('blog-web:post_list')
        
        # 記事はまだ存在する
        assert Post.objects.filter(pk=post.pk).exists()
    
    def test_post_delete_by_staff(self):
        """管理者は他人の記事も削除できることをテスト"""
        client = Client()
        author = User.objects.create_user(username='author')
        staff_user = User.objects.create_user(
            username='staff',
            password='testpass123',
            is_staff=True
        )
        
        post = Post.objects.create(
            title='削除対象記事',
            author=author,
            content='内容'
        )
        
        client.login(username='staff', password='testpass123')
        
        # POST で削除実行
        url = reverse('blog-web:post_delete', kwargs={'pk': post.pk})
        response = client.post(url)
        
        # 削除成功
        assert response.status_code == 302
        assert not Post.objects.filter(pk=post.pk).exists()


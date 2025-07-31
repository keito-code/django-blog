import pytest
from django.utils import timezone
from django.contrib.auth import get_user_model
from blog.models import Post, Comment
from blog.models import Post, Comment, CSPViolation  # CSPViolation を追加

User = get_user_model()

@pytest.mark.django_db
class TestPostModel:
    
    def test_post_creation(self):
        """記事が正しく作成されることをテスト"""
        # ユーザーを作成
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # 記事を作成
        post = Post.objects.create(
            title='テスト記事',
            slug='test-article',
            author=user,
            content='これはテスト記事です。',
            status='published'
        )
        
        # アサーション（期待する結果）
        assert post.title == 'テスト記事'
        assert post.slug == 'test-article'
        assert post.author == user
        assert post.status == 'published'
        assert post.publish is not None  # 公開日時が設定されているはず

    def test_post_str_representation(self):
        """Post モデルの文字列表現をテスト"""
        user = User.objects.create_user(username='testuser')
        post = Post.objects.create(
            title='サンプル記事',
            slug='sample-post',
            author=user,
            content='内容',
        )
        assert str(post) == 'サンプル記事'
        
    def test_post_ordering(self):
        """記事が公開日時の降順で並ぶことをテスト"""
        user = User.objects.create_user(username='testuser')
            
        # 異なる時刻で3つの記事を作成
        post1 = Post.objects.create(
            title='記事1',
            slug='post-1',
            author=user,
            content='内容1',
            publish=timezone.now() - timezone.timedelta(days=2)
        )
        post2 = Post.objects.create(
            title='記事2',
            slug='post-2',
            author=user,
            content='内容2',
            publish=timezone.now() - timezone.timedelta(days=1)
        )
        post3 = Post.objects.create(
            title='記事3',
            slug='post-3',
            author=user,
            content='内容3',
            publish=timezone.now()
        )
        
        # 最新の記事が最初に来ることを確認
        posts = Post.objects.all()
        assert posts[0] == post3
        assert posts[1] == post2
        assert posts[2] == post1

    def test_slug_auto_generation(self):
        """slugが自動生成されることをテスト"""
        user = User.objects.create_user(username='testuser')
        
        post = Post.objects.create(
            title='Test Article',  # 英語でテスト
            author=user,
            content='内容'
        )
        
        # slugが自動生成されている
        assert post.slug != ''
        assert post.slug == 'test-article'        


    def test_slug_uniqueness(self):
        """重複しないslugが生成されることをテスト"""
        user = User.objects.create_user(username='testuser')
        
        # 同じタイトルで2つの記事を作成
        post1 = Post.objects.create(
            title='Same Title',
            author=user,
            content='内容1'
        )
        post2 = Post.objects.create(
            title='Same Title',
            author=user,
            content='内容2'
        )
        
        # slugが異なることを確認
        assert post1.slug == 'same-title'
        assert post2.slug != post1.slug
        # 番号が付いていることを確認
        assert post2.slug == 'same-title-1'

    def test_japanese_title_slug(self):
        """日本語タイトルのslug生成をテスト"""
        user = User.objects.create_user(username='testuser')
        
        post = Post.objects.create(
            title='テスト記事',
            author=user,
            content='内容'
        )
        
        # 空文字列にならないことを確認
        assert post.slug != ''
         # post- プレフィックスがあることを確認
        assert post.slug.startswith('post-')
        assert len(post.slug) == 13  # 'post-' + 8文字



@pytest.mark.django_db
class TestCommentModel:
    
    def test_comment_creation(self):
        """コメントが正しく作成されることをテスト"""
        # ユーザーと記事を作成
        user = User.objects.create_user(username='testuser')
        post = Post.objects.create(
            title='Test Post',
            slug='test-post',
            author=user,
            content='Test content',
            status='published'
        )
        
        # コメントを作成
        comment = Comment.objects.create(
            post=post,
            name='コメント投稿者',
            email='commenter@example.com',
            body='これはテストコメントです。'
        )
        
        # アサーション
        assert comment.post == post
        assert comment.name == 'コメント投稿者'
        assert comment.email == 'commenter@example.com'
        assert comment.body == 'これはテストコメントです。'
        assert comment.created is not None
        assert comment.active is True  # デフォルトで有効

    def test_comment_str_representation(self):
        """Commentモデルの文字列表現をテスト"""
        user = User.objects.create_user(username='testuser')
        post = Post.objects.create(
            title='Test Post',
            author=user,
            content='Test content'
        )
        
        comment = Comment.objects.create(
            post=post,
            name='山田太郎',
            email='yamada@example.com',
            body='コメント内容'
        )
        
        expected = '山田太郎によるコメント: Test Post'
        assert str(comment) == expected

    def test_comment_ordering(self):
        """コメントが作成日時順に並ぶことをテスト"""
        user = User.objects.create_user(username='testuser')
        post = Post.objects.create(
            title='Test Post',
            author=user,
            content='Test content'
        )
        
        # 3つのコメントを異なる時刻で作成
        comment1 = Comment.objects.create(
            post=post,
            name='User1',
            email='user1@example.com',
            body='First comment'
        )
        
        # 少し待つ
        import time
        time.sleep(0.1)
        
        comment2 = Comment.objects.create(
            post=post,
            name='User2',
            email='user2@example.com',
            body='Second comment'
        )
        
        # 古い順（作成日時の昇順）で並ぶことを確認
        comments = Comment.objects.all()
        assert comments[0] == comment1
        assert comments[1] == comment2
    
    def test_comment_inactive(self):
        """非アクティブなコメントのテスト"""
        user = User.objects.create_user(username='testuser')
        post = Post.objects.create(
            title='Test Post',
            author=user,
            content='Test content'
        )
        
        # 非アクティブなコメントを作成
        comment = Comment.objects.create(
            post=post,
            name='Spammer',
            email='spam@example.com',
            body='Spam comment',
            active=False
        )
        
        # activeがFalseであることを確認
        assert comment.active is False
        
        # アクティブなコメントのみをフィルタ
        active_comments = Comment.objects.filter(active=True)
        assert comment not in active_comments

@pytest.mark.django_db
class TestCSPViolationModel:
    
    def test_csp_violation_creation(self):
        """CSP違反レポートが正しく作成されることをテスト"""
        violation = CSPViolation.objects.create(
            directive='script-src',
            blocked_uri='https://evil.com/malicious.js',
            document_uri='https://example.com/page',
            line_number=42,
            column_number=15,
            source_file='https://example.com/app.js',
            original_policy="script-src 'self'",
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
            ip_address='192.168.1.1'
        )
        
        # アサーション
        assert violation.directive == 'script-src'
        assert violation.blocked_uri == 'https://evil.com/malicious.js'
        assert violation.document_uri == 'https://example.com/page'
        assert violation.line_number == 42
        assert violation.column_number == 15
        assert violation.is_resolved is False  # デフォルトで未対応
        assert violation.created is not None
    
    def test_csp_violation_str_representation(self):
        """CSPViolationモデルの文字列表現をテスト"""
        violation = CSPViolation.objects.create(
            directive='style-src',
            document_uri='https://example.com',
            original_policy="style-src 'self'"
        )
        
        # 文字列表現に必要な要素が含まれているか
        violation_str = str(violation)
        assert 'CSP違反:' in violation_str
        assert 'style-src' in violation_str
        # 日付形式が含まれているか（YYYY-MM-DD HH:MM）
        assert violation.created.strftime("%Y-%m-%d %H:%M") in violation_str

    def test_csp_violation_ordering(self):
        """CSP違反が作成日時の降順で並ぶことをテスト"""
        # 3つの違反を作成
        violation1 = CSPViolation.objects.create(
            directive='script-src',
            document_uri='https://example.com/page1',
            original_policy="script-src 'self'"
        )
        
        import time
        time.sleep(0.1)
        
        violation2 = CSPViolation.objects.create(
            directive='img-src',
            document_uri='https://example.com/page2',
            original_policy="img-src 'self'"
        )
        
        # 最新のものが最初に来ることを確認（降順）
        violations = CSPViolation.objects.all()
        assert violations[0] == violation2
        assert violations[1] == violation1
    
    def test_csp_violation_optional_fields(self):
        """省略可能なフィールドのテスト"""
        # 必須フィールドのみで作成
        violation = CSPViolation.objects.create(
            directive='font-src',
            document_uri='https://example.com',
            original_policy="font-src 'self'"
        )
        
        # 省略可能フィールドの確認
        assert violation.blocked_uri == ''
        assert violation.line_number is None
        assert violation.column_number is None
        assert violation.source_file == ''
        assert violation.user_agent == ''
        assert violation.ip_address is None
        assert violation.notes == ''
    
    def test_csp_violation_resolved_status(self):
        """対応済みステータスのテスト"""
        violation = CSPViolation.objects.create(
            directive='connect-src',
            document_uri='https://example.com',
            original_policy="connect-src 'self'"
        )
        
        # デフォルトは未対応
        assert violation.is_resolved is False
        
        # 対応済みに変更
        violation.is_resolved = True
        violation.notes = '外部APIの許可リストに追加済み'
        violation.save()
        
        # 変更が保存されているか確認
        updated_violation = CSPViolation.objects.get(pk=violation.pk)
        assert updated_violation.is_resolved is True
        assert '許可リスト' in updated_violation.notes
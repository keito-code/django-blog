"""Serializerのテスト（バリデーション+出力）"""

import pytest
from django.contrib.auth import get_user_model
from blog.models import Post, Category
from blog.serializers import (
    CategorySerializer,
    PostListSerializer,
    PostDetailSerializer,
    PostCreateSerializer,
    PostUpdateSerializer
)

User = get_user_model()


@pytest.mark.django_db
class TestPostSerializers:
    """PostSerializer全般のテスト"""
    
    # === Fixtures ===
    @pytest.fixture
    def user(self):
        return User.objects.create_user(
            username='test',
            email='test@example.com',
            password='pass'
        )

    @pytest.fixture
    def post(self, user):
        return Post.objects.create(
            title='Original Title',
            content='Original Content',
            author=user
        )

    
    # === バリデーションテスト ===
    def test_create_validation_title_too_short(self):
        """タイトルの最小文字数検証"""
        data = {'title': 'ab', 'content': 'content'}
        serializer = PostCreateSerializer(data=data)
        assert not serializer.is_valid()
        assert 'title' in serializer.errors
        assert '3文字以上' in str(serializer.errors['title'])
    
    def test_create_validation_same_title_content(self):
        """タイトルと本文の重複禁止"""
        data = {'title': 'Same', 'content': 'Same'}
        serializer = PostCreateSerializer(data=data)
        assert not serializer.is_valid()
        assert 'non_field_errors' in serializer.errors

    def test_create_valid_data(self):
        """作成時：正常データの検証"""
        data = {
            'title': 'Valid Title',
            'content': 'Different Content',
            'status': 'draft'
        }
        serializer = PostCreateSerializer(data=data)
        assert serializer.is_valid()
        assert serializer.validated_data['status'] == 'draft'

    def test_update_validation_title_too_short(self):
        """更新時：タイトルの最小文字数検証"""
        data = {'title': 'ab'}
        serializer = PostUpdateSerializer(data=data)
        assert not serializer.is_valid()
        assert 'title' in serializer.errors

    def test_update_validation_same_title_content(self):
        """更新時：タイトルと本文の重複禁止"""
        data = {'title': 'Same', 'content': 'Same'}
        serializer = PostUpdateSerializer(data=data)
        assert not serializer.is_valid()
        assert 'non_field_errors' in serializer.errors

    def test_update_partial_valid(self):
        """更新時：部分更新の正常動作"""
        # タイトルのみ更新
        data = {'title': 'Updated Title'}
        serializer = PostUpdateSerializer(data=data)
        assert serializer.is_valid()
        
        # コンテンツのみ更新
        data = {'content': 'Updated Content'}
        serializer = PostUpdateSerializer(data=data)
        assert serializer.is_valid()

    def test_create_serializer_no_slug_field(self):
        """作成時：slugフィールドが存在しないこと"""
        data = {
            'title': 'Test Title',
            'content': 'Test Content',
            'slug': 'manual-slug'  # 手動で指定しても
        }
        serializer = PostCreateSerializer(data=data)
        assert serializer.is_valid()
        # slugがvalidated_dataに含まれないことを確認
        assert 'slug' not in serializer.validated_data

    def test_update_serializer_no_slug_field(self):
        """更新時：slugフィールドが存在しないこと"""
        data = {
            'title': 'Updated Title',
            'slug': 'new-slug'  # 手動で指定しても
        }
        serializer = PostUpdateSerializer(data=data)
        assert serializer.is_valid()
        # slugがvalidated_dataに含まれないことを確認
        assert 'slug' not in serializer.validated_data
    
    def test_post_slug_auto_generation(self, user):
        """投稿作成時のslug自動生成確認"""
        # モデルレベルでのテスト（実際の動作確認）
        post = Post.objects.create(
            title='Test Post Title',
            content='Content',
            author=user
        )
        assert post.slug is not None
        assert post.slug != ''
        # 英語タイトルならslugifyされている
        assert 'test' in post.slug.lower()

    def test_post_slug_immutable(self, post):
        """slugが更新されないことの確認"""
        original_slug = post.slug
        post.title = 'Completely New Title'
        post.save()
        post.refresh_from_db()
        # タイトルを変更してもslugは変わらない
        assert post.slug == original_slug

    
    # === 出力テスト（DB必要） ===
    def test_list_serializer_author_privacy(self, user):
        """著者情報が匿名化されること"""
        post = Post.objects.create(
            title='Test',
            content='Content',
            author=user
        )
        serializer = PostListSerializer(post)
        assert serializer.data['author_name'] == f"Author{user.id}"
        assert 'username' not in str(serializer.data)
        assert 'email' not in str(serializer.data)
    
    def test_detail_serializer_includes_content(self, post):
        """詳細：コンテンツが含まれること"""
        serializer = PostDetailSerializer(post)
        assert 'content' in serializer.data
        assert serializer.data['content'] == post.content
    
    def test_list_serializer_excludes_content(self, post):
        """一覧：コンテンツが含まれないこと"""
        serializer = PostListSerializer(post)
        assert 'content' not in serializer.data

    def test_category_serializer_readonly_fields_and_output(self):
        """カテゴリ：slugがread_only、post_countが出力に含まれる"""
        category = Category.objects.create(name='Test Category')
        serializer = CategorySerializer(category, data={'name': 'Updated', 'slug': 'manual'}, partial=True)
        if serializer.is_valid():
            assert 'slug' not in serializer.validated_data

        # シリアライザ出力の確認
        output_serializer = CategorySerializer(category)
        assert 'id' in output_serializer.data
        assert 'name' in output_serializer.data
        assert 'slug' in output_serializer.data
        assert 'post_count' in output_serializer.data
        assert output_serializer.data['post_count'] == 0  # デフォルト値

@pytest.mark.django_db
class TestPostSerializersSanitization:
    """サニタイズ機能のテスト"""
    
    def test_create_sanitize_script_in_title(self):
        """作成時：タイトルのスクリプトタグ除去"""
        data = {
            'title': '<script>alert("XSS")</script>Valid Title',
            'content': 'Test content',
            'status': 'draft'
        }
        serializer = PostCreateSerializer(data=data)
        assert serializer.is_valid()
        assert '<script>' not in serializer.validated_data['title']
        assert 'alert' not in serializer.validated_data['title']
        assert 'Valid Title' in serializer.validated_data['title']
    
    def test_create_sanitize_html_in_title(self):
        """作成時：タイトルのHTMLタグ完全除去"""
        data = {
            'title': '<h1>Title</h1> with <strong>tags</strong>',
            'content': 'Test content',
            'status': 'draft'
        }
        serializer = PostCreateSerializer(data=data)
        assert serializer.is_valid()
        assert serializer.validated_data['title'] == 'Title with tags'
    
    def test_create_sanitize_content_dangerous_tags(self):
        """作成時：コンテンツの危険なタグ除去"""
        data = {
            'title': 'Test Title',
            'content': 'Normal <script>evil()</script> text <onclick="bad()">click</onclick>',
            'status': 'draft'
        }
        serializer = PostCreateSerializer(data=data)
        assert serializer.is_valid()
        assert '<script>' not in serializer.validated_data['content']
        assert 'onclick' not in serializer.validated_data['content']
        assert 'Normal' in serializer.validated_data['content']
        assert 'text' in serializer.validated_data['content']
    
    def test_create_sanitize_content_safe_tags(self):
        """作成時：コンテンツの安全なタグは保持"""
        data = {
            'title': 'Test Title',
            'content': '<p>Paragraph</p><strong>Bold</strong><em>Italic</em><code>Code</code>',
            'status': 'draft'
        }
        serializer = PostCreateSerializer(data=data)
        assert serializer.is_valid()
        content = serializer.validated_data['content']
        assert '<p>' in content
        assert '<strong>' in content
        assert '<em>' in content
        assert '<code>' in content
    
    def test_update_partial_sanitize_title(self):
        """更新時：タイトルのみのサニタイズ"""
        data = {'title': '<b>Updated</b> Title'}
        serializer = PostUpdateSerializer(data=data, partial=True)
        assert serializer.is_valid()
        assert serializer.validated_data['title'] == 'Updated Title'
    
    def test_validation_after_sanitization(self):
        """サニタイズ後のバリデーション（3文字チェック）"""
        # HTMLタグ除去後に2文字になるケース
        data = {
            'title': '<strong>AB</strong>',  # サニタイズ後 "AB"
            'content': 'Valid content',
            'status': 'draft'
        }
        serializer = PostCreateSerializer(data=data)
        assert not serializer.is_valid()
        assert 'title' in serializer.errors
        assert '3文字以上' in str(serializer.errors['title'])
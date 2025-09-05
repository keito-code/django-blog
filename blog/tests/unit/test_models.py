"""
Blogモデルのユニットテスト
slug自動生成、日本語対応、重複処理等のビジネスロジックをテスト
"""
import re
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from blog.models import Post, Category

User = get_user_model()


class TestCategoryModel(TestCase):
    """カテゴリモデルのテスト"""
    
    def test_create_category(self):
        """カテゴリの作成"""
        category = Category.objects.create(
            name="テクノロジー",
            slug="technology"
        )
        self.assertEqual(category.name, "テクノロジー")
        self.assertEqual(category.slug, "technology")
        self.assertEqual(str(category), "テクノロジー")
    
    def test_slug_uniqueness_constraint(self):
        """slugの一意性制約（IntegrityError）"""
        Category.objects.create(name="Tech", slug="tech")
        with self.assertRaises(IntegrityError):
            Category.objects.create(name="Technology", slug="tech")
    
    def test_auto_slug_generation_english(self):
        """英語名からのslug自動生成"""
        category = Category.objects.create(name="Machine Learning")
        self.assertIsNotNone(category.slug)
        # slugify の標準的な動作確認
        self.assertTrue(all(c.isalnum() or c == '-' for c in category.slug))
        self.assertTrue(category.slug.islower())
    
    def test_auto_slug_generation_japanese(self):
        """日本語名からのslug自動生成（実装非依存）"""
        category = Category.objects.create(name="日本語カテゴリ")
        
        # 基本的な要件のみ検証（実装詳細に依存しない）
        self.assertIsNotNone(category.slug, "slugが生成されていない")
        self.assertNotEqual(category.slug, "", "slugが空文字")
        self.assertTrue(category.slug.isascii(), "slugにASCII以外の文字が含まれている")
        # slug形式の妥当性（英数字とハイフンのみ）
        self.assertTrue(
            re.match(r'^[a-z0-9]+(?:-[a-z0-9]+)*$', category.slug),
            f"slugが適切な形式ではない: {category.slug}"
        )
    
    def test_auto_slug_uniqueness_on_save(self):
        """save()メソッドでの自動slug重複回避"""
        # 同じ名前で2つ作成
        cat1 = Category.objects.create(name="Programming")
        cat2 = Category.objects.create(name="Programming")
        
        # slugが自動的にユニークになっている
        self.assertNotEqual(cat1.slug, cat2.slug)
        # 2つ目のslugに元のslugが含まれている（実装詳細に依存しない）
        self.assertIn(cat1.slug.split('-')[0], cat2.slug)


class TestPostModel(TestCase):
    """投稿モデルのテスト"""
    
    def setUp(self):
        """テスト用データのセットアップ"""
        self.user = User.objects.create_user(
            email='author@example.com',
            password='password123'
        )
        self.category = Category.objects.create(
            name="Tech",
            slug="tech"
        )

    def test_create_post_with_explicit_slug(self):
        """明示的なslugを指定して投稿作成"""
        post = Post.objects.create(
            title="Test Post",
            slug="test-post",
            content="This is test content",
            author=self.user,
            category=self.category,
            status='draft'
        )
        
        self.assertEqual(post.title, "Test Post")
        self.assertEqual(post.slug, "test-post")
        self.assertEqual(post.author, self.user)
        self.assertEqual(post.category, self.category)
        self.assertEqual(post.status, 'draft')
        self.assertIsNotNone(post.created_at)
        self.assertIsNotNone(post.updated_at)
    
    def test_auto_slug_generation_from_english_title(self):
        """英語タイトルからのslug自動生成"""
        post = Post.objects.create(
            title="Hello World Post",
            content="Content",
            author=self.user,
            category=self.category
        )
        
        # 生成されたslugの妥当性確認（実装詳細に依存しない）
        self.assertIsNotNone(post.slug)
        self.assertTrue(all(c.isalnum() or c == '-' for c in post.slug))
        self.assertTrue(post.slug.islower())
        # タイトルの単語が何らかの形で含まれている
        self.assertTrue(
            'hello' in post.slug.lower() or 
            'world' in post.slug.lower() or
            'post' in post.slug.lower()
        )
    
    def test_auto_slug_generation_from_japanese_title(self):
        """日本語タイトルからのslug生成（実装非依存）"""
        post = Post.objects.create(
            title="日本語のタイトル",
            content="内容",
            author=self.user,
            category=self.category
        )
        
        # 基本的な要件のみ検証
        self.assertIsNotNone(post.slug, "slugが生成されていない")
        self.assertNotEqual(post.slug, "", "slugが空文字")
        self.assertTrue(post.slug.isascii(), "slugにASCII以外の文字が含まれている")
        # slug形式の妥当性
        self.assertTrue(
            re.match(r'^[a-z0-9]+(?:-[a-z0-9]+)*$', post.slug),
            f"slugが適切な形式ではない: {post.slug}"
        )
    
    def test_duplicate_slug_auto_handling_in_model(self):
        """モデルのsave()での自動重複回避"""
        # 最初の投稿
        post1 = Post.objects.create(
            title="First Post",
            slug="same-slug",
            content="Content 1",
            author=self.user,
            category=self.category
        )
        
        # 2つ目は同じslugを指定
        post2 = Post(
            title="Second Post",
            slug="same-slug",
            content="Content 2",
            author=self.user,
            category=self.category
        )
        post2.save()
        
        # 重複が回避されている
        self.assertNotEqual(post1.slug, post2.slug)
        self.assertEqual(post1.slug, "same-slug")
        # 2つ目のslugに元のslugが含まれている
        self.assertIn("same-slug", post2.slug)
    
    def test_duplicate_title_generates_unique_slugs(self):
        """同じタイトルから異なるslugを生成"""
        post1 = Post.objects.create(
            title="Same Title",
            content="Content 1",
            author=self.user,
            category=self.category
        )
        
        post2 = Post.objects.create(
            title="Same Title",
            content="Content 2",
            author=self.user,
            category=self.category
        )
        
        # 自動生成されたslugが異なる
        self.assertNotEqual(post1.slug, post2.slug)
        # 両方のslugが妥当な形式
        for post in [post1, post2]:
            self.assertTrue(
                re.match(r'^[a-z0-9]+(?:-[a-z0-9]+)*$', post.slug)
            )
    
    def test_post_status_transitions(self):
        """投稿ステータスの遷移"""
        post = Post.objects.create(
            title="Status Test",
            content="Content",
            author=self.user,
            category=self.category,
            status='draft'
        )
        
        # draft -> published
        post.status = 'published'
        post.published_at = timezone.now()
        post.save()
        
        self.assertEqual(post.status, 'published')
        self.assertIsNotNone(post.published_at)
        
        # published -> archived
        post.status = 'archived'
        post.save()
        self.assertEqual(post.status, 'archived')
    
    def test_str_representation(self):
        """文字列表現のテスト"""
        post = Post.objects.create(
            title="String Test Post",
            content="Content",
            author=self.user,
            category=self.category
        )
        
        self.assertEqual(str(post), "String Test Post")
    
    def test_post_ordering(self):
        """投稿の並び順（作成日時の降順）"""
        post1 = Post.objects.create(
            title="First Post",
            content="Content",
            author=self.user,
            category=self.category
        )
        
        post2 = Post.objects.create(
            title="Second Post",
            content="Content",
            author=self.user,
            category=self.category
        )
        
        posts = Post.objects.all()
        # 新しい投稿が先に来る（降順）
        self.assertEqual(posts[0], post2)
        self.assertEqual(posts[1], post1)
    
    def test_slug_immutability_on_update(self):
        """更新時にslugが変わらないことを確認"""
        post = Post.objects.create(
            title="Original Title",
            content="Content",
            author=self.user,
            category=self.category
        )
        original_slug = post.slug
        
        # タイトルを変更して保存
        post.title = "Updated Title"
        post.save()
        
        # slugは変わらない
        self.assertEqual(post.slug, original_slug)
    
    
class TestModelValidation(TestCase):
    """モデルのバリデーションテスト"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='password123'
        )
        self.category = Category.objects.create(
            name="Test",
            slug="test"
        )
    
    def test_post_title_required(self):
        """投稿タイトルは必須"""
        post = Post(
            content="Content without title",
            author=self.user,
            category=self.category
        )
        
        with self.assertRaises(ValidationError) as cm:
            post.full_clean()
        
        self.assertIn('title', cm.exception.message_dict)
    
    def test_post_content_required(self):
        """投稿内容は必須"""
        post = Post(
            title="Title without content",
            author=self.user,
            category=self.category
        )
        
        with self.assertRaises(ValidationError) as cm:
            post.full_clean()
        
        self.assertIn('content', cm.exception.message_dict)
    
    def test_slug_format_validation(self):
        """slugのフォーマット検証"""
        category = Category(
            name="Invalid Slug Test",
            slug="invalid slug with spaces"
        )
        
        with self.assertRaises(ValidationError) as cm:
            category.full_clean()
        
        self.assertIn('slug', cm.exception.message_dict)
    
    def test_empty_slug_allowed_for_auto_generation(self):
        """空のslugは許可（自動生成のため）"""
        category = Category(
            name="Test Category"
            # slugを指定しない
        )
        
        # full_clean()はエラーを発生させない（slugは空でOK）
        try:
            category.full_clean()
        except ValidationError:
            self.fail("空のslugでValidationErrorが発生した")
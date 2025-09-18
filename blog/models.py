from django.db import models
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils.text import slugify
import random
import string

class Category(models.Model):
    """カテゴリモデル（最小限の実装）"""
    name = models.CharField('カテゴリ名', max_length=100)
    slug = models.SlugField('スラッグ', max_length=100, unique=True, blank=True)
    created_at = models.DateTimeField('作成日時', auto_now_add=True)
    updated_at = models.DateTimeField('更新日時', auto_now=True)
    
    class Meta:
        ordering = ('name',)
        verbose_name = 'カテゴリ'
        verbose_name_plural = 'カテゴリ'

    def save(self, *args, **kwargs):
        """保存時にslugを自動生成（Postモデルと同じロジック）"""
        if not self.slug:
            # まず通常のslugifyを試す
            base_slug = slugify(self.name)
            
            # 空文字列の場合（日本語など）はランダム文字列を生成
            if not base_slug:
                base_slug = 'category-' + ''.join(random.choices(
                    string.ascii_lowercase + string.digits, 
                    k=8
                ))
            
            slug = base_slug
            counter = 1
            
            # 重複チェック（自分自身を除外）
            qs = Category.objects.filter(slug=slug)
            if self.pk:
                qs = qs.exclude(pk=self.pk)
            
            while qs.exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
                qs = Category.objects.filter(slug=slug)
                if self.pk:
                    qs = qs.exclude(pk=self.pk)
            
            self.slug = slug
        
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

class Post(models.Model):
    STATUS_CHOICES = (
        ('draft', '下書き'),
        ('published', '公開'),
    )
    
    title = models.CharField('タイトル', max_length=200)
    slug = models.SlugField('スラッグ', max_length=200, unique=True, blank=True)
    content = models.TextField('本文')
    author = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='blog_posts', 
        verbose_name='投稿者'
    )
    category = models.ForeignKey(
        Category, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,  
        related_name='posts', 
        verbose_name='カテゴリ'
    )
    status = models.CharField(
        'ステータス',
         max_length=10, 
         choices=STATUS_CHOICES, 
         default='draft'
    )
    created_at = models.DateTimeField('作成日時', auto_now_add=True)
    updated_at = models.DateTimeField('更新日時', auto_now=True)
    
    class Meta:
        ordering = ('-created_at',)
        verbose_name = '記事'
        verbose_name_plural = '記事'
        
    def __str__(self):
        return self.title
        
    def get_absolute_url(self):
        return reverse('blog-web:post_detail', kwargs={'slug': self.slug})

    def save(self, *args, **kwargs):
        """保存時にslugを自動生成（重複チェック付き）"""
        if not self.slug:
            # まず通常のslugifyを試す
            base_slug = slugify(self.title)

            # 空文字列の場合（日本語など）はランダム文字列を生成
            if not base_slug:
                base_slug = 'post-' + ''.join(random.choices(
                    string.ascii_lowercase + string.digits, 
                    k=8
                ))

            slug = base_slug
            counter = 1
            
            # 重複チェック
            while Post.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            
            self.slug = slug
        
        super().save(*args, **kwargs)

    @property
    def is_published(self):
        return self.status == 'published'
    
class Comment(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments', verbose_name='記事')
    name = models.CharField('名前', max_length=80)
    email = models.EmailField('メールアドレス')
    body = models.TextField('コメント')
    created_at = models.DateTimeField('作成日時', auto_now_add=True)
    updated_at = models.DateTimeField('更新日時', auto_now=True)
    active = models.BooleanField('有効', default=True)
    
    class Meta:
        ordering = ('created_at',)
        verbose_name = 'コメント'
        verbose_name_plural = 'コメント'
        
    def __str__(self):
        return f'{self.name}によるコメント: {self.post}'


class CSPViolation(models.Model):
    """CSP違反レポートを記録するモデル"""
    
    # CSP違反の種類
    directive = models.CharField('違反ディレクティブ', max_length=100, help_text='script-src, style-src など')
    blocked_uri = models.TextField('ブロックされたURI', blank=True, help_text='違反したリソースのURI')
    document_uri = models.TextField('ドキュメントURI', help_text='違反が発生したページのURI')
    line_number = models.IntegerField('行番号', null=True, blank=True)
    column_number = models.IntegerField('列番号', null=True, blank=True)
    source_file = models.TextField('ソースファイル', blank=True)
    original_policy = models.TextField('元のポリシー', help_text='違反したCSPポリシー')
    
    # 環境情報
    user_agent = models.TextField('ユーザーエージェント', blank=True)
    ip_address = models.GenericIPAddressField('IPアドレス', null=True, blank=True)
    
    # 日時
    created = models.DateTimeField('発生日時', auto_now_add=True)
    
    # 処理状況
    is_resolved = models.BooleanField('対応済み', default=False)
    notes = models.TextField('メモ', blank=True)
    
    class Meta:
        ordering = ('-created',)
        verbose_name = 'CSP違反レポート'
        verbose_name_plural = 'CSP違反レポート'
        
    def __str__(self):
        return f'CSP違反: {self.directive} - {self.created.strftime("%Y-%m-%d %H:%M")}'
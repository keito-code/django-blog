from django.db import models
from django.contrib.auth.models import User
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
from enum import unique
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.urls import reverse


class Post(models.Model):
    STATUS_CHOICES = (
        ('draft', '下書き'),
        ('published', '公開'),
    )
    
    title = models.CharField('タイトル', max_length=200)
    slug = models.SlugField('スラッグ', max_length=200, unique=True, blank=True)
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='blog_posts', verbose_name='投稿者')
    content = models.TextField('本文')
    publish = models.DateTimeField('公開日時', default=timezone.now)
    created = models.DateTimeField('作成日時', auto_now_add=True)
    updated = models.DateTimeField('更新日時', auto_now=True)
    status = models.CharField('ステータス', max_length=10, choices=STATUS_CHOICES, default='draft')
    
    class Meta:
        ordering = ('-publish',)
        verbose_name = '記事'
        verbose_name_plural = '記事'
        
    def __str__(self):
        return self.title
        
    def get_absolute_url(self):
        return reverse('blog:post_detail', kwargs={'slug': self.slug})


class Comment(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments', verbose_name='記事')
    name = models.CharField('名前', max_length=80)
    email = models.EmailField('メールアドレス')
    body = models.TextField('コメント')
    created = models.DateTimeField('作成日時', auto_now_add=True)
    updated = models.DateTimeField('更新日時', auto_now=True)
    active = models.BooleanField('有効', default=True)
    
    class Meta:
        ordering = ('created',)
        verbose_name = 'コメント'
        verbose_name_plural = 'コメント'
        
    def __str__(self):
        return f'{self.name}によるコメント: {self.post}'
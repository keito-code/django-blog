from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Post, Comment
import bleach


class AuthorSerializer(serializers.ModelSerializer):
    """投稿者用シリアライザー"""
    class Meta:
        model = User
        fields = ['id', 'username']


class CommentSerializer(serializers.ModelSerializer):
    """コメント用シリアライザー"""
    class Meta:
        model = Comment
        fields = ['id', 'name', 'email', 'body', 'created']
        read_only_fields = ['created']
    
    def validate_body(self, value):
        """コメント本文のサニタイズ（プレーンテキストのみ許可）"""
        return bleach.clean(value, tags=[], strip=True)

    def validate_name(self, value):
        """名前のサニタイズ"""
        return bleach.clean(value, tags=[], strip=True)
    
    def validate_email(self, value):
        """メールアドレスのサニタイズ"""
        return bleach.clean(value, tags=[], strip=True)

class PostListSerializer(serializers.ModelSerializer):
    """記事一覧用シリアライザー"""
    author = serializers.ReadOnlyField(source='author.username')
    
    class Meta:
        model = Post
        fields = ['id', 'title', 'slug', 'author', 'status', 'publish', 'created']
        read_only_fields = ['slug', 'created']
    

class PostDetailSerializer(serializers.ModelSerializer):
    """記事詳細用シリアライザー"""
    author = AuthorSerializer(read_only=True)
    comments = CommentSerializer(many=True, read_only=True)
    
    class Meta:
        model = Post
        fields = [
            'id', 'title', 'slug', 'author', 'content', 'status',
            'publish', 'created', 'updated', 'comments'
        ]
        read_only_fields = ['slug', 'created', 'updated']

    def validate_title(self, value):
        """タイトルのサニタイズ（HTMLタグは不要）"""
        return bleach.clean(value, tags=[], strip=True)

    def validate_content(self, value):
        """
        投稿内容のサニタイズ
        Next.jsのServerMarkdownRendererと同じ設定で統一
        """
        # Next.jsと完全に同じ許可タグ
        allowed_tags = [
            'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
            'p', 'br', 'strong', 'em', 'u', 's', 'del',
            'ul', 'ol', 'li',
            'blockquote', 'code', 'pre', 'span',
            'a', 'img',
            'table', 'thead', 'tbody', 'tr', 'th', 'td',
            'hr'
        ]
        
        # Next.jsと完全に同じ許可属性
        allowed_attributes = {
            'a': ['href','title', 'target', 'rel'],
            'img': ['src', 'alt', 'title'],
            'code': ['class'],  # highlight.js用
            'span': ['class'],  # highlight.js用
            'pre': ['class'],
        }
        
        # Next.jsと完全に同じ許可プロトコル
        allowed_protocols = ['http', 'https', 'mailto', 'tel']
        
        return bleach.clean(
            value,
            tags=allowed_tags,
            attributes=allowed_attributes,
            protocols=allowed_protocols,
            strip=True,  # 許可されていないタグは完全に除去
            strip_comments=True  # HTMLコメントも除去
        )
    

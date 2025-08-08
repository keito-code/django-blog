from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Post, Comment


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
    

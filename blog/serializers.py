from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Post, Category

User = get_user_model()


class CategorySerializer(serializers.ModelSerializer):
    """カテゴリーシリアライザー"""
    class Meta:
        model = Category
        fields = ['id', 'name', 'slug']
        read_only_fields = ['slug']

class PostListSerializer(serializers.ModelSerializer):
    """記事一覧用"""
    author_name = serializers.SerializerMethodField()
    category = CategorySerializer(read_only=True)
    
    class Meta:
        model = Post
        fields = [
            'id', 'title', 'slug', 'author_name', 'category',
            'status', 'created_at', 'updated_at'
        ]
        read_only_fields = ['slug']

    def get_author_name(self, obj):
        # プライバシー保護のため匿名化
        return f"Author{obj.author.id}"
    
class PostDetailSerializer(serializers.ModelSerializer):
    """記事詳細用"""
    author_name = serializers.SerializerMethodField()
    category = CategorySerializer(read_only=True)
    
    class Meta:
        model = Post
        fields = [
            'id', 'title', 'slug', 'author_name', 'category',
            'content', 'status','created_at', 'updated_at'
        ]
        read_only_fields = ['slug']

    def get_author_name(self, obj):
        return f"Author{obj.author.id}"

class PostCreateSerializer(serializers.Serializer):
    """記事作成用（認証必要）"""
    title = serializers.CharField(max_length=200)
    content = serializers.CharField()
    category_id = serializers.IntegerField(required=False, allow_null=True)
    status = serializers.ChoiceField(
        choices=['draft', 'published'],
        default='draft'
    )

    def validate_title(self, value):
        if len(value) < 3:
            raise serializers.ValidationError(
                "タイトルは3文字以上必要です"
            )
        return value

    def validate(self, data):
        if data.get('title') == data.get('content'):
            raise serializers.ValidationError(
                "タイトルと本文に同じ内容は設定できません"
            )
        return data

class PostUpdateSerializer(serializers.Serializer):
    """記事更新用（認証必要）"""
    title = serializers.CharField(max_length=200, required=False)
    content = serializers.CharField(required=False)
    category_id = serializers.IntegerField(required=False, allow_null=True)
    status = serializers.ChoiceField(
        choices=['draft', 'published'],
        required=False
    )

    def validate_title(self, value):
        if value and len(value) < 3:
            raise serializers.ValidationError(
                "タイトルは3文字以上必要です"
            )
        return value
    
    def validate(self, data):
        if 'title' in data and 'content' in data:
            if data['title'] == data['content']:
                raise serializers.ValidationError(
                    "タイトルと本文に同じ内容は設定できません"
                )
        return data

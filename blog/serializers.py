from rest_framework import serializers
from django.contrib.auth import get_user_model
from drf_spectacular.utils import extend_schema_field
from .models import Post, Category
from .utils.sanitizers import ContentSanitizer

User = get_user_model()


class CategorySerializer(serializers.ModelSerializer):
    post_count = serializers.SerializerMethodField()  # 動的計算に変更

    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'post_count']
        read_only_fields = ['slug', 'post_count']

    @extend_schema_field(serializers.IntegerField())
    def get_post_count(self, obj) -> int:
        return obj.posts.filter(status='published').count()

class PostListSerializer(serializers.ModelSerializer):
    author_name = serializers.SerializerMethodField()
    category = CategorySerializer(read_only=True)
    
    class Meta:
        model = Post
        fields = [
            'id', 'title', 'slug', 'author_name', 'category',
            'status', 'created_at', 'updated_at'
        ]
        read_only_fields = ['slug']

    @extend_schema_field(serializers.CharField())
    def get_author_name(self, obj) -> str:
        """プライバシー保護のため匿名化"""
        return f"Author{obj.author.id}"
    
class PostDetailSerializer(serializers.ModelSerializer):
    author_name = serializers.SerializerMethodField()
    category = CategorySerializer(read_only=True)
    
    class Meta:
        model = Post
        fields = [
            'id', 'title', 'slug', 'author_name', 'category',
            'content', 'status','created_at', 'updated_at'
        ]
        read_only_fields = ['slug']

    @extend_schema_field(serializers.CharField())
    def get_author_name(self, obj) -> str:
        return f"Author{obj.author.id}"

class PostCreateSerializer(serializers.ModelSerializer):
    category_id = serializers.IntegerField(required=False, allow_null=True)

    class Meta:
        model = Post
        fields = ['title', 'content', 'status', 'category_id']
        
    def validate_title(self, value):
        sanitized_title = ContentSanitizer.sanitize_text(value)

        if len(sanitized_title) < 3:
            raise serializers.ValidationError("タイトルは3文字以上必要です")
        return sanitized_title

    def validate_content(self, value):
        return ContentSanitizer.sanitize_content(value)

    def validate(self, data):
        if data.get('title') == data.get('content'):
            raise serializers.ValidationError("タイトルと本文に同じ内容は設定できません")
        return data

    def create(self, validated_data):
        category_id = validated_data.pop('category_id', None)
        if category_id:
            validated_data['category_id'] = category_id
        return super().create(validated_data)

class PostUpdateSerializer(serializers.ModelSerializer):
    category_id = serializers.IntegerField(required=False, allow_null=True)

    class Meta:
        model = Post
        fields = ['title', 'content', 'status', 'category_id']
        extra_kwargs = {
            'title': {'required': False},
            'content': {'required': False},
            'status': {'required': False},
        }

    def validate_title(self, value):
        if value:
            sanitized_title = ContentSanitizer.sanitize_text(value)
            if len(sanitized_title) < 3:
                raise serializers.ValidationError("タイトルは3文字以上必要です")
            
            return sanitized_title
        return value

    def validate_content(self, value):
        if value:
            return ContentSanitizer.sanitize_content(value)
        return value
    
    def validate(self, data):
        if 'title' in data and 'content' in data:
            if data['title'] == data['content']:
                raise serializers.ValidationError("タイトルと本文に同じ内容は設定できません")
        return data

# ========================================
# JSendレスポンス用Serializer
# ========================================

class PaginationSerializer(serializers.Serializer):
    count = serializers.IntegerField(read_only=True)
    page = serializers.IntegerField(read_only=True)
    page_size = serializers.IntegerField(read_only=True)
    total_pages = serializers.IntegerField(read_only=True)
    next = serializers.CharField(allow_null=True, read_only=True)
    previous = serializers.CharField(allow_null=True, read_only=True)

class PostListDataSerializer(serializers.Serializer):
    posts = PostListSerializer(many=True, read_only=True)
    pagination = PaginationSerializer(read_only=True)

class PostListResponseSerializer(serializers.Serializer):
    status = serializers.CharField(default='success', read_only=True)
    data = PostListDataSerializer(read_only=True)

class PostDetailDataSerializer(serializers.Serializer):
    post = PostDetailSerializer(read_only=True)

class PostDetailResponseSerializer(serializers.Serializer):
    status = serializers.CharField(default='success', read_only=True)
    data = PostDetailDataSerializer(read_only=True)

class PostCreateResponseSerializer(serializers.Serializer):
    status = serializers.CharField(default='success', read_only=True)
    data = PostDetailDataSerializer(read_only=True)

class PostUpdateResponseSerializer(serializers.Serializer):
    status = serializers.CharField(default='success', read_only=True)
    data = PostDetailDataSerializer(read_only=True)

class PostDeleteResponseSerializer(serializers.Serializer):
    status = serializers.CharField(default='success', read_only=True)
    data = serializers.JSONField(default=None, allow_null=True, read_only=True)

class CategoryListDataSerializer(serializers.Serializer):
    categories = CategorySerializer(many=True, read_only=True)

class CategoryListResponseSerializer(serializers.Serializer):
    status = serializers.CharField(default='success', read_only=True)
    data = CategoryListDataSerializer(read_only=True)

class CategoryDetailDataSerializer(serializers.Serializer):
    category = CategorySerializer(read_only=True)

class CategoryDetailResponseSerializer(serializers.Serializer):
    status = serializers.CharField(default='success', read_only=True)
    data = CategoryDetailDataSerializer(read_only=True)

class CategoryCreateResponseSerializer(serializers.Serializer):
    status = serializers.CharField(default='success', read_only=True)
    data = CategoryDetailDataSerializer(read_only=True)

class CategoryUpdateResponseSerializer(serializers.Serializer):
    status = serializers.CharField(default='success', read_only=True)
    data = CategoryDetailDataSerializer(read_only=True)

class CategoryDeleteResponseSerializer(serializers.Serializer):
    status = serializers.CharField(default='success', read_only=True)
    data = serializers.JSONField(default=None, allow_null=True, read_only=True)

class CategoryPostsResponseSerializer(serializers.Serializer):
    status = serializers.CharField(default='success', read_only=True)
    data = PostListDataSerializer(read_only=True)

class UserPostListResponseSerializer(serializers.Serializer):
    """ユーザーの投稿一覧レスポンス用Serializer"""
    status = serializers.CharField(default='success', read_only=True)
    data = PostListDataSerializer(read_only=True)
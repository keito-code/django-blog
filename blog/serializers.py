from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Post, Category
from .utils.sanitizers import ContentSanitizer

User = get_user_model()


class CategorySerializer(serializers.ModelSerializer):
    post_count = serializers.SerializerMethodField()  # 動的計算に変更

    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'post_count']
        read_only_fields = ['slug', 'post_count']

    def get_post_count(self, obj):
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

    def get_author_name(self, obj):
        # プライバシー保護のため匿名化
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

    def get_author_name(self, obj):
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
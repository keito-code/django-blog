"""
- APIClientを使った実際のHTTPレスポンス形式のテスト
- JSend形式とCamelCase変換の検証
"""

import pytest
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from blog.models import Post, Category

User = get_user_model()


def to_camel_case(data):
    """
    Snake_case → camelCase変換
    
    APIClientのresponse.dataは内部のsnake_case形式だが、
    実際のHTTPレスポンスはCamelCase形式なので変換する。
    """
    if isinstance(data, dict):
        return {
            snake_to_camel(key): to_camel_case(value) 
            for key, value in data.items()
        }
    elif isinstance(data, list):
        return [to_camel_case(item) for item in data]
    return data


def snake_to_camel(snake_str):
    """snake_case文字列をcamelCaseに変換"""
    components = snake_str.split('_')
    return components[0] + ''.join(x.title() for x in components[1:])

    
@pytest.fixture
def api_client():
    """統合テスト用のAPIClient"""
    return APIClient()


@pytest.fixture
def user(db):
    """テスト用ユーザー"""
    return User.objects.create_user(
        email='test@example.com',
        username='testuser',
        password='testpass123',
    )


@pytest.fixture
def other_user(db):
    """別のテスト用ユーザー（権限テスト用）"""
    return User.objects.create_user(
        email='other@example.com',
        username='otheruser',
        password='testpass123',
    )


@pytest.fixture
def admin_user(db):
    """管理者ユーザー（カテゴリ管理用）"""
    return User.objects.create_superuser(
        email='admin@example.com',
        username='admin',
        password='adminpass123',
    )


@pytest.fixture
def authenticated_client(api_client, user):
    """認証済みクライアント"""
    api_client.force_authenticate(user=user)
    # テストでユーザーを参照できるようにする
    api_client.user = user
    return api_client


@pytest.fixture
def admin_client(api_client, admin_user):
    """管理者として認証済みのクライアント"""
    api_client.force_authenticate(user=admin_user)
    api_client.user = admin_user
    return api_client


@pytest.fixture
def category(db):
    """テスト用カテゴリ(slugは自動生成に任せる)"""
    return Category.objects.create(name='Technology')


@pytest.fixture
def post(db, user, category):
    """テスト用の公開済み投稿"""
    return Post.objects.create(
        title='Test Post',
        content='This is test content.',
        author=user,
        category=category,
        status='published'
    )


@pytest.fixture
def draft_post(db, user, category):
    """テスト用の下書き投稿"""
    return Post.objects.create(
        title='Draft Post',
        content='This is draft content.',
        author=user,
        category=category,
        status='draft'
    )


@pytest.fixture
def create_post_data():
    """投稿作成用のテストデータ"""
    return {
        'title': 'New Post Title',
        'content': 'New post content here.',
        'status': 'draft',
        'category_id': None  # 任意フィールドはNoneにしておく
    }


@pytest.fixture
def update_post_data():
    """投稿更新用のテストデータ（部分更新）"""
    return {
        'title': 'Updated Post Title'
    }

@pytest.fixture
def category_data():
    """カテゴリ作成用のテストデータ"""
    return {
        'name': 'New Category'
    }
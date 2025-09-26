import pytest
from rest_framework.test import APIRequestFactory, force_authenticate
from rest_framework import status
from django.contrib.auth import get_user_model
from blog.api_views import PostViewSet, UserPostListView, CategoryViewSet
from blog.models import Post, Category

User = get_user_model()


@pytest.mark.django_db
class TestPostViewSet:
    """PostViewSetのユニットテスト"""
    
    @pytest.fixture
    def factory(self):
        return APIRequestFactory()
    
    @pytest.fixture
    def user(self):
        return User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass'
        )
    
    @pytest.fixture
    def other_user(self):
        return User.objects.create_user(
            username='other',
            email='other@example.com',
            password='testpass'
        )
        
    def test_create_post_success(self, factory, user):
        """正常な投稿作成"""
        view = PostViewSet.as_view({'post': 'create'})
        data = {
            'title': 'Test Title',
            'content': 'Test Content',
            'status': 'draft'
        }
        request = factory.post('/v1/posts/', data, format='json')
        force_authenticate(request, user=user)
        
        response = view(request)
        
        assert response.status_code == status.HTTP_201_CREATED
        assert Post.objects.filter(title='Test Title').exists()
        post = Post.objects.get(title='Test Title')
        assert post.author == user
        assert post.slug  # 自動生成されている
        assert post.category is None
        
    def test_update_post_by_author(self, factory, user):
        """作者による投稿更新"""
        post = Post.objects.create(
            title='Original',
            content='Original Content',
            author=user
        )
        
        view = PostViewSet.as_view({'patch': 'partial_update'})
        data = {'title': 'Updated Title'}
        request = factory.patch(f'/v1/posts/{post.slug}/', data, format='json')
        force_authenticate(request, user=user)
        
        response = view(request, slug=post.slug)
        
        assert response.status_code == status.HTTP_200_OK
        post.refresh_from_db()
        assert post.title == 'Updated Title'
    
    def test_update_post_by_other_user(self, factory, user, other_user):
        """他人の投稿は更新不可(404)"""
        post = Post.objects.create(
            title='Original',
            content='Original Content',
            author=user,
            status='draft'
        )
        
        view = PostViewSet.as_view({'patch': 'partial_update'})
        data = {'title': 'Hacked'}
        request = factory.patch(f'/v1/posts/{post.slug}/', data, format='json')
        force_authenticate(request, user=other_user)
        
        response = view(request, slug=post.slug)

         # 他人の下書きはQuerySetでフィルタされるため404
        assert response.status_code == status.HTTP_404_NOT_FOUND
        post.refresh_from_db()
        assert post.title == 'Original'
        
    def test_delete_post_by_author(self, factory, user):
        """作者による投稿削除"""
        post = Post.objects.create(
            title='To Delete',
            content='Content',
            author=user
        )
        
        view = PostViewSet.as_view({'delete': 'destroy'})
        request = factory.delete(f'/v1/posts/{post.slug}/')
        force_authenticate(request, user=user)
        
        response = view(request, slug=post.slug)
        
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Post.objects.filter(id=post.id).exists()
    
    def test_delete_post_by_other_user(self, factory, user, other_user):
        """他人の下書きは削除不可(404)"""
        post = Post.objects.create(
            title='Protected',
            content='Content',
            author=user,
            status='draft'
        )
        
        view = PostViewSet.as_view({'delete': 'destroy'})
        request = factory.delete(f'/v1/posts/{post.slug}/')
        force_authenticate(request, user=other_user)
        
        response = view(request, slug=post.slug)

        # 他人の下書きはQuerySetでフィルタされるため404
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert Post.objects.filter(id=post.id).exists()

    def test_update_published_post_by_other_user(self, factory, user, other_user):
        """他人の公開記事も更新不可（403）"""
        post = Post.objects.create(
            title='Published Post',
            content='Content',
            author=user,
            status='published'  # 公開記事
        )
        
        view = PostViewSet.as_view({'patch': 'partial_update'})
        data = {'title': 'Hacked'}
        request = factory.patch(f'/v1/posts/{post.slug}/', data, format='json')
        force_authenticate(request, user=other_user)
        
        response = view(request, slug=post.slug)
        
        # 公開記事は見えるが、IsAuthorOrReadOnlyで403
        assert response.status_code == status.HTTP_403_FORBIDDEN
        post.refresh_from_db()
        assert post.title == 'Published Post'
    
    def test_delete_published_post_by_other_user(self, factory, user, other_user):
        """他人の公開記事も削除不可（403）"""
        post = Post.objects.create(
            title='Published Protected',
            content='Content',
            author=user,
            status='published'  # 公開記事
        )
        
        view = PostViewSet.as_view({'delete': 'destroy'})
        request = factory.delete(f'/v1/posts/{post.slug}/')
        force_authenticate(request, user=other_user)
        
        response = view(request, slug=post.slug)
        
        # 公開記事は見えるが、IsAuthorOrReadOnlyで403
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert Post.objects.filter(id=post.id).exists()
        
    def test_view_draft_by_author(self, factory, user):
        """下書きは作者のみ閲覧可能"""
        post = Post.objects.create(
            title='Draft',
            content='Draft Content',
            author=user,
            status='draft'
        )
        
        view = PostViewSet.as_view({'get': 'retrieve'})
        request = factory.get(f'/v1/posts/{post.slug}/')
        force_authenticate(request, user=user)
        
        response = view(request, slug=post.slug)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['title'] == 'Draft'
    
    def test_view_draft_by_other_user(self, factory, user, other_user):
        """他人の下書きは閲覧不可"""
        post = Post.objects.create(
            title='Secret Draft',
            content='Secret Content',
            author=user,
            status='draft'
        )
        
        view = PostViewSet.as_view({'get': 'retrieve'})
        request = factory.get(f'/v1/posts/{post.slug}/')
        force_authenticate(request, user=other_user)
        
        response = view(request, slug=post.slug)
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    def test_view_draft_anonymous(self, factory, user):
        """未認証ユーザーは下書き閲覧不可"""
        post = Post.objects.create(
            title='Draft',
            content='Draft Content',
            author=user,
            status='draft'
        )
        
        view = PostViewSet.as_view({'get': 'retrieve'})
        request = factory.get(f'/v1/posts/{post.slug}/')
        # 認証なし
        
        response = view(request, slug=post.slug)
        
        # 404として扱う（存在しないかのように）
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    def test_list_posts_filtered_by_status(self, factory, user):
        """投稿一覧は適切にフィルタリング"""
        # 自分の下書き
        Post.objects.create(
            title='My Draft',
            content='Content',
            author=user,
            status='draft'
        )
        # 自分の公開記事
        Post.objects.create(
            title='My Published',
            content='Content',
            author=user,
            status='published'
        )
        # 他人の下書き（見えないはず）
        other = User.objects.create_user(username='other2', email='other2@example.com')
        Post.objects.create(
            title='Other Draft',
            content='Content',
            author=other,
            status='draft'
        )
        
        view = PostViewSet.as_view({'get': 'list'})
        request = factory.get('/v1/posts/')
        force_authenticate(request, user=user)
        
        response = view(request)
        
        assert response.status_code == status.HTTP_200_OK
        titles = [post['title'] for post in response.data['results']]
        assert 'My Draft' in titles
        assert 'My Published' in titles
        assert 'Other Draft' not in titles  # 他人の下書きは見えない

    def test_publish_draft_post(self, factory, user):
        """下書きを公開(PATCHでstatus変更)"""
        post = Post.objects.create(
            title='Draft to Publish',
            content='Content',
            author=user,
            status='draft'
        )
        
        view = PostViewSet.as_view({'patch': 'partial_update'})
        data = {'status': 'published'}
        request = factory.patch(f'/v1/posts/{post.slug}/', data, format='json')
        force_authenticate(request, user=user)
        
        response = view(request, slug=post.slug)
        
        assert response.status_code == status.HTTP_200_OK
        post.refresh_from_db()
        assert post.status == 'published'
    
    def test_publish_already_published(self, factory, user):
        """既に公開済みの投稿を公開してもエラーにならない（無視される）"""
        post = Post.objects.create(
            title='Already Published',
            content='Content',
            author=user,
            status='published'
        )
        
        view = PostViewSet.as_view({'patch': 'partial_update'})
        data = {'status': 'published', 'title': 'Title Updated'}
        request = factory.patch(f'/v1/posts/{post.slug}/', data, format='json')
        force_authenticate(request, user=user)
        
        response = view(request, slug=post.slug)

        # statusは無視されて、titleのみ更新される
        assert response.status_code == status.HTTP_200_OK
        post.refresh_from_db()
        assert post.status == 'published'  # 変更なし
        assert post.title == 'Title Updated'  # titleは更新される
        
    def test_publish_other_users_post(self, factory, user, other_user):
        """他人の投稿は公開できない"""
        post = Post.objects.create(
            title='Others Draft',
            content='Content',
            author=other_user,
            status='draft'
        )

        view = PostViewSet.as_view({'patch': 'partial_update'})
        data = {'status': 'published'}
        request = factory.patch(f'/v1/posts/{post.slug}/', data, format='json')
        force_authenticate(request, user=user)
        
        response = view(request, slug=post.slug)
        
        assert response.status_code == status.HTTP_404_NOT_FOUND  # QuerySetでフィルタされるため404
    
    def test_unpublish_published_post(self, factory, user):
        """公開記事を下書きに戻す(PATCHでstatus変更)"""
        post = Post.objects.create(
            title='Published to Draft',
            content='Content',
            author=user,
            status='published'
        )

        view = PostViewSet.as_view({'patch': 'partial_update'})
        data = {'status': 'draft'}
        request = factory.patch(f'/v1/posts/{post.slug}/', data, format='json')
        force_authenticate(request, user=user)
        
        response = view(request, slug=post.slug)
        
        assert response.status_code == status.HTTP_200_OK
        post.refresh_from_db()
        assert post.status == 'draft'
    
    def test_unpublish_already_draft(self, factory, user):
        """既に下書きの投稿を下書きにしてもエラーにならない（無視される）"""
        post = Post.objects.create(
            title='Already Draft',
            content='Content',
            author=user,
            status='draft'
        )

        view = PostViewSet.as_view({'patch': 'partial_update'})
        data = {'status': 'draft', 'content': 'Updated Content'}
        request = factory.patch(f'/v1/posts/{post.slug}/', data, format='json')
        force_authenticate(request, user=user)
        
        response = view(request, slug=post.slug)

        # statusは無視されて、contentのみ更新される
        assert response.status_code == status.HTTP_200_OK
        post.refresh_from_db()
        assert post.status == 'draft'  # 変更なし
        assert post.content == 'Updated Content'  # contentは更新される

    def test_my_posts_endpoint(self, factory, user):
        """/v1/users/me/posts/エンドポイントで自分の投稿を取得"""
        
        # 自分の投稿
        Post.objects.create(title='My Post 1', content='Content', author=user, status='published')
        Post.objects.create(title='My Post 2', content='Content', author=user, status='draft')
        
        # 他人の投稿
        other = User.objects.create_user(username='other3', email='other3@example.com')
        Post.objects.create(title='Other Post', content='Content', author=other, status='published')
        
        view = UserPostListView.as_view()
        request = factory.get('/v1/users/me/posts/')
        force_authenticate(request, user=user)
        
        response = view(request)
        
        assert response.status_code == status.HTTP_200_OK
        titles = [post['title'] for post in response.data['results']]
        assert 'My Post 1' in titles
        assert 'My Post 2' in titles
        assert 'Other Post' not in titles
        
@pytest.mark.django_db
class TestCategoryViewSet:
    """CategoryViewSetのユニットテスト"""
    
    @pytest.fixture
    def factory(self):
        return APIRequestFactory()
    
    @pytest.fixture
    def admin_user(self):
        return User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='adminpass'
        )
    
    @pytest.fixture
    def normal_user(self):
        return User.objects.create_user(
            username='user',
            email='user@example.com',
            password='userpass'
        )
    
    def test_create_category_as_admin(self, factory, admin_user):
        """管理者はカテゴリー作成可能"""
        view = CategoryViewSet.as_view({'post': 'create'})
        data = {'name': 'New Category'}
        request = factory.post('/v1/categories/', data, format='json')
        force_authenticate(request, user=admin_user)
        
        response = view(request)
        
        assert response.status_code == status.HTTP_201_CREATED
        assert Category.objects.filter(name='New Category').exists()
        category = Category.objects.get(name='New Category')
        assert category.slug  # 自動生成
    
    def test_create_category_as_normal_user(self, factory, normal_user):
        """一般ユーザーはカテゴリー作成不可"""
        view = CategoryViewSet.as_view({'post': 'create'})
        data = {'name': 'Forbidden Category'}
        request = factory.post('/v1/categories/', data, format='json')
        force_authenticate(request, user=normal_user)
        
        response = view(request)
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert not Category.objects.filter(name='Forbidden Category').exists()
    
    def test_update_category_as_admin(self, factory, admin_user):
        """管理者はカテゴリー更新可能"""
        category = Category.objects.create(name='Old Name')
        
        view = CategoryViewSet.as_view({'patch': 'partial_update'})
        data = {'name': 'New Name'}
        request = factory.patch(f'/v1/categories/{category.slug}/', data, format='json')
        force_authenticate(request, user=admin_user)
        
        response = view(request, slug=category.slug)
        
        assert response.status_code == status.HTTP_200_OK
        category.refresh_from_db()
        assert category.name == 'New Name'
        # slugは変更されない
        assert category.slug == 'old-name'
    
    def test_delete_category_as_admin(self, factory, admin_user):
        """管理者はカテゴリー削除可能"""
        category = Category.objects.create(name='To Delete')
        
        view = CategoryViewSet.as_view({'delete': 'destroy'})
        request = factory.delete(f'/v1/categories/{category.slug}/')
        force_authenticate(request, user=admin_user)
        
        response = view(request, slug=category.slug)
        
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Category.objects.filter(id=category.id).exists()

    def test_list_categories_anonymous(self, factory):
        """未認証ユーザーでもカテゴリー一覧は閲覧可能"""
        Category.objects.create(name='Tech')
        Category.objects.create(name='Life')
        
        view = CategoryViewSet.as_view({'get': 'list'})
        request = factory.get('/v1/categories/')
        # 認証なし
        
        response = view(request)
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 2
    
    def test_category_posts_action(self, factory, normal_user):
        """カテゴリーに属する投稿一覧を取得"""
        category = Category.objects.create(name='Tech')
        user = User.objects.create_user(username='author', email='author@example.com')
        
        # カテゴリーに属する公開記事
        Post.objects.create(
            title='Tech Post 1',
            content='Content',
            author=user,
            category=category,
            status='published'
        )
        Post.objects.create(
            title='Tech Post 2',
            content='Content',
            author=user,
            category=category,
            status='published'
        )
        # カテゴリーに属する下書き（表示されないはず）
        Post.objects.create(
            title='Tech Draft',
            content='Content',
            author=user,
            category=category,
            status='draft'
        )
        
        view = CategoryViewSet.as_view({'get': 'posts'})
        request = factory.get(f'/v1/categories/{category.slug}/posts/')
        force_authenticate(request, user=normal_user)
        
        response = view(request, slug=category.slug)
        
        assert response.status_code == status.HTTP_200_OK
        titles = [post['title'] for post in response.data['results']]
        assert 'Tech Post 1' in titles
        assert 'Tech Post 2' in titles
        assert 'Tech Draft' not in titles  # 下書きは表示されない
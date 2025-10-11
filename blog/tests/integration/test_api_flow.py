
@pytest.mark.django_db
class TestBlogAPIFlow:
    """ブログAPI全体フローの統合テスト"""
    
    def test_admin_category_management(self, api_client, admin_user):
        """管理者によるカテゴリー管理フロー"""
        api_client.force_authenticate(admin_user)
        
        # カテゴリー作成
        response = api_client.post('/api/blog/categories/', {
            'name': 'Tech'
        })
        assert response.status_code == 201
        category_slug = response.data['data']['category']['slug']
        
        # 一般ユーザーは作成不可
        normal_user = User.objects.create_user('normal', 'n@test.com')
        api_client.force_authenticate(normal_user)
        response = api_client.post('/api/blog/categories/', {
            'name': 'Hack'
        })
        assert response.status_code == 403
    
    def test_post_lifecycle_with_auto_slug(self, api_client, user):
        """投稿のライフサイクル（slug自動生成）"""
        api_client.force_authenticate(user)
        
        # 投稿作成（slugなし）
        response = api_client.post('/api/blog/posts/', {
            'title': '日本語タイトル',
            'content': 'コンテンツ'
        })
        assert response.status_code == 201
        post_slug = response.data['data']['post']['slug']
        assert post_slug  # 自動生成されている
        
        # slug手動設定は無視される
        response = api_client.post('/api/blog/posts/', {
            'title': 'Another Post',
            'content': 'Content',
            'slug': 'manual-slug'  # 無視される
        })
        assert response.data['data']['post']['slug'] != 'manual-slug'
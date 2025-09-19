
@pytest.mark.django_db
class TestBlogAPIFlow:
    """ブログAPI全体フローの統合テスト"""

    def test_admin_category_management(self, api_client, admin_user):
        """管理者によるカテゴリー管理フロー"""
        api_client.force_authenticate(admin_user)
        
        # カテゴリー作成
        response = api_client.post('/api/v1/blog/categories/', {  
            'name': 'Tech'
        })
        assert response.status_code == 201
        category_slug = response.data['slug']  
        
        # 一般ユーザーは作成不可
        normal_user = User.objects.create_user('normal', 'n@test.com')
        api_client.force_authenticate(normal_user)
        response = api_client.post('/api/v1/blog/categories/', {  
            'name': 'Hack'
        })
        assert response.status_code == 403
    

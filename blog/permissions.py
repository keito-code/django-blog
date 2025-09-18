from rest_framework import permissions

class IsAuthorOrReadOnly(permissions.BasePermission):
    """
    新規作成は認証済みのみ可能
    作者のみ編集・削除可能
    下書きは作者のみ閲覧可能
    """

    def has_permission(self, request, view):
        # 記事一覧の閲覧(GET)は誰でも許可
        if request.method in permissions.SAFE_METHODS:
            return True

        # 新規作成(POST)は、認証必須
        return request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        # 読み取り権限
        if request.method in permissions.SAFE_METHODS:
            # 公開記事は誰でも閲覧可能
            if obj.status == 'published':
                return True
            # 下書きは作者のみ
            return obj.author == request.user
        
        # 書き込み権限は作者のみ
        return obj.author == request.user
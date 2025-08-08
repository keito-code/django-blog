from rest_framework import permissions


class IsAuthorOrReadOnly(permissions.BasePermission):
    """
    カスタムパーミッション：著者のみ編集・削除可能
    - 読み取り操作は全員に許可
    - 作成・更新・削除は記事の著者のみに許可
    """
    
    def has_object_permission(self, request, view, obj):
        # 読み取り権限はすべてのリクエストに許可
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # 書き込み権限は記事の著者のみ
        return obj.author == request.user
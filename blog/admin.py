from django.contrib import admin
from .models import Post, Comment, CSPViolation


admin.site.site_url = None # 「サイトを表示」リンクを非表示


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ('title', 'slug', 'author', 'publish', 'status')
    list_filter = ('status', 'created', 'publish', 'author')
    search_fields = ('title', 'content')
    prepopulated_fields = {'slug': ('title',)}
    raw_id_fields = ('author',)
    date_hierarchy = 'publish'
    ordering = ('status', 'publish')
    view_on_site = False  # 「サイト上で表示」ボタンを非表示
    list_per_page = 50  # ページネーション設定
    list_editable = ('status',)  # 一覧で直接編集
    save_on_top = True  # 上部にも保存ボタン


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'post', 'created', 'active')
    list_filter = ('active', 'created', 'updated')
    search_fields = ('name', 'email', 'body')


def mark_violations_as_resolved(modeladmin, request, queryset):
    """選択されたCSP違反を一括で対応済みにする"""
    updated = queryset.update(is_resolved=True)
    modeladmin.message_user(request, f'{updated}件のCSP違反を対応済みにしました。')
mark_violations_as_resolved.short_description = '選択されたCSP違反を対応済みにする'


@admin.register(CSPViolation)
class CSPViolationAdmin(admin.ModelAdmin):
    list_display = ('directive', 'blocked_uri_short', 'document_uri_short', 'created', 'is_resolved')
    list_filter = ('directive', 'is_resolved', 'created')
    search_fields = ('blocked_uri', 'document_uri', 'source_file')
    readonly_fields = ('directive', 'blocked_uri', 'document_uri', 'line_number', 
                      'column_number', 'source_file', 'original_policy', 
                      'user_agent', 'ip_address', 'created')
    fields = (
        ('directive', 'is_resolved'),
        ('blocked_uri', 'document_uri'),
        ('line_number', 'column_number'),
        'source_file',
        'original_policy',
        ('user_agent', 'ip_address'),
        'created',
        'notes'
    )
    actions = [mark_violations_as_resolved]
    
    def blocked_uri_short(self, obj):
        """ブロックされたURIを短縮表示"""
        if obj.blocked_uri:
            return obj.blocked_uri[:50] + ('...' if len(obj.blocked_uri) > 50 else '')
        return '-'
    blocked_uri_short.short_description = 'ブロックされたURI'
    
    def document_uri_short(self, obj):
        """ドキュメントURIを短縮表示"""
        if obj.document_uri:
            return obj.document_uri[:50] + ('...' if len(obj.document_uri) > 50 else '')
        return '-'
    document_uri_short.short_description = 'ドキュメントURI'
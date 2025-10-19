from django.contrib import admin
from .models import Post, Category


admin.site.site_url = None  # 「サイトを表示」リンクを非表示


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'post_count', 'created_at')
    search_fields = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}  # 英語名の場合は自動生成
    ordering = ('name',)
    readonly_fields = ('post_count', 'created_at', 'updated_at')
    
    def post_count(self, obj):
        """カテゴリーに属する公開記事数を表示"""
        return obj.posts.filter(status='published').count()
    post_count.short_description = '公開記事数'


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ('title', 'slug', 'author', 'category', 'created_at', 'status')
    list_filter = ('status', 'category', 'created_at', 'updated_at', 'author')
    search_fields = ('title', 'content')
    prepopulated_fields = {'slug': ('title',)}
    raw_id_fields = ('author',)
    date_hierarchy = 'created_at'
    ordering = ('status', '-created_at')
    view_on_site = False  # 「サイト上で表示」ボタンを非表示
    list_per_page = 50  # ページネーション設定
    list_editable = ('status',)  # 一覧で直接編集
    save_on_top = True  # 上部にも保存ボタン
    autocomplete_fields = ['category']
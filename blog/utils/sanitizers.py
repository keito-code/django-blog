# blog/utils/sanitizers.py
import bleach
import re
from html import escape

class ContentSanitizer:
    
    @staticmethod
    def sanitize_text(text: str) -> str:
        """タイトル等のプレーンテキスト化"""
        if not text:
            return ''
        return bleach.clean(text, tags=[], strip=True).strip()[:200]
    
    @staticmethod
    def sanitize_content(text: str) -> str:
        """ブログコンテンツの保存用サニタイズ"""
        if not text:
            return ''
        
        # 危険なパターンを除去
        cleaned = re.sub(r'<script\b[^<]*(?:(?!</script>)<[^<]*)*</script>', '', text, flags=re.IGNORECASE)
        cleaned = re.sub(r'javascript:', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'on\w+\s*=', '', cleaned, flags=re.IGNORECASE)
        
        # 許可するタグ（Markdown変換後のHTML用）
        allowed_tags = [
            'p', 'br', 'strong', 'b', 'em', 'i', 'code', 'pre',
            'blockquote', 'ul', 'ol', 'li',
            'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
            'a', 'img', 'hr'
        ]
        
        return bleach.clean(
            cleaned,
            tags=allowed_tags,
            attributes={
                'a': ['href', 'title'],
                'img': ['src', 'alt'],
                'code': ['class']
            },
            protocols=['http', 'https', 'mailto'],
            strip=True
        )
    
    @staticmethod
    def sanitize_search_display(query: str) -> str:
        """検索クエリの表示用サニタイズ"""
        if not query:
            return ''
        return escape(query)  # HTMLエスケープのみ
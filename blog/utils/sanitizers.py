import bleach
import re
from html import escape

class ContentSanitizer:
    
    @staticmethod
    def sanitize_text(text: str) -> str:
        """HTMLタグを完全に除去（プレーンテキスト化）"""
        if not text:
            return ''
        
        # まずscriptとstyleタグを中身ごと削除
        text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
        
        # その後、残りのHTMLタグを除去
        cleaned = bleach.clean(text, tags=[], strip=True)
        
        # 余分な空白を整理
        cleaned = ' '.join(cleaned.split())
        
        return cleaned.strip()[:200]
    
    @staticmethod
    def sanitize_content(text: str) -> str:
        """ブログコンテンツの保存用サニタイズ"""
        if not text:
            return ''

        # まず危険なタグを中身ごと削除
        text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
        
        # イベントハンドラを除去
        text = re.sub(r'\s*on\w+\s*=\s*["\'][^"\']*["\']', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\s*on\w+\s*=\s*[^\s>]+', '', text, flags=re.IGNORECASE)
        
        # javascript: URLを除去
        text = re.sub(r'javascript:', '', text, flags=re.IGNORECASE)
        
        # 許可するタグ（Markdown変換後のHTML用）
        allowed_tags = [
            'p', 'br', 'strong', 'b', 'em', 'i', 'code', 'pre',
            'blockquote', 'ul', 'ol', 'li',
            'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
            'a', 'img', 'hr'
        ]

        allowed_attrs = {
            'a': ['href', 'title'],
            'img': ['src', 'alt'],
            'code': ['class'],
            'pre': ['class'],
        }
        
        return bleach.clean(
            text,
            tags=allowed_tags,
            attributes=allowed_attrs,
            protocols=['http', 'https', 'mailto'],
            strip=True
        )
        
    @staticmethod
    def sanitize_search_display(query: str) -> str:
        """検索クエリの表示用サニタイズ"""
        if not query:
            return ''
        return escape(query)  # HTMLエスケープのみ
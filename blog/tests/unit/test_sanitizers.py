import pytest
from blog.utils.sanitizers import ContentSanitizer


class TestContentSanitizer:
    """サニタイザーのユニットテスト"""
    
    def test_sanitize_text_removes_html_tags(self):
        """HTMLタグが完全に除去されることを確認"""
        input_text = '<script>alert("XSS")</script>Hello <b>World</b>'
        result = ContentSanitizer.sanitize_text(input_text)
        assert result == 'Hello World'
        assert '<' not in result
        assert '>' not in result
    
    def test_sanitize_text_with_empty_string(self):
        """空文字列の処理"""
        assert ContentSanitizer.sanitize_text('') == ''
        assert ContentSanitizer.sanitize_text(None) == ''
    
    def test_sanitize_content_removes_script_tags(self):
        """スクリプトタグが除去されることを確認"""
        input_content = 'Normal text <script>alert("XSS")</script> more text'
        result = ContentSanitizer.sanitize_content(input_content)
        assert '<script>' not in result
        assert 'alert' not in result
        assert 'Normal text' in result
        assert 'more text' in result
    
    def test_sanitize_content_removes_event_handlers(self):
        """イベントハンドラが除去されることを確認"""
        input_content = '<div onclick="alert(1)">Click me</div>'
        result = ContentSanitizer.sanitize_content(input_content)
        assert 'onclick' not in result
        assert 'alert' not in result
    
    def test_sanitize_content_allows_safe_tags(self):
        """安全なタグは保持されることを確認"""
        input_content = '<p>Paragraph</p><strong>Bold</strong><em>Italic</em>'
        result = ContentSanitizer.sanitize_content(input_content)
        assert '<p>' in result
        assert '<strong>' in result
        assert '<em>' in result
    
    def test_sanitize_content_with_markdown_code_blocks(self):
        """Markdownのコードブロックが保持されることを確認"""
        input_content = '<pre><code class="python">print("Hello")</code></pre>'
        result = ContentSanitizer.sanitize_content(input_content)
        assert '<pre>' in result
        assert '<code' in result
        assert 'print("Hello")' in result
    
    def test_sanitize_search_display(self):
        """検索クエリのHTMLエスケープ"""
        input_query = '<script>alert("XSS")</script>'
        result = ContentSanitizer.sanitize_search_display(input_query)
        assert '&lt;script&gt;' in result
        assert '<script>' not in result

    def test_sanitize_content_with_links(self):
        """リンクの処理を確認"""
        input_content = '<a href="http://example.com">Link</a>'
        result = ContentSanitizer.sanitize_content(input_content)
        assert '<a href="http://example.com">' in result
    
    def test_sanitize_content_with_javascript_url(self):
        """javascript:URLが除去されることを確認"""
        input_content = '<a href="javascript:alert(1)">Bad Link</a>'
        result = ContentSanitizer.sanitize_content(input_content)
        assert 'javascript:' not in result

    def test_sanitize_content_removes_disallowed_tags(self):
        """許可されていないタグの削除確認"""
        input_content = '<video src="movie.mp4"></video><p>Text</p>'
        result = ContentSanitizer.sanitize_content(input_content)
        assert '<video' not in result
        assert '<p>' in result

    def test_sanitize_content_with_img_tag(self):
        input_content = '<img src="image.png" alt="test" onerror="alert(1)">'
        result = ContentSanitizer.sanitize_content(input_content)
        assert '<img' in result
        assert 'src="image.png"' in result
        assert 'onerror' not in result

    def test_sanitize_text_truncates_long_input(self):
        input_text = 'a' * 500
        result = ContentSanitizer.sanitize_text(input_text)
        assert len(result) <= 200

from djangorestframework_camel_case.render import CamelCaseJSONRenderer


class JSendCamelCaseRenderer(CamelCaseJSONRenderer):
    """
    CamelCase変換とJSend形式を両立するレンダラー
    
    1. データをJSend形式でラップ
    2. その後、CamelCase変換を適用
    """
    
    def render(self, data, accepted_media_type=None, renderer_context=None):
        response = renderer_context.get('response') if renderer_context else None

        # response が無い場合は成功扱いしない（エラーの可能性があるため）
        if response is None:
            return super().render(data, accepted_media_type, renderer_context)
        
        # エラーステータス → custom_exception_handler の処理を尊重
        if response.status_code >= 400:
            return super().render(data, accepted_media_type, renderer_context)
        
        # すでにJSend形式の場合はそのまま
        if isinstance(data, dict) and 'status' in data:
            return super().render(data, accepted_media_type, renderer_context)
        
        # 成功レスポンスをJSend形式にラップ
        jsend_data = {
            'status': 'success',
            'data': data
        }
        
        # CamelCase変換を適用
        return super().render(jsend_data, accepted_media_type, renderer_context)
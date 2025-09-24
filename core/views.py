from django.http import JsonResponse

def csrf_failure(request, reason=""):
    """CSRF検証失敗時にJSON応答を返す"""
    if request.path.startswith(('/api/', '/v1/')):
        return JsonResponse({
            "status": "error",
            "message": "CSRF verification failed",
        }, status=403)

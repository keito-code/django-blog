from django.urls import path
from .views import (
    CSRFTokenView,
    LoginView,
    LogoutView,
    RegisterView,
    RefreshTokenView,
    VerifyTokenView,
)

urlpatterns = [
    path('csrf/', CSRFTokenView.as_view(), name='csrf'),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('register/', RegisterView.as_view(), name='register'),
    path('refresh/', RefreshTokenView.as_view(), name='refresh'),  # SimpleJWT標準
    path('verify/', VerifyTokenView.as_view(), name='verify'),
]


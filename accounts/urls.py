from django.urls import path
from . import views

urlpatterns = [
    path('csrf/', views.CSRFTokenView.as_view(), name='csrf'),
    path('login/', views.LoginView.as_view(), name='login'),
    path('register/', views.RegisterView.as_view(), name='register'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    path('refresh/', views.RefreshTokenView.as_view(), name='refresh'),
    path('user/', views.CurrentUserView.as_view(), name='user'),
    path('verify/', views.VerifyTokenView.as_view(), name='verify'), 
]
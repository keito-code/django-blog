from django.urls import path
from . import views_web


urlpatterns = [
    path('signup/', views_web.signup, name='signup'),
    path('login/', views_web.login_view, name='login'),
    path('logout/', views_web.logout_view, name='logout'),
]
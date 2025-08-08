from django.urls import path
from . import views

urlpatterns = [
    path('', views.post_list, name='post_list'),
    path('search/', views.post_search, name='post_search'),
    path('drafts/', views.post_draft_list, name='post_draft_list'),
    path('create/', views.post_create, name='post_create'),
    path('<int:pk>/edit/', views.post_update, name='post_update'),
    path('<int:pk>/delete/', views.post_delete, name='post_delete'),
    path('post/<slug:slug>/', views.post_detail, name='post_detail'),
    path('csp-report/', views.csp_report, name='csp_report'),
]
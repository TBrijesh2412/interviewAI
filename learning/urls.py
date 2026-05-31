from django.urls import path
from . import views

app_name = 'learning'

urlpatterns = [
    path('', views.learning_home, name='learning_home'),
    path('search/', views.learning_search, name='learning_search'),
    path('<slug:subject_slug>/', views.subject_detail, name='subject_detail'),
    path('<slug:subject_slug>/<slug:topic_slug>/<slug:article_slug>/', views.article_detail, name='article_detail'),
]

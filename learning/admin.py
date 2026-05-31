from django.contrib import admin
from .models import Subject, Topic, Article

@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'order', 'created_at')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name',)
    ordering = ('order', 'name')

@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    list_display = ('title', 'subject', 'slug', 'order', 'created_at')
    list_filter = ('subject',)
    prepopulated_fields = {'slug': ('title',)}
    search_fields = ('title', 'subject__name')
    ordering = ('subject', 'order')

@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = ('title', 'topic', 'slug', 'order', 'created_at', 'updated_at')
    list_filter = ('topic__subject', 'topic')
    prepopulated_fields = {'slug': ('title',)}
    search_fields = ('title', 'content')
    ordering = ('topic__subject', 'topic', 'order')

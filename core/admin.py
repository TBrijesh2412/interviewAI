from django.contrib import admin
from .models import UserProfile, InterviewReport, MockInterviewSession, QuestionAnswer


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ["user", "target_role", "experience_level", "updated_at"]
    search_fields = ["user__username", "target_role"]


@admin.register(InterviewReport)
class InterviewReportAdmin(admin.ModelAdmin):
    list_display = ["title", "user", "match_score", "created_at"]
    list_filter = ["match_score"]
    search_fields = ["title", "user__username"]
    ordering = ["-created_at"]


@admin.register(MockInterviewSession)
class MockInterviewSessionAdmin(admin.ModelAdmin):
    list_display = ["user", "report", "status", "overall_score", "created_at"]
    list_filter = ["status"]
    ordering = ["-created_at"]


@admin.register(QuestionAnswer)
class QuestionAnswerAdmin(admin.ModelAdmin):
    list_display = [
        "session",
        "question_index",
        "question_type",
        "ai_score",
        "created_at",
    ]
    ordering = ["session", "question_index"]

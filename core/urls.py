from django.urls import path
from . import views

urlpatterns = [
    path("", views.landing_page, name="landing"),
    # Auth
    path("register/", views.register_view, name="register"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    # Core
    path("dashboard/", views.dashboard, name="dashboard"),
    path("create-report/", views.create_report, name="create_report"),
    path("report/<int:report_id>/", views.report_detail, name="report_detail"),
    path("report/<int:report_id>/delete/", views.delete_report, name="delete_report"),
    path("report/<int:report_id>/notes/", views.save_notes, name="save_notes"),
    path("analyze-job-url/", views.analyze_job_url, name="analyze_job_url"),
    path(
        "download-resume/<int:report_id>/",
        views.download_resume,
        name="download_resume",
    ),
    # Profile & Analytics
    path("profile/", views.profile_view, name="profile"),
    path("analytics/", views.analytics_view, name="analytics"),
    # Technical Whiteboard
    path("whiteboard/", views.coding_whiteboard, name="whiteboard"),
    path("whiteboard/evaluate/", views.evaluate_code, name="evaluate_code"),
    path("job-matcher/", views.job_matcher, name="job_matcher"),
    path("star-coach/", views.star_coach_view, name="star_coach"),
    path("star-coach/message/", views.star_coach_message, name="star_coach_message"),
    path("star-coach/clear/", views.clear_star_coach, name="clear_star_coach"),
    # Mock Interview
    path(
        "mock/<int:report_id>/start/",
        views.mock_interview_start,
        name="mock_interview_start",
    ),
    path(
        "mock/session/<int:session_id>/answer/",
        views.mock_interview_answer,
        name="mock_interview_answer",
    ),
    path(
        "mock/session/<int:session_id>/complete/",
        views.mock_interview_complete,
        name="mock_interview_complete",
    ),
    # Mega Interview
    path("mega-interview/", views.mega_interview_setup, name="mega_interview_setup"),
    path("mega-interview/<int:session_id>/session/", views.mega_interview_interface, name="mega_interview_interface"),
    path("mega-interview/<int:session_id>/evaluate/", views.mega_interview_evaluate, name="mega_interview_evaluate"),
    path("mega-interview/<int:session_id>/result/", views.mega_interview_result, name="mega_interview_result"),
    path("mega-interview/run-code/", views.run_code, name="run_code"),
    path(
        "report/<int:report_id>/cover-letter/",
        views.cover_letter_view,
        name="cover_letter",
    ),
    path(
        "report/<int:report_id>/resume-builder/",
        views.resume_builder_view,
        name="resume_builder",
    ),
    path("roadmap/", views.career_roadmap, name="roadmap"),
    path("roadmap/selection/", views.roadmap_selection, name="roadmap_selection"),
    path(
        "roadmap/generate/", views.generate_roadmap_post, name="generate_roadmap_post"
    ),
    path("roadmap/refresh/", views.refresh_roadmap, name="refresh_roadmap"),
    # Health check - used by reload detector (must be instant, no ML)
    path("ping/", views.ping, name="ping"),
]

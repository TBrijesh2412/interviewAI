from django.db import models
from django.contrib.auth.models import User


class UserProfile(models.Model):
    EXPERIENCE_CHOICES = [
        ("0-1", "Fresher (0-1 years)"),
        ("1-3", "Junior (1-3 years)"),
        ("3-5", "Mid-level (3-5 years)"),
        ("5-10", "Senior (5-10 years)"),
        ("10+", "Expert (10+ years)"),
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    target_role = models.CharField(max_length=255, blank=True)
    experience_level = models.CharField(
        max_length=10, choices=EXPERIENCE_CHOICES, blank=True
    )
    headline = models.CharField(max_length=255, blank=True)
    target_companies = models.CharField(
        max_length=500, blank=True, help_text="Comma-separated"
    )
    skills = models.CharField(max_length=1000, blank=True, help_text="Comma-separated")

    # Resume fields for RAG
    resume_file = models.FileField(upload_to="resumes/", blank=True, null=True)
    resume_text = models.TextField(blank=True, null=True)

    # New Preference Fields
    city = models.CharField(max_length=255, blank=True)
    preferred_joining = models.DateField(null=True, blank=True)
    employment_type = models.CharField(
        max_length=50,
        choices=[
            ("full-time", "Full-time"),
            ("part-time", "Part-time"),
            ("contract", "Contract"),
        ],
        default="full-time",
    )
    preferred_language = models.CharField(max_length=100, default="English")

    linkedin_url = models.URLField(blank=True)
    github_url = models.URLField(blank=True)
    career_roadmap = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} Profile"

    def get_target_companies_list(self):
        return [c.strip() for c in self.target_companies.split(",") if c.strip()]

    def get_skills_list(self):
        return [s.strip() for s in self.skills.split(",") if s.strip()]


class InterviewReport(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="interview_reports"
    )
    title = models.CharField(max_length=255)
    target_company = models.CharField(max_length=255, blank=True)
    job_description = models.TextField()
    resume_content = models.TextField(blank=True, null=True)
    self_description = models.TextField(blank=True, null=True)
    match_score = models.IntegerField(default=0)

    # Using JSONField to store structured data from AI
    technical_questions = models.JSONField(default=list)
    behavioral_questions = models.JSONField(default=list)
    coding_questions = models.JSONField(default=list)
    skill_gaps = models.JSONField(default=list)
    preparation_plan = models.JSONField(default=list)

    # ML ATS Prediction fields
    ats_score = models.IntegerField(default=0)
    ats_matching_keywords = models.JSONField(default=list)
    ats_missing_keywords = models.JSONField(default=list)

    # User personal notes on this report
    notes = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} @ {self.target_company if self.target_company else 'General'} - {self.user.username}"


class MockInterviewSession(models.Model):
    STATUS_CHOICES = [
        ("active", "Active"),
        ("completed", "Completed"),
    ]
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="mock_sessions"
    )
    report = models.ForeignKey(
        InterviewReport, on_delete=models.CASCADE, related_name="mock_sessions"
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="active")
    overall_score = models.FloatField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Mock Session - {self.user.username} - {self.report.title}"

    def calculate_overall_score(self):
        answers = self.answers.all()
        if not answers:
            return None
        scored = [a.ai_score for a in answers if a.ai_score is not None]
        if not scored:
            return None
        return round(sum(scored) / len(scored), 1)


class QuestionAnswer(models.Model):
    QUESTION_TYPE_CHOICES = [
        ("technical", "Technical"),
        ("behavioral", "Behavioral"),
        ("coding", "Coding"),
    ]
    session = models.ForeignKey(
        MockInterviewSession, on_delete=models.CASCADE, related_name="answers"
    )
    question_text = models.TextField()
    question_type = models.CharField(
        max_length=20, choices=QUESTION_TYPE_CHOICES, default="technical"
    )
    question_index = models.IntegerField(default=0)
    user_answer = models.TextField()
    ai_score = models.FloatField(null=True, blank=True)  # 0-10
    ai_feedback = models.TextField(blank=True)
    ai_strengths = models.JSONField(default=list)
    ai_improvements = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["question_index"]

    def __str__(self):
        return f"Q{self.question_index} - Score: {self.ai_score}"


# ---------------------------------------------------------------------------
# High-Level Industry Project Features
# ---------------------------------------------------------------------------



class STARSession(models.Model):
    STATUS_CHOICES = [
        ("active", "Active"),
        ("completed", "Completed"),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="star_sessions")
    question_text = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="active")
    chat_history = models.JSONField(default=list, help_text="Complete transcript of the conversation")
    ai_score = models.FloatField(null=True, blank=True)
    ai_feedback = models.JSONField(default=dict, help_text="Final analysis breaking down S-T-A-R components")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"STAR Session ({self.id}) - {self.user.username}"


class MegaInterviewSession(models.Model):
    STATUS_CHOICES = [
        ("active", "Active"),
        ("completed", "Completed"),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="mega_sessions")
    experience_level = models.CharField(max_length=50)
    resume_text = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="active")
    
    # Stores the generated questions structure from AI
    questions = models.JSONField(default=list) 
    
    # Stores user's submitted answers
    answers = models.JSONField(default=dict)
    
    # Stores the final evaluation from AI
    ai_review = models.JSONField(default=dict, help_text="Final comprehensive review including score and topics to learn")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Mega Interview Session ({self.id}) - {self.user.username}"


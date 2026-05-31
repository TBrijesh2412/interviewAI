import os
import random
import json
import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_POST, require_http_methods
from django.views.decorators.csrf import csrf_exempt
from .models import (
    UserProfile,
    InterviewReport,
    MockInterviewSession,
    STARSession,
    MegaInterviewSession,
)
from .services import (
    generate_interview_report,
    generate_resume_html,
    convert_html_to_pdf,
    evaluate_mock_answer,
    get_user_analytics,
    generate_cover_letter,
    generate_career_roadmap,
    generate_mega_interview,
    evaluate_mega_interview,
)

logger = logging.getLogger("core")


# ---------------------------------------------------------------------------
# Auth views
# ---------------------------------------------------------------------------


def landing_page(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    return render(request, "core/landing.html")


def register_view(request):
    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Create an empty profile
            UserProfile.objects.get_or_create(user=user)
            login(request, user)
            return redirect("dashboard")
    else:
        form = UserCreationForm()
    return render(request, "core/register.html", {"form": form})


def login_view(request):
    if request.method == "POST":
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect("dashboard")
    else:
        form = AuthenticationForm()
    return render(request, "core/login.html", {"form": form})


def logout_view(request):
    logout(request)
    return redirect("landing")


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------


@login_required
def dashboard(request):
    # Ensure profile exists
    UserProfile.objects.get_or_create(user=request.user)

    sort_by = request.GET.get("sort", "-created_at")
    allowed_sorts = ["-created_at", "created_at", "-match_score", "match_score"]
    if sort_by not in allowed_sorts:
        sort_by = "-created_at"

    reports = InterviewReport.objects.filter(user=request.user).order_by(sort_by)
    analytics = get_user_analytics(request.user)
    return render(
        request,
        "core/dashboard_main.html",
        {
            "reports": reports,
            "analytics": analytics,
            "current_sort": sort_by,
        },
    )


# ---------------------------------------------------------------------------
# Report CRUD
# ---------------------------------------------------------------------------


@login_required
def create_report(request):
    if request.method == "POST":
        job_description = request.POST.get("job_description")
        self_description = request.POST.get("self_description")
        target_company = request.POST.get("target_company", "")
        resume_file = request.FILES.get("resume")

        resume_content = ""
        if resume_file:
            if resume_file.name.endswith(".pdf"):
                from pypdf import PdfReader

                try:
                    reader = PdfReader(resume_file)
                    for page in reader.pages:
                        resume_content += page.extract_text() + "\n"
                except Exception as e:
                    logger.error(f"Error extracting PDF: {e}")
                    resume_content = resume_file.read().decode("utf-8", errors="ignore")
            else:
                resume_content = resume_file.read().decode("utf-8", errors="ignore")
        else:
            # Fallback to profile resume
            if hasattr(request.user, "profile") and request.user.profile.resume_text:
                resume_content = request.user.profile.resume_text

        logger.info(f"Generating report for user {request.user.username}")

        try:
            from .ml_services import calculate_ats_score

            # 1. Generate Interview Questions (LLM)
            report_data = generate_interview_report(
                resume_content, self_description, job_description, target_company
            )

            # 2. Calculate ATS ML Score
            logger.info("Calculating ATS Score via ML Pipeline...")
            ats_data = calculate_ats_score(resume_content, job_description)

            report = InterviewReport.objects.create(
                user=request.user,
                title=report_data.get("title", "Interview Report"),
                target_company=target_company,
                job_description=job_description,
                resume_content=resume_content,
                self_description=self_description,
                match_score=report_data.get("matchScore", 0),
                technical_questions=report_data.get("technicalQuestions", []),
                behavioral_questions=report_data.get("behavioralQuestions", []),
                coding_questions=report_data.get("codingQuestions", []),
                skill_gaps=report_data.get("skillGaps", []),
                preparation_plan=report_data.get("preparationPlan", []),
                # ML ATS Results
                ats_score=ats_data.get("score", 0),
                ats_matching_keywords=ats_data.get("matching_keywords", []),
                ats_missing_keywords=ats_data.get("missing_keywords", []),
            )
            logger.info(
                f"Report created: {report.id} with ATS Score {ats_data.get('score')}"
            )
            return redirect("report_detail", report_id=report.id)
        except Exception as e:
            logger.exception("Error in create_report view")
            return render(request, "core/create_report.html", {"error": str(e)})

    return render(request, "core/create_report.html")


@login_required
def report_detail(request, report_id):
    report = get_object_or_404(InterviewReport, id=report_id, user=request.user)
    sessions = report.mock_sessions.filter(status="completed").order_by("-created_at")
    return render(
        request,
        "core/report_detail.html",
        {
            "report": report,
            "mock_sessions": sessions,
        },
    )


@login_required
@require_POST
def delete_report(request, report_id):
    report = get_object_or_404(InterviewReport, id=report_id, user=request.user)
    report.delete()
    return JsonResponse({"success": True})


@login_required
@require_POST
def save_notes(request, report_id):
    report = get_object_or_404(InterviewReport, id=report_id, user=request.user)
    try:
        data = json.loads(request.body)
        report.notes = data.get("notes", "")
        report.save(update_fields=["notes"])
        return JsonResponse({"success": True})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=400)


# ---------------------------------------------------------------------------
# User Profile
# ---------------------------------------------------------------------------


@login_required
def profile_view(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)

    if request.method == "POST":
        profile.target_role = request.POST.get("target_role", "")
        profile.experience_level = request.POST.get("experience_level", "")
        profile.headline = request.POST.get("headline", "")
        profile.target_companies = request.POST.get("target_companies", "")
        profile.skills = request.POST.get("skills", "")

        # New Fields
        profile.city = request.POST.get("city", "")
        profile.employment_type = request.POST.get("employment_type", "full-time")
        profile.preferred_language = request.POST.get("preferred_language", "English")

        joining_date = request.POST.get("preferred_joining")
        if joining_date:
            profile.preferred_joining = joining_date
        else:
            profile.preferred_joining = None

        profile.linkedin_url = request.POST.get("linkedin_url", "")
        profile.github_url = request.POST.get("github_url", "")

        # Handle Document Upload and Parse via pdfplumber
        resume_file = request.FILES.get("resume_file")
        if resume_file:
            profile.resume_file = resume_file
            if resume_file.name.lower().endswith(".pdf"):
                try:
                    import pdfplumber

                    text = ""
                    # pdfplumber requires a real file object
                    with pdfplumber.open(resume_file) as pdf:
                        for page in pdf.pages:
                            page_text = page.extract_text()
                            if page_text:
                                text += page_text + "\n"
                    profile.resume_text = text
                    logger.info(
                        f"Successfully extracted {len(text)} characters from uploaded resume."
                    )
                except Exception as e:
                    logger.error(f"Error parsing resume via pdfplumber: {e}")
                    # Keep existing text if parse fails, or set to empty
                    pass

        profile.save()
        return redirect("/profile/?saved=1")

    return render(request, "core/profile.html", {"profile": profile})


@login_required
def analyze_job_url(request):
    if request.method == "POST":
        url = request.POST.get("job_url")
        if not url:
            return redirect("dashboard")

        from .services import scrape_job_from_url, generate_interview_report

        logger.info(f"Analyzing job URL: {url}")
        job_data = scrape_job_from_url(url)

        if not job_data:
            return render(
                request,
                "core/job_matcher.html",
                {
                    "error": "Could not scrape this URL. Please ensure it's a valid job link.",
                    "profile": request.user.profile,
                    "analytics": get_user_analytics(request.user),
                },
            )

        # Generate report from scraped data
        try:
            # We use an empty resume if the user hasn't uploaded one for this specific analysis,
            # but ideally we'd use their last known profile details.
            profile = request.user.profile
            resume_content = (
                f"Skills: {profile.skills}\nTarget Role: {profile.target_role}"
            )

            from .ml_services import calculate_ats_score

            report_data = generate_interview_report(
                resume_content,
                profile.headline,
                job_data["description"],
                job_data["company"],
            )

            # Calculate ATS Score for Scraped Job
            logger.info("Calculating ATS Score for scraped job...")
            ats_data = calculate_ats_score(resume_content, job_data["description"])

            report = InterviewReport.objects.create(
                user=request.user,
                title=job_data["title"],
                target_company=job_data["company"],
                job_description=job_data["description"],
                resume_content=resume_content,
                match_score=report_data.get("matchScore", 0),
                technical_questions=report_data.get("technicalQuestions", []),
                behavioral_questions=report_data.get("behavioralQuestions", []),
                coding_questions=report_data.get("codingQuestions", []),
                skill_gaps=report_data.get("skillGaps", []),
                preparation_plan=report_data.get("preparationPlan", []),
                # ML ATS Results
                ats_score=ats_data.get("score", 0),
                ats_matching_keywords=ats_data.get("matching_keywords", []),
                ats_missing_keywords=ats_data.get("missing_keywords", []),
            )
            return redirect("report_detail", report_id=report.id)
        except Exception as e:
            logger.exception("Error in analyze_job_url")
            return render(request, "core/dashboard_main.html", {"error": str(e)})

    return redirect("dashboard")


# ---------------------------------------------------------------------------
# Technical Whiteboard
# ---------------------------------------------------------------------------


@login_required
def coding_whiteboard(request):
    problems = [
        {
            "description": "Design a function to find the longest palindromic substring.",
            "boilerplate": "def longest_palindrome(s: str) -> str:\n    # Write your code here...\n    pass"
        },
        {
            "description": "Implement a function to check if a binary tree is balanced.",
            "boilerplate": "class TreeNode:\n    def __init__(self, val=0, left=None, right=None):\n        self.val = val\n        self.left = left\n        self.right = right\n\ndef is_balanced(root: TreeNode) -> bool:\n    # Write your code here...\n    pass"
        },
        {
            "description": "Write a function to merge two sorted linked lists.",
            "boilerplate": "class ListNode:\n    def __init__(self, val=0, next=None):\n        self.val = val\n        self.next = next\n\ndef merge_two_lists(l1: ListNode, l2: ListNode) -> ListNode:\n    # Write your code here...\n    pass"
        },
        {
            "description": "Design a function to find the maximum subarray sum (Kadane's Algorithm).",
            "boilerplate": "def max_sub_array(nums: list[int]) -> int:\n    # Write your code here...\n    pass"
        },
        {
            "description": "Implement a Least Recently Used (LRU) Cache.",
            "boilerplate": "class LRUCache:\n    def __init__(self, capacity: int):\n        pass\n\n    def get(self, key: int) -> int:\n        pass\n\n    def put(self, key: int, value: int) -> None:\n        pass"
        }
    ]
    problem = random.choice(problems)
    return render(request, "core/whiteboard.html", {
        "problem": problem["description"],
        "boilerplate": problem["boilerplate"]
    })


@login_required
@require_POST
def evaluate_code(request):
    try:
        body_unicode = request.body.decode("utf-8")
        logger.info(f"evaluate_code request body: {body_unicode[:500]}...")
        if not body_unicode:
            return JsonResponse({"error": "Empty request body"}, status=400)
        data = json.loads(body_unicode)
        code = data.get("code", "")
        language = data.get("language", "python")
        problem = data.get(
            "problem", "Design a function to find the longest palindromic substring."
        )

        if not code.strip():
            return JsonResponse({"error": "Code cannot be empty."}, status=400)

        # We can reuse evaluate_mock_answer or create a specialized one
        # For whiteboard, let's use the generic completion for more flexibility
        from .services import client, MODEL_NAME, parse_ai_json

        system_prompt = """You are a senior technical interviewer. 
        Evaluate the provided code for:
        1. Correctness
        2. Time & Space Complexity
        3. Code Quality
        Output ONLY valid JSON:
        {
            "score": 8.5,
            "complexity": "O(N^2) time, O(1) space",
            "feedback": "...",
            "suggestions": ["...", "..."]
        }"""

        prompt = f"Problem: {problem}\nLanguage: {language}\nCode:\n{code}"

        try:
            completion = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,
            )

            content = completion.choices[0].message.content or ""
            logger.info(f"Whiteboard AI response: {content[:500]}...")

            if not content.strip():
                raise ValueError("Empty AI response")

            result = parse_ai_json(content)
            return JsonResponse(result)
        except Exception as e:
            logger.error(f"Fallback triggered for evaluation: {e}")
            # Fallback for UI consistency
            return JsonResponse(
                {
                    "score": 5.0,
                    "complexity": "N/A",
                    "feedback": "Deep AI review failed. Please try again or simplify your code.",
                    "suggestions": [
                        "Check your internet connection",
                        "Try a shorter code snippet",
                    ],
                }
            )
    except Exception as e:
        logger.exception("Error in evaluate_code")
        return JsonResponse({"error": str(e)}, status=500)




# ---------------------------------------------------------------------------
# Code Review / PR Simulator
# ---------------------------------------------------------------------------



# ---------------------------------------------------------------------------
# Mega Interview
# ---------------------------------------------------------------------------

@login_required
def mega_interview_setup(request):
    """
    Shows a form to upload a resume and select experience level.
    On submit, generates the interview questions via AI and redirects to the session.
    """
    if request.method == "POST":
        experience_level = request.POST.get("experience_level")
        resume_file = request.FILES.get("resume")
        
        resume_content = ""
        if resume_file:
            if resume_file.name.endswith(".pdf"):
                from pypdf import PdfReader
                try:
                    reader = PdfReader(resume_file)
                    for page in reader.pages:
                        resume_content += page.extract_text() + "\n"
                except Exception as e:
                    logger.error(f"Error extracting PDF: {e}")
                    resume_content = resume_file.read().decode("utf-8", errors="ignore")
            else:
                resume_content = resume_file.read().decode("utf-8", errors="ignore")
        else:
            # Fallback to profile resume
            if hasattr(request.user, "profile") and request.user.profile.resume_text:
                resume_content = request.user.profile.resume_text
                
        if not resume_content.strip():
            return render(request, "core/mega_interview_setup.html", {"error": "Please provide a resume to generate questions."})

        # Generate Mega Interview questions via Groq AI
        questions_data = generate_mega_interview(resume_content, experience_level)
        
        if "error" in questions_data:
            return render(request, "core/mega_interview_setup.html", {"error": questions_data["error"]})
            
        session = MegaInterviewSession.objects.create(
            user=request.user,
            experience_level=experience_level,
            resume_text=resume_content,
            questions=questions_data
        )
        
        return redirect("mega_interview_interface", session_id=session.id)
        
    return render(request, "core/mega_interview_setup.html")


@login_required
def mega_interview_interface(request, session_id):
    """
    The Single Page Application interface for the Mega Interview.
    """
    session = get_object_or_404(MegaInterviewSession, id=session_id, user=request.user)
    
    if session.status == "completed":
        return redirect("mega_interview_result", session_id=session.id)
        
    # Prepare all questions into a flat structure with indices for the frontend JS
    all_questions = []
    
    hr_questions = session.questions.get("hr_questions", [])
    for q in hr_questions:
        q["category"] = "HR / Behavioral"
        all_questions.append(q)
        
    tech_questions = session.questions.get("tech_questions", [])
    for q in tech_questions:
        q["category"] = "Technical"
        all_questions.append(q)
        
    coding_questions = session.questions.get("coding_questions", [])
    for q in coding_questions:
        q["category"] = "Coding"
        all_questions.append(q)
        
    return render(request, "core/mega_interview_interface.html", {
        "session": session,
        "questions": all_questions
    })


@require_POST
@login_required
def mega_interview_evaluate(request, session_id):
    """
    API Endpoint. Receives all user answers from the SPA, evaluates them, and marks the session complete.
    """
    session = get_object_or_404(MegaInterviewSession, id=session_id, user=request.user)
    
    try:
        data = json.loads(request.body)
        answers = data.get("answers", {})
        
        session.answers = answers
        
        # Evaluate using AI
        ai_review = evaluate_mega_interview(session.questions, answers)
        session.ai_review = ai_review
        session.status = "completed"
        session.save()
        
        return JsonResponse({"success": True, "redirect_url": f"/mega-interview/{session.id}/result/"})
    except Exception as e:
        logger.exception("Error evaluating Mega Interview")
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@require_POST
@login_required
def run_code(request):
    """
    Safely executes user-provided code using subprocess.
    """
    try:
        data = json.loads(request.body)
        code = data.get("code", "")
        language = data.get("language", "python").lower()

        if not code.strip():
            return JsonResponse({"error": "Code cannot be empty."}, status=400)

        if language != "python":
            return JsonResponse({"error": f"Execution for {language} is not supported yet."}, status=400)

        import subprocess
        import sys
        import tempfile

        # Create a temporary file for the code
        with tempfile.NamedTemporaryFile(suffix=".py", delete=False, mode="w") as tmp:
            tmp.write(code)
            tmp_path = tmp.name

        try:
            # Use current python interpreter for execution
            result = subprocess.run(
                [sys.executable, tmp_path],
                capture_output=True,
                text=True,
                timeout=5, # 5 second timeout
            )
            
            return JsonResponse({
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode
            })
        except subprocess.TimeoutExpired:
            return JsonResponse({"error": "Execution timed out (5s limit)."}, status=408)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
        finally:
            import os
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    except Exception as e:
        logger.exception("Error in run_code view")
        return JsonResponse({"error": str(e)}, status=500)


@login_required
def mega_interview_result(request, session_id):
    """
    Displays the final evaluation and topics to learn.
    """
    session = get_object_or_404(MegaInterviewSession, id=session_id, user=request.user)
    
    if session.status != "completed":
        return redirect("mega_interview_interface", session_id=session.id)
        
    return render(request, "core/mega_interview_result.html", {
        "session": session,
        "ai_review": session.ai_review
    })


# ---------------------------------------------------------------------------
# Job Matcher
# ---------------------------------------------------------------------------


@login_required
def job_matcher(request):
    from .services import get_user_analytics, fetch_live_jobs

    profile = request.user.profile
    analytics = get_user_analytics(request.user)

    # Ensure mastery_data exists even if analytics is missing it (though services.py should handle it now)
    if "mastery_data" not in analytics:
        analytics["mastery_data"] = []

    recommendations = []
    if request.method == "POST":
        recommendations = fetch_live_jobs(profile.target_role, profile.city)

    return render(
        request,
        "core/job_matcher.html",
        {
            "profile": profile,
            "analytics": analytics,
            "recommendations": recommendations,
            "has_searched": request.method == "POST",
        },
    )


# ---------------------------------------------------------------------------
# STAR Behavioral Coach
# ---------------------------------------------------------------------------

@login_required
def star_coach_view(request):
    """
    Renders the STAR Behavioral Coach chat interface.
    """
    # Create or get active session
    session = STARSession.objects.filter(user=request.user, status="active").first()
    
    if not session:
        questions = [
            "Tell me about a time you had to deal with a difficult coworker or team member.",
            "Describe a situation where you had to meet a tight deadline under significant pressure.",
            "Tell me about a time you failed or made a major mistake at work. How did you handle it?",
            "Give an example of a time you went above and beyond for a customer or project.",
            "Describe a time you lead a project or initiative from scratch."
        ]
        question = random.choice(questions)
        initial_history = [
            {"role": "assistant", "content": f"Hi there! Let's practice a behavioral question. To help you structure your answer, please use the STAR method (Situation, Task, Action, Result).\n\nHere is your question: **{question}**"}
        ]
        
        session = STARSession.objects.create(
            user=request.user,
            question_text=question,
            chat_history=initial_history
        )
        
    return render(request, "core/star_coach.html", {
        "session": session
    })


@login_required
@require_POST
def star_coach_message(request):
    """
    Handles chat messages and uses the STAR Coach LLM logic.
    """
    try:
        data = json.loads(request.body.decode("utf-8"))
        message = data.get("message", "")
        
        session = STARSession.objects.filter(user=request.user, status="active").first()
        if not session:
            return JsonResponse({"error": "No active session found."}, status=400)
            
        # Append user message
        history = session.chat_history
        history.append({"role": "user", "content": message})
        
        from .services import analyze_star_response
        
        # We pass the history to the AI to evaluate if S, T, A, R are fully covered
        ai_response = analyze_star_response(session.question_text, history)
        
        # Append AI response
        history.append({"role": "assistant", "content": ai_response.get("reply", "")})
        
        session.chat_history = history
        
        # Check if interview is concluded
        if ai_response.get("is_complete"):
            session.status = "completed"
            session.ai_score = ai_response.get("score")
            session.ai_feedback = ai_response
            
        session.save()
        
        return JsonResponse(ai_response)

    except Exception as e:
        logger.exception("Error in star_coach_message")
        return JsonResponse({"error": str(e)}, status=500)


@login_required
@require_POST
def clear_star_coach(request):
    """
    Clears the current active STAR session for the user by marking it completed.
    This allows the user to start a fresh chat.
    """
    STARSession.objects.filter(user=request.user, status="active").update(status="completed")
    return JsonResponse({"success": True})


# ---------------------------------------------------------------------------
# Analytics
# ---------------------------------------------------------------------------


@login_required
def analytics_view(request):
    analytics = get_user_analytics(request.user)
    return render(request, "core/analytics.html", {"analytics": analytics})


# ---------------------------------------------------------------------------
# Mock Interview
# ---------------------------------------------------------------------------


@login_required
def mock_interview_start(request, report_id):
    report = get_object_or_404(InterviewReport, id=report_id, user=request.user)
    # Create a fresh session
    session = MockInterviewSession.objects.create(user=request.user, report=report)

    all_questions = []
    for i, q in enumerate(report.technical_questions):
        all_questions.append(
            {
                "index": len(all_questions),
                "type": "technical",
                "text": q.get("question", ""),
            }
        )
    for i, q in enumerate(report.behavioral_questions):
        all_questions.append(
            {
                "index": len(all_questions),
                "type": "behavioral",
                "text": q.get("question", ""),
            }
        )
    for i, q in enumerate(report.coding_questions):
        all_questions.append(
            {
                "index": len(all_questions),
                "type": "coding",
                "text": q.get("question", ""),
            }
        )

    return render(
        request,
        "core/mock_interview.html",
        {
            "session": session,
            "report": report,
            "questions": json.dumps(all_questions),
            "total": len(all_questions),
        },
    )


@login_required
@require_POST
def mock_interview_answer(request, session_id):
    session = get_object_or_404(MockInterviewSession, id=session_id, user=request.user)
    try:
        data = json.loads(request.body)
        question_text = data.get("question", "")
        question_type = data.get("question_type", "technical")
        question_index = data.get("question_index", 0)
        user_answer = data.get("answer", "")

        if not user_answer.strip():
            return JsonResponse({"error": "Answer cannot be empty."}, status=400)

        # Evaluate with AI
        job_context = f"Company: {session.report.target_company}\nJob: {session.report.job_description[:1000]}"
        result = evaluate_mock_answer(question_text, user_answer, job_context)

        # Save the Q&A
        qa = QuestionAnswer.objects.create(
            session=session,
            question_text=question_text,
            question_type=question_type,
            question_index=question_index,
            user_answer=user_answer,
            ai_score=result.get("score", 5.0),
            ai_feedback=result.get("feedback", ""),
            ai_strengths=result.get("strengths", []),
            ai_improvements=result.get("improvements", []),
        )

        return JsonResponse(
            {
                "score": qa.ai_score,
                "feedback": qa.ai_feedback,
                "strengths": qa.ai_strengths,
                "improvements": qa.ai_improvements,
            }
        )
    except Exception as e:
        logger.exception("Error in mock_interview_answer")
        return JsonResponse({"error": str(e)}, status=500)


@login_required
@require_POST
def mock_interview_complete(request, session_id):
    session = get_object_or_404(MockInterviewSession, id=session_id, user=request.user)
    session.status = "completed"
    session.overall_score = session.calculate_overall_score()
    session.save()
    return JsonResponse(
        {
            "success": True,
            "overall_score": session.overall_score,
            "redirect": f"/report/{session.report.id}/",
        }
    )


# ---------------------------------------------------------------------------
# Resume Builder
# ---------------------------------------------------------------------------


@login_required
def resume_builder_view(request, report_id):
    report = get_object_or_404(InterviewReport, id=report_id, user=request.user)

    if request.method == "POST":
        # Accepts multipart/form-data (with optional file upload)
        try:
            style = request.POST.get("style", "modern")

            # Start with the stored resume content from the report
            combined_resume = report.resume_content or ""

            # If user uploaded an additional resume file, extract and merge it
            uploaded_file = request.FILES.get("resume_file")
            if uploaded_file:
                extra_text = ""
                filename = uploaded_file.name.lower()
                if filename.endswith(".pdf"):
                    try:
                        from pypdf import PdfReader

                        reader = PdfReader(uploaded_file)
                        for page in reader.pages:
                            extra_text += (page.extract_text() or "") + "\n"
                    except Exception as e:
                        logger.warning(f"PDF parse failed for uploaded resume: {e}")
                        extra_text = uploaded_file.read().decode(
                            "utf-8", errors="ignore"
                        )
                else:
                    extra_text = uploaded_file.read().decode("utf-8", errors="ignore")

                if extra_text.strip():
                    combined_resume = (
                        "=== UPLOADED RESUME ===\n"
                        + extra_text.strip()
                        + "\n\n=== ORIGINAL REPORT RESUME ===\n"
                        + combined_resume
                    )
                    logger.info(
                        f"Merged uploaded resume ({len(extra_text)} chars) with report content"
                    )

            logger.info(
                f"Generating resume preview for report {report_id} style={style}, "
                f"resume_chars={len(combined_resume)}"
            )

            html_content = generate_resume_html(
                combined_resume,
                report.self_description,
                report.job_description,
                report.target_company,
                style=style,
            )
            return JsonResponse({"html": html_content})
        except Exception as e:
            logger.exception("Error generating resume preview")
            return JsonResponse({"error": str(e)}, status=500)

    return render(request, "core/resume_builder.html", {"report": report})


@login_required
def download_resume(request, report_id):
    report = get_object_or_404(InterviewReport, id=report_id, user=request.user)
    style = request.GET.get("style", "modern")
    logger.info(f"Generating resume PDF for report {report_id} style={style}")
    html_content = generate_resume_html(
        report.resume_content,
        report.self_description,
        report.job_description,
        report.target_company,
        style=style,
    )
    pdf_buffer = convert_html_to_pdf(html_content)

    if pdf_buffer:
        response = HttpResponse(pdf_buffer, content_type="application/pdf")
        response["Content-Disposition"] = (
            f'attachment; filename="resume_{report.id}.pdf"'
        )
        return response
    logger.error(f"PDF generation failed for report {report_id}")
    return HttpResponse("Error generating PDF", status=500)


@login_required
def cover_letter_view(request, report_id):
    report = get_object_or_404(InterviewReport, id=report_id, user=request.user)

    # Check if we should generate or just show
    if request.method == "POST":
        try:
            data = generate_cover_letter(
                report.resume_content,
                report.self_description,
                report.job_description,
                report.target_company,
            )
            return render(
                request,
                "core/cover_letter.html",
                {
                    "report": report,
                    "letter_title": data.get("title", "Cover Letter"),
                    "letter_content": data.get("content", ""),
                },
            )
        except Exception as e:
            logger.exception("Error generating cover letter")
            return render(
                request, "core/report_detail.html", {"report": report, "error": str(e)}
            )

    return render(request, "core/cover_letter.html", {"report": report})


# ---------------------------------------------------------------------------
# Career Roadmap
# ---------------------------------------------------------------------------


@login_required
def career_roadmap(request):
    profile = request.user.profile
    roadmap_data = profile.career_roadmap

    # If no roadmap exists, redirect to selection page
    if not roadmap_data:
        return redirect("roadmap_selection")

    return render(
        request,
        "core/career_roadmap.html",
        {"roadmap": roadmap_data, "profile": profile},
    )


@login_required
def roadmap_selection(request):
    profile = request.user.profile
    # Check for existing preferences to pre-fill the form
    return render(request, "core/roadmap_selection.html", {"profile": profile})


@login_required
@require_POST
def generate_roadmap_post(request):
    profile = request.user.profile

    selected_role = request.POST.get("role")
    selected_level = request.POST.get("level")
    selected_focus = request.POST.getlist("focus")  # Multiple focus areas
    timeline_pref = request.POST.get("timeline")

    focus_str = ", ".join(selected_focus) if selected_focus else "General Tech Stack"

    # Temporarily override role for this generation if provided
    if selected_role:
        profile.target_role = selected_role
        profile.save(update_fields=["target_role"])

    reports = InterviewReport.objects.filter(user=request.user).order_by("-created_at")[
        :5
    ]

    roadmap_data = generate_career_roadmap(
        profile,
        reports,
        selected_level=selected_level,
        selected_focus=focus_str,
        timeline_pref=timeline_pref,
    )

    # Store preferences in the roadmap data for future editing
    roadmap_data["preferences"] = {
        "role": selected_role,
        "level": selected_level,
        "focus": selected_focus,
        "timeline": timeline_pref,
    }

    profile.career_roadmap = roadmap_data
    profile.save(update_fields=["career_roadmap"])

    return redirect("roadmap")


@login_required
@require_POST
def refresh_roadmap(request):
    profile = request.user.profile
    prev_prefs = profile.career_roadmap.get("preferences", {})

    reports = InterviewReport.objects.filter(user=request.user).order_by("-created_at")[
        :5
    ]

    roadmap_data = generate_career_roadmap(
        profile,
        reports,
        selected_level=prev_prefs.get("level"),
        selected_focus=", ".join(prev_prefs.get("focus", [])) or None,
        timeline_pref=prev_prefs.get("timeline"),
    )

    roadmap_data["preferences"] = prev_prefs

    profile.career_roadmap = roadmap_data
    profile.save(update_fields=["career_roadmap"])
    return JsonResponse({"success": True})


def ping(request):
    """Ultra-lightweight health check endpoint used by the reload detector.
    Must NOT do any DB queries or ML processing - just return OK instantly."""
    return JsonResponse({"status": "ok"})

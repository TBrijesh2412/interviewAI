import logging
from groq import Groq
import os
import json
from django.conf import settings
from xhtml2pdf import pisa
from io import BytesIO
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("core")

MODEL_NAME = "llama-3.3-70b-versatile"

# Initialize Groq client at module level to reuse connections
api_key = os.getenv("GROQ_API_KEY")
if not api_key:
    logger.error("GROQ_API_KEY is not set!")
client = Groq(api_key=api_key, timeout=60.0)

# Initialize Tavily client for live job search
tavily_api_key = os.getenv("TAVILY_API_KEY")
_tavily_client = None
if tavily_api_key and tavily_api_key != "your-tavily-api-key-here":
    try:
        from tavily import TavilyClient

        _tavily_client = TavilyClient(api_key=tavily_api_key)
        logger.info("Tavily client initialized successfully.")
    except Exception as e:
        logger.warning(f"Failed to initialize Tavily client: {e}")
else:
    logger.warning("TAVILY_API_KEY not set. Job search will use mock data.")


def parse_ai_json(content):
    """
    Robustly extracts and parses JSON from AI output.
    Handles Markdown blocks and conversational filler.
    """
    content = str(content).strip()
    try:
        # Try direct parse first
        return json.loads(content, strict=False)
    except json.JSONDecodeError:
        # Try extracting from { ... }
        start = content.find("{")
        end = content.rfind("}") + 1
        if start != -1 and end > start:
            try:
                return json.loads(content[start:end], strict=False)
            except json.JSONDecodeError:
                pass

        # Try extracting from [ ... ] if it's an array
        start_arr = content.find("[")
        end_arr = content.rfind("]") + 1
        if start_arr != -1 and end_arr > start_arr:
            try:
                return json.loads(content[start_arr:end_arr], strict=False)
            except json.JSONDecodeError:
                pass

        raise


def generate_interview_report(
    resume, self_description, job_description, target_company=""
):
    resume = str(resume)[:8000]
    self_description = str(self_description)[:2000]
    job_description = str(job_description)[:6000]
    target_company = str(target_company)[:255]

    system_prompt = """You are an expert technical interviewer. Output ONLY a valid JSON object.
    
    CRITICAL: You MUST use the provided Resume context to highly personalize the interview. Ask specific questions about their past projects, companies, and exact skills as listed in their resume to simulate a real-world, personalized interview.

    JSON STRUCTURE:
    {
        "matchScore": 85,
        "technicalQuestions": [{"question": "...", "intention": "...", "answer": "..."}],
        "behavioralQuestions": [{"question": "...", "intention": "...", "answer": "..."}],
        "codingQuestions": [{"question": "Problem title and description", "intention": "What this tests", "answer": "Sample solution code"}],
        "skillGaps": [{"skill": "...", "severity": "medium"}],
        "preparationPlan": [{"day": 1, "focus": "...", "tasks": ["..."]}],
        "title": "Job Title"
    }
    IMPORTANT: Provide exactly 2 coding questions suitable for the role.
    
    SKILL GAPS RULES (CRITICAL):
    - skillGaps must ONLY contain skills that are explicitly required by the Job Description but are clearly MISSING from the candidate's resume/profile.
    - Do NOT add technologies that are unrelated to the job description just because they are popular.
    - For example: if someone applies for an ML Engineer role, do NOT add Java, MERN, or Spring Boot as gaps unless the job description specifically requires them.
    - Severity: "high" = core required skill missing, "medium" = mentioned in JD but not critical, "low" = nice-to-have.
    - If the candidate already has a skill listed in their resume, it is NOT a gap.
    - Maximum 5 skill gaps. If no real gaps exist, return an empty array [].
    """

    prompt = f"Target Company: {target_company}\nResume: {resume}\nSelf Description: {self_description}\nJob Description: {job_description}"

    logger.debug(f"Prompting {MODEL_NAME} for interview report")
    completion = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ],
        temperature=0.1,
    )

    content = completion.choices[0].message.content.strip()
    logger.debug(f"Raw Groq response: {content}")

    try:
        return parse_ai_json(content)
    except Exception as e:
        logger.error(f"Failed to parse Groq JSON: {e}")
        raise


def evaluate_mock_answer(question, user_answer, job_context=""):
    """
    Evaluates a user's mock interview answer using AI.
    Returns a dict with score (0-10), feedback, strengths, and improvements.
    """
    user_answer = str(user_answer)[:3000]
    job_context = str(job_context)[:2000]
    # job_context already contains target_company if passed from view

    system_prompt = """You are an expert technical interviewer evaluating a candidate's answer.
    Output ONLY valid JSON in this exact format:
    Score from 0-10. Be honest but constructive.
    If the question is a coding question, evaluate the code for correctness, complexity, and style.
    Output ONLY valid JSON in this exact format:
    {
        "score": 7.5,
        "feedback": "...",
        "strengths": ["...", "..."],
        "improvements": ["...", "..."]
    }"""

    prompt = f"""Interview Question: {question}

Job Context: {job_context}

Candidate's Answer:
{user_answer}

Evaluate this answer and return your assessment as JSON."""

    logger.debug(f"Evaluating mock answer with {MODEL_NAME}")
    try:
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
        )

        raw_content = completion.choices[0].message.content or ""
        logger.debug(f"Raw AI response: {raw_content[:200]}")

        if not raw_content.strip():
            raise ValueError("AI returned empty response")

        return parse_ai_json(raw_content)
    except Exception as e:
        logger.error(f"Failed to evaluate mock answer: {e}")
        return {
            "score": 5.0,
            "feedback": "Could not evaluate your answer. Please try again.",
            "strengths": [],
            "improvements": [
                "Try to be more specific and structured in your response."
            ],
        }




def get_user_analytics(user):
    """
    Aggregates analytics data from all of a user's reports.
    Returns a dict with stats, score trend, and skill gap frequency.
    """
    from .models import InterviewReport

    reports = InterviewReport.objects.filter(user=user).order_by("created_at")

    if not reports.exists():
        return {
            "total_reports": 0,
            "avg_score": 0,
            "best_score": 0,
            "score_trend": [],
            "skill_gap_frequency": {},
            "mastery_data": [],
        }

    scores = [r.match_score for r in reports]
    avg_score = round(sum(scores) / len(scores), 1)
    best_score = max(scores)

    score_trend = [
        {
            "date": r.created_at.strftime("%b %d"),
            "score": r.match_score,
            "title": r.title[:30],
        }
        for r in reports
    ]

    # Count frequency of each skill gap
    skill_gap_freq = {}
    for r in reports:
        for gap in r.skill_gaps:
            skill = gap.get("skill", "")
            if skill:
                skill_gap_freq[skill] = skill_gap_freq.get(skill, 0) + 1

    # Sort by frequency
    skill_gap_freq = dict(
        sorted(skill_gap_freq.items(), key=lambda x: x[1], reverse=True)[:10]
    )

    # Topic Mastery logic (New)
    from .models import MockInterviewSession

    attempts = MockInterviewSession.objects.filter(report__user=user)

    topic_mastery = {}
    for att in attempts:
        # Assuming we can infer topic from question or report title
        # For now, let's use a simple mapping or AI-extracted categories
        topic = "General"
        title_lower = att.report.title.lower()
        if "react" in title_lower:
            topic = "React"
        elif "python" in title_lower:
            topic = "Python"
        elif "django" in title_lower:
            topic = "Django"
        elif "java" in title_lower:
            topic = "Java"
        elif "behavioral" in title_lower:
            topic = "Behavioral"

        if topic not in topic_mastery:
            topic_mastery[topic] = {"scores": [], "count": 0}

        # Use overall_score from MockInterviewSession
        if att.overall_score is not None:
            topic_mastery[topic]["scores"].append(att.overall_score)
            topic_mastery[topic]["count"] += 1

    # Calculate averages and colors
    mastery_data = []
    for topic, stats in topic_mastery.items():
        if stats["count"] == 0:
            avg = 0
        else:
            avg = round(sum(stats["scores"]) / stats["count"], 1)

        # Calculate color in backend
        hue = 0  # Red
        if avg > 7:
            hue = 140  # Green
        elif avg > 5:
            hue = 45  # Gold

        opacity = min(0.9, (float(avg) + 2) / 10)
        color = f"hsla({hue}, 80%, 45%, {opacity})"

        mastery_data.append(
            {"topic": topic, "mastery": avg, "attempts": stats["count"], "color": color}
        )

    return {
        "total_reports": len(scores),
        "avg_score": avg_score,
        "best_score": best_score,
        "score_trend": score_trend,
        "skill_gap_frequency": skill_gap_freq,
        "mastery_data": mastery_data,
    }


def generate_resume_html(resume, self_description, job_description, target_company="", style="modern"):
    resume = str(resume)[:8000]
    self_description = str(self_description)[:2000]
    job_description = str(job_description)[:6000]
    target_company = str(target_company)[:255]
    style = str(style).lower()

    # Style-specific CSS themes
    style_css = {
        "modern": """
            body { font-family: 'Segoe UI', Arial, sans-serif; color: #1a1a2e; margin: 0; padding: 0; background: #f8f9fa; }
            .resume-wrap { max-width: 820px; margin: 0 auto; background: #fff; box-shadow: 0 4px 32px rgba(0,0,0,0.10); }
            .resume-header { background: linear-gradient(135deg, #1a1a2e 0%, #16213e 60%, #0f3460 100%); color: #fff; padding: 2.5rem 3rem 2rem; }
            .resume-header h1 { margin: 0 0 0.3rem; font-size: 2.2rem; font-weight: 800; letter-spacing: -0.03em; }
            .resume-header .headline { font-size: 1.05rem; opacity: 0.85; font-weight: 400; margin-bottom: 1rem; }
            .resume-header .contact { display: flex; gap: 1.5rem; flex-wrap: wrap; font-size: 0.82rem; opacity: 0.8; }
            .resume-body { padding: 2.5rem 3rem; }
            .section { margin-bottom: 2rem; }
            .section-title { font-size: 0.72rem; font-weight: 800; text-transform: uppercase; letter-spacing: 0.12em; color: #e94560; border-bottom: 2px solid #e94560; padding-bottom: 0.4rem; margin-bottom: 1.2rem; }
            .exp-item { margin-bottom: 1.5rem; }
            .exp-header { display: flex; justify-content: space-between; align-items: flex-start; }
            .exp-title { font-weight: 700; font-size: 1.05rem; color: #1a1a2e; }
            .exp-company { color: #0f3460; font-weight: 600; font-size: 0.92rem; }
            .exp-date { font-size: 0.8rem; color: #888; white-space: nowrap; background: #f0f4ff; padding: 0.2rem 0.7rem; border-radius: 20px; }
            .exp-bullets { margin: 0.6rem 0 0 1.1rem; padding: 0; }
            .exp-bullets li { font-size: 0.92rem; line-height: 1.6; color: #444; margin-bottom: 0.35rem; }
            .skills-grid { display: flex; flex-wrap: wrap; gap: 0.5rem; }
            .skill-badge { background: #f0f4ff; border: 1px solid #c7d8ff; color: #0f3460; padding: 0.3rem 0.85rem; border-radius: 20px; font-size: 0.82rem; font-weight: 600; }
            .summary-text { font-size: 0.97rem; line-height: 1.75; color: #444; }
        """,
        "classic": """
            body { font-family: 'Georgia', serif; color: #2d2d2d; margin: 0; padding: 0; background: #fff; }
            .resume-wrap { max-width: 820px; margin: 0 auto; background: #fff; border-top: 6px solid #8B4513; }
            .resume-header { text-align: center; padding: 2.5rem 3rem 1.5rem; border-bottom: 1px solid #ccc; }
            .resume-header h1 { margin: 0 0 0.3rem; font-size: 2.3rem; font-weight: 700; letter-spacing: 0.05em; text-transform: uppercase; color: #2d2d2d; }
            .resume-header .headline { font-size: 1rem; color: #8B4513; font-style: italic; margin-bottom: 0.8rem; }
            .resume-header .contact { display: flex; justify-content: center; gap: 1.5rem; flex-wrap: wrap; font-size: 0.82rem; color: #555; }
            .resume-body { padding: 2rem 3rem; }
            .section { margin-bottom: 2rem; }
            .section-title { font-size: 1rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.1em; color: #8B4513; border-bottom: 1px solid #8B4513; padding-bottom: 0.3rem; margin-bottom: 1.1rem; }
            .exp-item { margin-bottom: 1.5rem; }
            .exp-header { display: flex; justify-content: space-between; align-items: baseline; }
            .exp-title { font-weight: 700; font-size: 1rem; }
            .exp-company { color: #555; font-style: italic; font-size: 0.92rem; }
            .exp-date { font-size: 0.82rem; color: #888; }
            .exp-bullets { margin: 0.6rem 0 0 1.2rem; padding: 0; }
            .exp-bullets li { font-size: 0.92rem; line-height: 1.65; color: #444; margin-bottom: 0.3rem; }
            .skills-grid { display: flex; flex-wrap: wrap; gap: 0.4rem 1.5rem; }
            .skill-badge { font-size: 0.9rem; color: #2d2d2d; }
            .skill-badge::before { content: "• "; color: #8B4513; }
            .summary-text { font-size: 0.95rem; line-height: 1.75; color: #444; font-style: italic; }
        """,
        "minimal": """
            body { font-family: 'Helvetica Neue', Arial, sans-serif; color: #111; margin: 0; padding: 0; background: #fff; }
            .resume-wrap { max-width: 820px; margin: 0 auto; background: #fff; padding: 0; }
            .resume-header { padding: 3rem 3rem 1.5rem; border-bottom: 1px solid #e5e5e5; }
            .resume-header h1 { margin: 0 0 0.25rem; font-size: 2rem; font-weight: 700; color: #111; }
            .resume-header .headline { font-size: 1rem; color: #555; margin-bottom: 0.8rem; }
            .resume-header .contact { display: flex; gap: 1.5rem; flex-wrap: wrap; font-size: 0.82rem; color: #888; }
            .resume-body { padding: 2rem 3rem; }
            .section { margin-bottom: 2rem; }
            .section-title { font-size: 0.72rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.15em; color: #111; margin-bottom: 1rem; }
            .exp-item { margin-bottom: 1.5rem; display: grid; grid-template-columns: 1fr auto; gap: 0 1rem; }
            .exp-header { grid-column: 1 / -1; display: flex; justify-content: space-between; }
            .exp-title { font-weight: 600; font-size: 0.97rem; }
            .exp-company { color: #555; font-size: 0.9rem; }
            .exp-date { font-size: 0.82rem; color: #aaa; }
            .exp-bullets { margin: 0.5rem 0 0 1rem; padding: 0; grid-column: 1 / -1; }
            .exp-bullets li { font-size: 0.88rem; line-height: 1.6; color: #555; margin-bottom: 0.25rem; }
            .skills-grid { display: flex; flex-wrap: wrap; gap: 0.4rem; }
            .skill-badge { background: #f2f2f2; color: #333; padding: 0.25rem 0.7rem; border-radius: 4px; font-size: 0.82rem; }
            .summary-text { font-size: 0.93rem; line-height: 1.75; color: #555; }
        """,
    }.get(style, "")

    system_prompt = f"""You are a world-class professional resume writer. 
Output ONLY a valid JSON object with a single 'html' key.
The value must be a complete, self-contained HTML resume using the CSS classes defined below.

REQUIRED CSS CLASSES (already injected — DO NOT include <style> tags):
{style_css[:500]}...

REQUIRED HTML STRUCTURE:
{{
  "html": "<div class=\\"resume-wrap\\"><div class=\\"resume-header\\"><h1>Full Name</h1><p class=\\"headline\\">Target Role at Company</p><div class=\\"contact\\"><span>email@example.com</span><span>Phone</span><span>LinkedIn</span><span>City</span></div></div><div class=\\"resume-body\\"><div class=\\"section\\"><div class=\\"section-title\\">Professional Summary</div><p class=\\"summary-text\\">...</p></div><div class=\\"section\\"><div class=\\"section-title\\">Skills</div><div class=\\"skills-grid\\"><span class=\\"skill-badge\\">Skill</span>...</div></div><div class=\\"section\\"><div class=\\"section-title\\">Work Experience</div><div class=\\"exp-item\\"><div class=\\"exp-header\\"><div><div class=\\"exp-title\\">Job Title</div><div class=\\"exp-company\\">Company</div></div><span class=\\"exp-date\\">2020 – 2023</span></div><ul class=\\"exp-bullets\\"><li>Achievement 1</li></ul></div></div><div class=\\"section\\"><div class=\\"section-title\\">Education</div>...</div></div></div>"
}}

RULES:
- Extract all real details from the resume content provided (name, email, phone, education, experience, skills)
- Tailor the Professional Summary specifically to the target company and job description
- Highlight skills most relevant to the job description
- Use strong action verbs and quantified achievements in experience bullets
- DO NOT invent information not present in the resume
- Output ONLY the JSON, nothing else"""

    prompt = f"Target Company: {target_company}\nResume Content:\n{resume}\nSelf Description: {self_description}\nJob Description:\n{job_description}"

    logger.debug(f"Prompting {MODEL_NAME} for resume HTML (style={style})")
    try:
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            temperature=0.15,
        )
        content = completion.choices[0].message.content.strip()
        logger.debug(f"Raw resume response (first 300): {content[:300]}")

        data = parse_ai_json(content)
        raw_html = data.get("html", "")

        # Inject the style CSS into the returned HTML
        full_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<style>
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
{style_css}
@media print {{
  body {{ background: #fff !important; }}
  .resume-wrap {{ box-shadow: none !important; }}
}}
</style>
</head>
<body>
{raw_html}
</body>
</html>"""
        return full_html
    except Exception as e:
        logger.error(f"Failed to generate resume HTML: {e}")
        return "<html><body><h1>Error</h1><p>Could not generate resume. Please try again.</p></body></html>"


def generate_cover_letter(resume, self_description, job_description, target_company=""):
    resume = str(resume)[:8000]
    self_description = str(self_description)[:2000]
    job_description = str(job_description)[:6000]
    target_company = str(target_company)[:255]

    system_prompt = """You are a professional career coach and expert cover letter writer. 
    Output ONLY a JSON object with a 'content' field (plain text with newlines) and a 'title' field.
    The cover letter should be professional, persuasive, and tailored specifically to the company and job description."""

    prompt = f"Target Company: {target_company}\nResume: {resume}\nSelf Description: {self_description}\nJob Description: {job_description}"

    logger.debug(f"Prompting {MODEL_NAME} for cover letter")
    try:
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
        )
        content = completion.choices[0].message.content.strip()

        start = content.find("{")
        end = content.rfind("}") + 1
        if start != -1 and end > start:
            json_str = content[start:end]
            return json.loads(json_str, strict=False)
        else:
            return json.loads(content, strict=False)
    except Exception as e:
        logger.error(f"Failed to generate cover letter: {e}")
        # Try a smaller model if the versatile one fails
        try:
            logger.info("Retrying cover letter generation with llama-3.1-8b-instant")
            completion = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.7,
            )
            content = completion.choices[0].message.content.strip()
            return parse_ai_json(completion.choices[0].message.content)
        except Exception as retry_e:
            logger.error(f"Retry also failed: {retry_e}")
            return {
                "title": "Cover Letter Error",
                "content": f"AI Generation failed. Details: {str(e)}. Please check your Groq API connection.",
            }


def convert_html_to_pdf(html_content):
    result = BytesIO()
    pisa_status = pisa.CreatePDF(BytesIO(html_content.encode("utf-8")), dest=result)
    if pisa_status.err:
        return None
    return result.getvalue()


def recommend_jobs(user_profile, mastery_data):
    """
    Simulates a job matching engine using user preferences and AI analysis.
    """
    resume_skills = getattr(user_profile, "skills", "")
    city = getattr(user_profile, "city", "Remote")
    role = getattr(user_profile, "target_role", "Software Engineer")

    system_prompt = f"""You are a professional career recruiter. 
    Based on the candidate's profile and mastery, generate 3-4 realistic simulated job postings.
    Output ONLY a JSON array of objects:
    [
        {{
            "company": "...",
            "role": "...",
            "location": "...",
            "match_score": 92,
            "why": "Your mastery in React and Python fits perfectly.",
            "salary_range": "$120k - $150k",
            "job_link": "https://www.linkedin.com/jobs/view/..."
        }}
    ]"""

    prompt = f"Target Role: {role}\nLocation: {city}\nSkills: {resume_skills}\nMastery Stats: {mastery_data}"

    try:
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
        )
        content = completion.choices[0].message.content.strip()
        return parse_ai_json(completion.choices[0].message.content)
    except Exception as e:
        logger.error(f"Job recommendation failed: {e}")
        return []


def scrape_job_from_url(url):
    """
    Scrapes job details from a live URL (LinkedIn, Indeed, etc.)
    Uses Tavily Extract for smart scraping (bypasses bot protection).
    Falls back to BeautifulSoup if Tavily is not available.
    """
    # --- Tavily-powered extraction (preferred) ---
    if _tavily_client:
        try:
            logger.info(f"Using Tavily to extract content from: {url}")
            result = _tavily_client.extract(urls=[url])
            if result and result.get("results"):
                page = result["results"][0]
                raw_content = page.get("raw_content", "")

                # Use Groq to parse out structured job data from raw content
                parse_prompt = f"""From the following webpage content, extract:
1. Job Title
2. Company Name
3. Full Job Description

Return ONLY valid JSON:
{{"title": "...", "company": "...", "description": "..."}}

Content:
{raw_content[:8000]}"""

                completion = client.chat.completions.create(
                    model=MODEL_NAME,
                    messages=[
                        {
                            "role": "system",
                            "content": "You are a data extraction assistant. Output ONLY valid JSON.",
                        },
                        {"role": "user", "content": parse_prompt},
                    ],
                    temperature=0.0,
                )
                parsed = parse_ai_json(completion.choices[0].message.content or "{}")
                parsed["url"] = url
                logger.info(
                    f"Tavily extracted job: {parsed.get('title')} at {parsed.get('company')}"
                )
                return parsed
        except Exception as e:
            logger.warning(
                f"Tavily extraction failed for {url}, falling back to BeautifulSoup: {e}"
            )

    # --- BeautifulSoup fallback ---
    import requests
    from bs4 import BeautifulSoup

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
    }

    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")

        title = ""
        company = ""
        description = ""

        if "linkedin.com" in url:
            title_el = soup.find("h1") or soup.select_one(".top-card-layout__title")
            company_el = soup.select_one(".topcard__org-name-link") or soup.select_one(
                ".top-card-layout__first-subline"
            )
            desc_el = soup.select_one(".description__text") or soup.select_one(
                ".show-more-less-html__markup"
            )
            if title_el:
                title = title_el.get_text().strip()
            if company_el:
                company = company_el.get_text().strip().split("\n")[0]
            if desc_el:
                description = desc_el.get_text(separator="\n").strip()

        if not description:
            title = soup.title.string if soup.title else ""
            meta_desc = soup.find("meta", attrs={"name": "description"})
            if meta_desc:
                description = meta_desc.get("content", "")
            if not description:
                for s in soup(["script", "style", "nav", "footer"]):
                    s.decompose()
                description = soup.get_text(separator="\n")

        return {
            "title": title or "Scraped Job",
            "company": company or "Unknown Company",
            "description": (
                description[:10000] if description else "Could not extract description."
            ),
            "url": url,
        }
    except Exception as e:
        logger.error(f"Scraping failed for {url}: {e}")
        return None


def fetch_live_jobs(role, city):
    """
    Fetches real-time job listings from LinkedIn and Indeed using Tavily.
    Falls back to mock data if Tavily API key is not configured.
    """
    if _tavily_client and role:
        try:
            # Build a targeted search query for LinkedIn jobs
            location_query = f"in {city}" if city else "remote OR worldwide"
            query = (
                f"{role} job {location_query} site:linkedin.com/jobs OR site:indeed.com"
            )

            logger.info(f"Searching for live jobs: {query}")
            search_results = _tavily_client.search(
                query=query,
                search_depth="advanced",
                max_results=8,
                include_domains=["linkedin.com", "indeed.com"],
            )

            results = search_results.get("results", [])
            jobs = []

            if results:
                # Use Groq to parse/score the Tavily results into structured job cards
                results_text = json.dumps(
                    [
                        {
                            "title": r.get("title"),
                            "url": r.get("url"),
                            "snippet": r.get("content", "")[:400],
                        }
                        for r in results
                    ],
                    indent=2,
                )
                parse_prompt = f"""You are a job search assistant. I searched for '{role}' jobs in '{city}'.
Here are the raw search results:
{results_text}

For each result that is genuinely a job posting, extract and return a JSON array in this format:
[
  {{
    "company": "Actual Company Name",
    "role": "Exact Job Title",
    "location": "City or Remote",
    "match_score": 88,
    "why": "One sentence on why this role matches a {role} candidate.",
    "salary_range": "Salary if mentioned, else 'Competitive'",
    "job_link": "https://..."
  }}
]
Return ONLY valid JSON array. Skip any results that are not actual job postings."""

                completion = client.chat.completions.create(
                    model=MODEL_NAME,
                    messages=[
                        {
                            "role": "system",
                            "content": "You are a job data extraction assistant. Output ONLY a valid JSON array.",
                        },
                        {"role": "user", "content": parse_prompt},
                    ],
                    temperature=0.1,
                )
                content = completion.choices[0].message.content or "[]"
                parsed = parse_ai_json(content)
                if isinstance(parsed, list) and parsed:
                    logger.info(f"Tavily returned {len(parsed)} real job listings.")
                    return parsed[:6]  # Return top 6 results

        except Exception as e:
            logger.error(f"Tavily job search failed: {e}. Falling back to mock data.")

    # --- Fallback: Mock data (used when Tavily key not configured) ---
    logger.warning("Using mock job data. Set TAVILY_API_KEY in .env for live results.")
    import random

    base_links = [
        "https://www.linkedin.com/jobs/search/?keywords="
        + (role or "developer").replace(" ", "%20"),
        "https://www.indeed.com/jobs?q=" + (role or "developer").replace(" ", "+"),
    ]
    return [
        {
            "company": f"{city or 'Global'} Tech Hub",
            "role": f"Senior {role}",
            "location": city or "Remote",
            "match_score": random.randint(85, 98),
            "why": f"Your profile aligns well with {role} requirements.",
            "salary_range": "Competitive",
            "job_link": random.choice(base_links),
        },
        {
            "company": "Innovate AI",
            "role": f"{role} Specialist",
            "location": "Remote",
            "match_score": random.randint(78, 90),
            "why": f"Strong match for {role} tools and frameworks.",
            "salary_range": "Competitive",
            "job_link": random.choice(base_links),
        },
    ]




def analyze_star_response(question, history):
    """
    Analyzes an ongoing behavioral interview chat.
    Determines if S, T, A, R have been covered.
    Returns the next question or the final evaluation.
    """
    system_prompt = """You are an expert Behavioral Interview Coach.
    You are guiding a candidate through a behavioral question using the STAR method.
    You must evaluate the conversation history to determine which parts of STAR are missing.
    
    If S, T, A, or R is missing or weak, ask a follow-up question specifically targeting that missing piece. 
    Be conversational but brief.
    
    If they have sufficiently covered all four parts (Situation, Task, Action, Result), conclude the interview and provide a final evaluation.
    
    Output ONLY a valid JSON object in this exact format:
    {
        "reply": "That's a great situation. What specific actions did YOU take to resolve it?",
        "is_complete": false,
        "score": 0.0,
        "feedback": "Covered Situation well, but needs Action.",
        "strengths": [],
        "improvements": []
    }
    
    If the interview is complete, `is_complete` MUST be true, `score` should be out of 10, and provide final feedback, strengths, and improvements.
    """

    user_prompt = f"Question: {question}\n\nChat History:\n{json.dumps(history, indent=2)}"

    try:
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3, # Slightly conversational
        )
        content = completion.choices[0].message.content or "{}"
        return parse_ai_json(content)
    except Exception as e:
        logger.error(f"STAR Evaluation failed: {e}")
        return {
            "reply": "I'm having trouble analyzing that. Could you elaborate?",
            "is_complete": False,
            "score": 0.0,
            "feedback": str(e),
            "strengths": [],
            "improvements": []
        }


def generate_mega_interview(resume_text, experience_level):
    """
    Generates a full "Mega Interview" JSON structure based on the user's resume and experience level.
    """
    resume = str(resume_text)[:8000]
    exp = str(experience_level)[:50]

    system_prompt = f"""You are an expert technical interviewer creating a comprehensive "Mega Interview".
The candidate has '{exp}' experience.
Based entirely on their resume, generate a JSON object with exactly:
- 3 HR/Behavioral questions
- 3 Technical questions
- Coding questions: 1 primary challenging question and 1-2 simpler questions appropriate for their experience.

Output ONLY a valid JSON object matching this exact schema:
{{
  "hr_questions": [
    {{
      "id": "hr_1",
      "type": "hr",
      "question": "Tell me about..."
    }}
  ],
  "tech_questions": [
    {{
      "id": "tech_1",
      "type": "technical",
      "question": "How did you implement..."
    }}
  ],
  "coding_questions": [
    {{
      "id": "code_1",
      "type": "coding",
      "question": "Write a function to...",
      "boilerplate": "def solve():\\n    pass"
    }}
  ]
}}
Do NOT output anything other than the JSON."""

    prompt = f"Candidate Resume:\n{resume}"

    try:
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
        )
        content = completion.choices[0].message.content or "{}"
        return parse_ai_json(content)
    except Exception as e:
        logger.error(f"Mega Interview generation failed: {e}")
        return {
            "hr_questions": [],
            "tech_questions": [],
            "coding_questions": [],
            "error": "Failed to generate interview."
        }

def evaluate_mega_interview(questions_data, answers_data):
    """
    Evaluates all submitted answers for a Mega Interview and returns a comprehensive review and topics to learn.
    """
    system_prompt = """You are an expert technical interviewer evaluating a full candidate interview.
You will receive the interview questions and the candidate's answers.
Evaluate the answers for correctness, communication, and technical depth.
Identify their weaknesses and generate a list of "Topics to Learn" to help them improve.

Output ONLY a valid JSON object matching this exact schema:
{{
  "overall_score": 8.5,
  "summary": "Overall good performance, but needs work on...",
  "question_evaluations": [
    {{
      "question_id": "hr_1",
      "score": 8.0,
      "feedback": "Good answer, clearly formatted."
    }}
  ],
  "topics_to_learn": [
    {{
      "topic": "System Design",
      "reason": "You struggled with scaling questions."
    }}
  ]
}}
Do NOT output anything other than the JSON."""

    prompt = f"Questions:\n{json.dumps(questions_data)}\n\nAnswers:\n{json.dumps(answers_data)}"

    try:
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
        )
        content = completion.choices[0].message.content or "{}"
        return parse_ai_json(content)
    except Exception as e:
        logger.error(f"Mega Interview evaluation failed: {e}")
        return {
            "overall_score": 0,
            "summary": "Evaluation failed due to an error.",
            "question_evaluations": [],
            "topics_to_learn": []
        }

def generate_career_roadmap(user_profile, reports, selected_level=None, selected_focus=None, timeline_pref=None):
    """
    Synthesizes user profile and past interview reports into a career roadmap.
    Now supports custom manual selections for level, focus areas, and timeline.
    """
    role = user_profile.target_role or "Software Engineer"
    experience = selected_level or user_profile.experience_level or "Fresher"
    skills = user_profile.skills or ""
    focus_areas = selected_focus or "General Tech Stack"
    timeline = timeline_pref or "3 Months"

    # Aggregate skill gaps from reports as secondary context
    all_gaps = []
    for r in reports:
        for gap in r.skill_gaps:
            all_gaps.append(gap.get("skill", ""))
    unique_gaps = list(set([g for g in all_gaps if g]))

    system_prompt = f"""You are an elite career strategist and tech mentor. 
    Create a highly detailed, binary-perfect career roadmap for a {role}.
    The user is targeting the {experience} level and wants to focus specifically on: {focus_areas}.
    The desired timeline for this roadmap is {timeline}.
    
    Output ONLY a JSON object:
    {{
        "title": "Roadmap to {role} ({experience})",
        "focus": "{focus_areas}",
        "timeline": "{timeline}",
        "milestones": [
            {{
                "id": 1,
                "title": "Phase 1: ...",
                "estimated_time": "...",
                "status": "current",
                "objectives": ["...", "..."],
                "next_steps": ["...", "..."]
            }}
        ]
    }}
    Provide exactly 4-5 progressive milestones.
    Status for first is "current", others "locked".
    Integrate these previously identified gaps if they fit the focus: {unique_gaps}
    """

    prompt = f"Current Skills: {skills}\nTarget Role: {role}\nPrimary Focus: {focus_areas}\nTimeline: {timeline}"

    try:
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
        )
        content = completion.choices[0].message.content or "{}"
        return parse_ai_json(content)
    except Exception as e:
        logger.error(f"Roadmap generation failed: {e}")
        return {
            "title": f"My Roadmap to {role}",
            "milestones": [
                {
                    "id": 1,
                    "title": "Foundations",
                    "estimated_time": "1 Month",
                    "status": "current",
                    "objectives": ["Master core language syntax", "Build 1 portfolio project"],
                    "next_steps": ["Review official docs", "Push code to GitHub"]
                },
                {
                    "id": 2,
                    "title": "Advanced Mastery",
                    "estimated_time": "2 Months",
                    "status": "locked",
                    "objectives": ["Learn system design basics", "Solve 50 coding problems"],
                    "next_steps": ["Start LeetCode", "Read Design Patterns book"]
                }
            ]
        }


# Interview AI: Enterprise-Grade Career Intelligence Platform

Transform your job search with the power of AI. **Interview AI** is an all-in-one career preparation platform designed to help you land your dream job at top-tier companies. Built with a focus on high-impact results using 100% free and open-source technologies.

---

## 🚀 Key Features

### 1. 📊 Mastery Analytics Dashboard
Gain deep insights into your interview readiness.
- **Performance Trends**: Track your growth over time with interactive charts.
- **Skill Gap Discovery**: Automatically identify recurring technical and behavioral weaknesses.
- **Preparation Roadmaps**: Get a personalized day-by-day plan to bridge your skill gaps.

### 2. 🎤 AI Voice Interviewer & Mega Interview
The most realistic mock interview experience available in your browser.
- **Mega Interview Mode**: A full-screen, immersive simulation with strict anti-cheat measures and automatic evaluation.
- **AI-Powered Speech**: The platform reads interview questions aloud to simulate a real conversation.
- **Voice Transcription**: Speak your answers directly into the microphone; our AI transcribes them in real-time.
- **Comprehensive Feedback**: Receive instant scores (0-10) and deep semantic analysis on your performance.

### 3. ⭐ STAR Behavioral Coach
Master the STAR (Situation, Task, Action, Result) method with interactive coaching.
- **Interactive Chat**: Guidance on structuring your behavioral stories according to enterprise standards.
- **Real-Time Tracker**: Visual S.T.A.R. tracker highlights which components of your story are complete as you speak/type.
- **Score & Evaluation**: Get a final score and breakdown of how well you applied each STAR component.

### 4. 📄 Resume-Driven RAG Pipeline
Context-aware interview generation based on your actual experience.
- **PDF Extraction**: Upload your resume and automatically extract high-quality text using `pdfplumber`.
- **RAG Integration**: The AI heavily personalizes technical and behavioral questions by referencing your past projects, skills, and companies directly from your resume.

### 5. 📉 ATS Score Predictor (ML Powered)
Validate your resume against job descriptions using real-world Applicant Tracking System (ATS) methodologies.
- **Keyword Matching**: Scikit-Learn TF-IDF calculates exact keyword density matching.
- **NLP Extraction**: SpaCy intelligently extracts core nouns and entities.
- **Semantic Analysis**: Hugging Face Sentence Transformers provide deep semantic analysis to understand the contextual meaning of your experience versus requirements.

### 6. ✍️ Technical Whiteboard
Practice your coding skills with specialized evaluation.
- **In-Browser Editor**: Write code directly in a clean, professional interface.
- **AI Evaluation**: Get your code reviewed for logic, efficiency, and edge cases.

### 7. 🔗 Job Matcher & Roadmap
- **Live Job Scraping**: Find and analyze jobs directly from URLs.
- **Career Roadmap**: Dynamic generation of a personalized career path based on your current skills and target goals.

---

## 🛠️ Technology Stack
- **Backend**: Django (Python)
- **AI Engine**: Groq (Llama 3.3 70B & Llama 3.1 8B)
- **Machine Learning**: `scikit-learn` (TF-IDF), `spaCy` (NLP), `sentence-transformers` (Hugging Face)
- **Frontend**: Vanilla HTML5, CSS3 (Premium Glassmorphism), GSAP (Animations), VanillaTilt (3D Effects)
- **Voice**: Web Speech API (Recognition & Synthesis)
- **Data Viz**: Chart.js
- **PDF Processing**: `pdfplumber`, `xhtml2pdf`

---

## 🏗️ Getting Started

1. **Setup Environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Download NLP Models**:
   ```bash
   python -m spacy download en_core_web_sm
   ```

3. **Configure API Keys**:
   Create a `.env` file in the `python/` directory:
   ```env
   GROQ_API_KEY=your_free_groq_key_here
   ```

4. **Run Application**:
   ```bash
   python manage.py migrate
   python manage.py runserver
   ```

---

## 🌟 Why Interview AI?
- **Privacy First**: Your sessions and data are handled securely and remain within your control.
- **Free & Open Source**: Uses high-performance, open-source AI models via free API tiers.
- **Premium UX**: Advanced diagonal slice transitions, persistent dark mode, and buttery-smooth micro-animations.

---
*Developed for ambitious candidates looking to ace their next big tech interview.*

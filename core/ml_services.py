import logging
import spacy
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer

logger = logging.getLogger("core")

# Load NLP models lazy to prevent heavy memory usage on import
_nlp = None
_sentence_model = None

def get_spacy_nlp():
    global _nlp
    if _nlp is None:
        try:
            logger.info("Loading spaCy model 'en_core_web_sm'...")
            _nlp = spacy.load("en_core_web_sm")
        except Exception as e:
            logger.error(f"Failed to load spaCy model: {e}")
            raise RuntimeError("Please ensure 'en_core_web_sm' is downloaded.")
    return _nlp

def get_sentence_model():
    global _sentence_model
    if _sentence_model is None:
        try:
            logger.info("Loading sentence-transformer 'all-MiniLM-L6-v2'...")
            _sentence_model = SentenceTransformer('all-MiniLM-L6-v2')
        except Exception as e:
            logger.error(f"Failed to load sentence-transformer: {e}")
            raise
    return _sentence_model

def extract_keywords(text):
    """
    Extracts meaningful keywords (nouns, propns, and key entities) from text using spaCy.
    """
    if not text or not text.strip():
        return set()
        
    nlp = get_spacy_nlp()
    doc = nlp(text.lower())
    
    keywords = set()
    for token in doc:
        # Keep NOUNs and PROPNs (Proper Nouns) that aren't stop words
        if token.pos_ in ["NOUN", "PROPN"] and not token.is_stop and token.is_alpha:
            keywords.add(token.lemma_)
            
    # Also extract entities like "Machine Learning", "Python" which might span multiple words
    for ent in doc.ents:
        if ent.label_ not in ["DATE", "TIME", "PERCENT", "MONEY", "QUANTITY", "ORDINAL", "CARDINAL"]:
            # Clean and add multi-word entities
            clean_ent = " ".join([t.lemma_ for t in ent if not t.is_stop and t.is_alpha])
            if clean_ent:
                keywords.add(clean_ent)
                
    return keywords

def calculate_ats_score(resume_text, job_description_text):
    """
    Predicts an ATS pass score and returns matching/missing keywords 
    between a Resume and a Job Description.
    """
    if not resume_text or not job_description_text:
        return {
            "score": 0,
            "matching_keywords": [],
            "missing_keywords": ["No resume or JD provided"]
        }
        
    # 1. Keyword Extraction & Gap Analysis
    resume_keywords = extract_keywords(resume_text)
    jd_keywords = extract_keywords(job_description_text)
    
    matching_kws = list(jd_keywords.intersection(resume_keywords))
    missing_kws = list(jd_keywords.difference(resume_keywords))
    
    # Calculate Keyword Match %
    if not jd_keywords:
        keyword_score = 100.0
    else:
        keyword_score = (len(matching_kws) / len(jd_keywords)) * 100.0

    # 2. TF-IDF Exact Keyword Density Similarity
    tfidf_score = 0.0
    try:
        vectorizer = TfidfVectorizer(stop_words='english')
        tfidf_matrix = vectorizer.fit_transform([job_description_text, resume_text])
        cosine_sim = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])
        tfidf_score = cosine_sim[0][0] * 100.0
    except Exception as e:
        logger.warning(f"TF-IDF calculation failed: {e}")
        
    # 3. Semantic Similarity (Hugging Face sentence-transformers for contextual meaning)
    semantic_score = 0.0
    try:
        model = get_sentence_model()
        embeddings = model.encode([job_description_text, resume_text])
        sem_cosine_sim = cosine_similarity([embeddings[0]], [embeddings[1]])
        semantic_score = sem_cosine_sim[0][0] * 100.0
        # Sentence Transformers can sometimes output slightly < 0 if perfectly orthogonal
        semantic_score = max(0.0, min(100.0, semantic_score))
    except Exception as e:
        logger.warning(f"Semantic similarity calculation failed: {e}")
        
    # 4. Final Weighted Score
    # Real ATS systems heavily bias exact keyword matching via TF-IDF, but modern ones use Semantic
    # We blend them: 30% Keyword Match, 30% TF-IDF Density, 40% Deep Semantic Understanding
    final_score = (keyword_score * 0.3) + (tfidf_score * 0.3) + (semantic_score * 0.4)
    final_score_rounded = min(100, max(0, int(round(final_score))))
    
    # Sort keywords by length/importance roughly to show best ones first
    matching_kws = sorted(matching_kws, key=len, reverse=True)[:15]
    missing_kws = sorted(missing_kws, key=len, reverse=True)[:15]

    return {
        "score": final_score_rounded,
        "matching_keywords": matching_kws,
        "missing_keywords": missing_kws
    }

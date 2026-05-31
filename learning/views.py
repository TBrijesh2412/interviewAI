from django.shortcuts import render, get_object_or_404
from django.db.models import Q
from .models import Subject, Topic, Article
import markdown


def learning_home(request):
    """View to list all available subjects."""
    subjects = Subject.objects.all()
    return render(request, 'learning/home.html', {'subjects': subjects})


def subject_detail(request, subject_slug):
    """View to display the roadmap/topics for a specific subject."""
    subject = get_object_or_404(Subject, slug=subject_slug)
    # We will pass all topics with their related articles
    topics = subject.topics.all().prefetch_related('articles')
    
    # Optional: fetch the first article of the first topic as the default landing
    first_article = None
    first_topic = topics.first()
    if first_topic:
        first_article = first_topic.articles.first()
        
    return render(request, 'learning/subject.html', {
        'subject': subject,
        'topics': topics,
        'first_article': first_article
    })


def article_detail(request, subject_slug, topic_slug, article_slug):
    """View to display the specific article content, converting Markdown."""
    subject = get_object_or_404(Subject, slug=subject_slug)
    topic = get_object_or_404(Topic, subject=subject, slug=topic_slug)
    article = get_object_or_404(Article, topic=topic, slug=article_slug)
    
    # Process markdown to HTML. Using 'fenced_code' for code blocks
    article_html = markdown.markdown(
        article.content,
        extensions=['fenced_code', 'codehilite', 'tables', 'toc']
    )
    
    # Get all topics for the sidebar
    topics = subject.topics.all().prefetch_related('articles')
    
    return render(request, 'learning/article.html', {
        'subject': subject,
        'topic': topic,
        'article': article,
        'article_html': article_html,
        'topics': topics
    })


def learning_search(request):
    """View to handle global search for articles in the learning section."""
    query = request.GET.get('q', '')
    results = []
    
    if query:
        # Search by article title or content
        results = Article.objects.filter(
            Q(title__icontains=query) | Q(content__icontains=query)
        ).select_related('topic__subject').order_by('-created_at')
        
    return render(request, 'learning/search.html', {
        'query': query,
        'results': results
    })

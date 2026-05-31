import os
import json
import logging
from django.core.management.base import BaseCommand
from django.utils.text import slugify
from learning.models import Subject, Topic, Article

try:
    from groq import Groq
except ImportError:
    Groq = None

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Generates 0-100 structured learning content using Groq AI'

    def add_arguments(self, parser):
        parser.add_argument('--subject', type=str, required=True, help='The subject to generate (e.g., "Python", "System Design")')
        parser.add_argument('--topics-count', type=int, default=5, help='Number of topics to generate')

    def handle(self, *args, **kwargs):
        if not Groq:
            self.stdout.write(self.style.ERROR("Groq library not found. Please install with: pip install groq"))
            return

        subject_name = kwargs['subject']
        topics_count = kwargs['topics_count']

        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            self.stdout.write(self.style.ERROR("GROQ_API_KEY environment variable is not set. Please check your .env file."))
            return

        client = Groq(api_key=api_key)
        self.stdout.write(self.style.SUCCESS(f"Starting auto-generation for {subject_name}..."))

        # 1. Create or get the Subject
        subject, created = Subject.objects.get_or_create(
            name=subject_name,
            defaults={
                'slug': slugify(subject_name),
                'description': f"A comprehensive A-Z guide for mastering {subject_name}."
            }
        )
        if created:
             self.stdout.write(f"Created Subject: {subject.name}")

        # 2. Ask Groq for an array of Topics
        topics_prompt = f"""
        You are an expert tech educator. I am building a GeeksforGeeks-style tutorial site.
        Generate a logical learning path for mastering '{subject_name}' from zero to advanced.
        Provide EXACTLY {topics_count} modules/topics in logical order.
        Return ONLY a raw JSON array of strings. No markdown, no backticks, no explanations. 
        Example format: ["Introduction", "Variables & Data Types", "Control Flow", "Object Oriented Concepts", "Advanced Concepts"]
        """

        self.stdout.write("Requesting Topic Outline from AI...")
        response_text = ""
        try:
             chat_completion = client.chat.completions.create(
                messages=[{"role": "user", "content": topics_prompt}],
                model="llama-3.1-8b-instant",
                temperature=0.3,
             )
             
             response_text = chat_completion.choices[0].message.content.strip()
             # Cleanup potential markdown ticks if AI decides to ignore instructions
             if response_text.startswith("```json"):
                 response_text = response_text[7:]
             if response_text.endswith("```"):
                 response_text = response_text[:-3]
             
             topics_list = json.loads(response_text)
             if not isinstance(topics_list, list):
                 raise ValueError("AI did not return a JSON array.")

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Failed to parse topics from AI: {e} | Raw Response: {response_text}"))
            return

        self.stdout.write(self.style.SUCCESS(f"Successfully generated {len(topics_list)} topics!"))

        # 3. For each topic, ask Groq to write the detailed Article
        for i, topic_title in enumerate(topics_list, start=1):
            self.stdout.write(f"[{i}/{len(topics_list)}] Generating content for topic '{topic_title}'...")

            topic, t_created = Topic.objects.get_or_create(
                subject=subject,
                title=topic_title,
                defaults={
                    'slug': slugify(topic_title)[:200], # ensure fits in DB
                    'order': i
                }
            )

            article_prompt = f"""
            Write an incredibly detailed, comprehensive, GeeksforGeeks-style technical article for the topic '{topic_title}' within the larger subject '{subject_name}'.
            
            Requirements:
            - Write in Markdown format.
            - Start with a clear H1 (#) title.
            - Include deep explanations, best practices, and real-world importance.
            - Use multiple H2 (##) and H3 (###) subheadings to break down the concept.
            - Provide clear, well-commented code examples enclosed in standard markdown code blocks (e.g., ```python) for ALL technical concepts discussed.
            - Minimum length should be around 600-1000 words. Make it authoritative and deep.
            
            Return ONLY the valid raw Markdown text. No leading conversational text like "Here is the article".
            """

            try:
                article_completion = client.chat.completions.create(
                    messages=[{"role": "user", "content": article_prompt}],
                    model="llama-3.3-70b-versatile", # Deep context model
                    temperature=0.5,
                )
                markdown_content = article_completion.choices[0].message.content.strip()

                Article.objects.get_or_create(
                    topic=topic,
                    title=f"{topic_title} - Deep Dive",
                    defaults={
                        'slug': slugify(f"{subject_name} {topic_title} deep dive")[:255],
                        'content': markdown_content,
                        'order': 1
                    }
                )
                self.stdout.write(self.style.SUCCESS(f"  -> Saved article for '{topic_title}'"))

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  -> Failed generating article for '{topic_title}': {e}"))

        self.stdout.write(self.style.SUCCESS(f"\nGeneration complete! Run the server and check /learn/"))

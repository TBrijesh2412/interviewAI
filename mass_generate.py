import os
import django
import sys
from django.core.management import call_command

# Initialize Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'interview_ai.settings')
django.setup()

subjects = [
    "Python Programming",
    "Advanced Python",
    "Python for Data Science",
    "Python for Web Development",
    "Python Automation",
    "Java Programming",
    "Advanced Java",
    "Spring Boot Development",
    "Java Multithreading",
    "Java Performance Optimization",
    "C Programming",
    "Advanced C Programming",
    "C++ Programming",
    "Advanced C++",
    "Rust Programming",
    "Go Programming",
    "Swift Programming",
    "Kotlin Programming",
    "C# Programming",
    "Scala Programming",
    "TypeScript Programming",
    "JavaScript Programming",
    "Advanced JavaScript",
    "Frontend Development",
    "Backend Development",
    "Fullstack Development",
    "HTML Complete Guide",
    "Advanced HTML",
    "CSS Complete Guide",
    "Advanced CSS",
    "Responsive Web Design",
    "Web Performance Optimization",
    "REST API Development",
    "GraphQL APIs",
    "Progressive Web Apps",
    "React Development",
    "Advanced React",
    "React Hooks",
    "Next.js Framework",
    "Angular Framework",
    "Vue.js Framework",
    "Svelte Framework",
    "Tailwind CSS",
    "Bootstrap Framework",
    "Redux State Management",
    "Node.js Backend Development",
    "Express.js Framework",
    "Django Backend Development",
    "Flask Web Framework",
    "Ruby on Rails",
    "Laravel PHP Framework",
    "ASP.NET Core",
    "Microservices Architecture",
    "API Gateway Design",
    "Authentication Systems",
    "Authorization Systems",
    "System Design Fundamentals",
    "Scalable System Design",
    "Distributed Systems",
    "Load Balancing",
    "Caching Systems",
    "Message Queues",
    "Database Design",
    "SQL Database",
    "Advanced SQL",
    "MySQL Database",
    "PostgreSQL Database",
    "MongoDB Database",
    "NoSQL Databases",
    "Redis Caching",
    "Graph Databases",
    "Database Optimization",
    "Data Structures",
    "Arrays",
    "Linked Lists",
    "Stacks",
    "Queues",
    "Hash Tables",
    "Trees",
    "Binary Trees",
    "Binary Search Trees",
    "Graphs",
    "Heaps",
    "Algorithms",
    "Sorting Algorithms",
    "Searching Algorithms",
    "Graph Algorithms",
    "Dynamic Programming",
    "Greedy Algorithms",
    "Backtracking Algorithms",
    "Bit Manipulation",
    "String Algorithms",
    "Machine Learning",
    "Deep Learning",
    "Neural Networks",
    "Natural Language Processing",
    "Computer Vision",
    "Reinforcement Learning",
    "AI Fundamentals",
    "AI Model Deployment",
    "Data Science",
    "Data Analysis",
    "Data Visualization",
    "Big Data Processing",
    "Apache Spark",
    "Apache Hadoop",
    "Feature Engineering",
    "Time Series Analysis",
    "Cybersecurity Fundamentals",
    "Network Security",
    "Application Security",
    "Ethical Hacking",
    "Penetration Testing",
    "Cryptography",
    "Malware Analysis",
    "Security Incident Response",
    "Operating Systems",
    "Computer Networks",
    "Compiler Design",
    "Software Engineering",
    "Object Oriented Programming",
    "Functional Programming",
    "Parallel Computing",
    "Distributed Computing",
    "Android Development",
    "iOS Development",
    "Flutter Development",
    "React Native Development",
    "Mobile App Architecture",
    "Unity Game Development",
    "Unreal Engine",
    "2D Game Development",
    "3D Game Development",
    "Game AI",
    "Docker Containerization",
    "Kubernetes Orchestration",
    "CI CD Pipelines",
    "DevOps Fundamentals",
    "Infrastructure as Code",
    "Linux Server Administration",
    "Server Monitoring",
    "Cloud Computing",
    "AWS Cloud Services",
    "Azure Cloud",
    "Google Cloud Platform",
    "Serverless Computing",
    "Cloud Architecture",
    "Cloud Security",
    "Cloud Networking"
]

import time

def generate_mass_content():
    print(f"Starting mass content generation for {len(subjects)} subjects...")
    print("WARNING: This will take a significant amount of time and use API credits.")
    
    success_count = 0
    fail_count = 0
    
    for idx, subject in enumerate(subjects, 1):
        print(f"\n========================================================")
        print(f"Processing ({idx}/{len(subjects)}): {subject}")
        print(f"========================================================")
        
        retries = 3
        while retries > 0:
            try:
                # Call the custom management command we built earlier
                call_command('generate_learning_content', subject=subject, topics_count=5)
                success_count += 1
                break # break out of retry loop on success
            except Exception as e:
                error_msg = str(e)
                print(f"Failed to generate content for {subject}.")
                if "429" in error_msg or "rate limit" in error_msg.lower():
                    # 1 minute 40s is usually 100 seconds to be safe
                    delay = 120 
                    print(f"Rate limit hit! Sleeping for {delay} seconds before retrying...")
                    time.sleep(delay)
                    retries -= 1
                else:
                    print(f"Error: {e}")
                    fail_count += 1
                    break # break out on persistent non-rate limit failures
            
    print("\n\n================ MASS GENERATION COMPLETE ================")
    print(f"Successfully generated: {success_count}/{len(subjects)}")
    print(f"Failed: {fail_count}/{len(subjects)}")

if __name__ == "__main__":
    # Allow passing an index to resume if it crashes halfway
    start_idx = 0
    if len(sys.argv) > 1:
        try:
            start_idx = int(sys.argv[1])
            subjects = subjects[start_idx:]
            print(f"Resuming from index {start_idx} (Subject: {subjects[0] if subjects else 'None'})")
        except ValueError:
            pass

    generate_mass_content()

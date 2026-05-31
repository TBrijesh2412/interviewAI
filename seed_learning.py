import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'interview_ai.settings')
django.setup()

from learning.models import Subject, Topic, Article
from django.utils.text import slugify

def seed_learning_data():
    print("Seeding Learning Data...")

    # Python Subject
    python, _ = Subject.objects.get_or_create(
        name="Python",
        slug="python",
        description="Learn Python Programming from scratch to advanced level.",
        order=1
    )

    # Topics for Python
    intro_topic, _ = Topic.objects.get_or_create(
        subject=python, 
        title="Introduction", 
        slug="introduction", 
        order=1
    )
    
    oops_topic, _ = Topic.objects.get_or_create(
        subject=python, 
        title="Object Oriented Programming", 
        slug="oop", 
        order=2
    )

    # Articles
    Article.objects.get_or_create(
        topic=intro_topic,
        title="Getting Started with Python",
        slug="getting-started",
        defaults={
            "content": """
# What is Python?
Python is a high-level, interpreted string object-oriented programming language.
It is widely used in data science, web development, and artificial intelligence.

## Hello World
Here is how you write a simple Hello World in Python:
```python
print("Hello, World!")
```

### Why use Python?
- **Readable Syntax**: Very clean code structure
- **Vast Libraries**: Rich ecosystem
""",
            "order": 1
        }
    )

    Article.objects.get_or_create(
        topic=oops_topic,
        title="Classes and Objects",
        slug="classes-objects",
        defaults={
            "content": """
# Object-Oriented Programming in Python

Classes define the blueprint for objects. They contain properties (variables) and methods (functions).

## Creating a Class
```python
class Animal:
    def __init__(self, name):
        self.name = name

    def speak(self):
        print(f"{self.name} makes a sound.")
        
dog = Animal("Buddy")
dog.speak()
```
""",
            "order": 1
        }
    )

    # Java Subject
    java, _ = Subject.objects.get_or_create(
        name="Java",
        slug="java",
        description="Master Java for enterprise applications and Android development.",
        order=2
    )
    
    java_intro, _ = Topic.objects.get_or_create(
        subject=java, 
        title="Java Basics", 
        slug="java-basics", 
        order=1
    )
    
    Article.objects.get_or_create(
        topic=java_intro,
        title="Java Hello World",
        slug="java-hello-world",
        defaults={
            "content": """
# Getting Started with Java
Java is a strongly typed object-oriented language.

```java
public class HelloWorld {
    public static void main(String[] args) {
        System.out.println("Hello, Java!");
    }
}
```
""",
            "order": 1
        }
    )

    print("Seeding Complete!")

if __name__ == "__main__":
    seed_learning_data()

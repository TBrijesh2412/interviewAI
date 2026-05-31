import os
import glob

directory = r'C:\Users\brije\OneDrive\Desktop\PROJECT_INTERVIEW ai\templates'
html_files = glob.glob(os.path.join(directory, '**', '*.html'), recursive=True)

for file_path in html_files:
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Simple replacement for all the known offenders
    new_content = content.replace('background-image: var(--card-pattern);', '')
    new_content = new_content.replace('--card-pattern: url("{% static \'core/images/Shape_main.svg\' %}");', '')
    
    if new_content != content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"Cleaned {file_path}")
print("Cleanup complete.")

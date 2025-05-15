from flask import Flask, render_template
import os

app = Flask(__name__)

def get_level_content(level_number):
    level_file_path = os.path.join('levels', f'level{level_number}.txt')
    try:
        with open(level_file_path, 'r') as f:
            return f.read()
    except FileNotFoundError:
        return "Level content not found."

@app.route('/')
def index():
    current_level = 1 # For now, always level 1
    level_content = get_level_content(current_level)
    return render_template('index.html', level_content=level_content, current_level=current_level)

if __name__ == '__main__':
    app.run(debug=True) 
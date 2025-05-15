from flask import Flask, render_template
import os
import re

app = Flask(__name__)


def parse_level_content(level_number):
    """Return objective text and code text for the given level number."""
    level_file_path = os.path.join('levels', f'level{level_number}.txt')
    objective_lines = []
    code_lines = []
    current_section = None

    if not os.path.exists(level_file_path):
        return "Objective not found.", "Code not found."

    with open(level_file_path, 'r') as f:
        for raw_line in f:
            line = raw_line.rstrip('\n')
            stripped = line.strip()

            # Detect section starts
            if stripped.upper() == "<OBJECTIVE>":
                current_section = "objective"
                continue
            elif stripped.upper() in ("</OBJECTIVE>", "<\\OBJECTIVE>", "<\\OBJECTIVE>"):  # handle different closing formats
                current_section = None
                continue
            elif stripped.upper() == "<CODE>":
                current_section = "code"
                continue
            elif stripped.upper() in ("</CODE>", "<\\CODE>", "<\\CODE>"):
                current_section = None
                continue

            # Collect lines for current section
            if current_section == "objective":
                objective_lines.append(line)
            elif current_section == "code":
                code_lines.append(line)

    objective_text = "\n".join(objective_lines).strip()
    code_text = "\n".join(code_lines).strip()
    return objective_text, code_text


@app.route('/')
def index():
    current_level = 1  # For now, always level 1
    objective, code = parse_level_content(current_level)
    return render_template(
        'index.html',
        current_level=current_level,
        objective=objective,
        code=code
    )


if __name__ == '__main__':
    app.run(debug=True) 
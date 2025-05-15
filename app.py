import os
import re
import glob

from flask import Flask, jsonify, render_template, request

import claude
from voice import AudioRecorder

app = Flask(__name__)

# Instantiate the recorder globally
# This is a simplification. For production, you might manage this differently
# (e.g., per-user sessions if multiple users could record simultaneously).
recorder = AudioRecorder()


def get_total_levels():
    """Counts the number of level files in the 'levels' directory."""
    level_files = glob.glob(os.path.join("levels", "level*.txt"))
    return len(level_files)


def parse_level_content(level_number):
    """Return objective text and code text for the given level number."""
    level_file_path = os.path.join("levels", f"level{level_number}.txt")
    objective_lines = []
    code_lines = []
    current_section = None

    if not os.path.exists(level_file_path):
        return "Objective not found.", "Code not found."

    with open(level_file_path, "r") as f:
        for raw_line in f:
            line = raw_line.rstrip("\n")
            stripped = line.strip()

            # Detect section starts
            if stripped.upper() == "<OBJECTIVE>":
                current_section = "objective"
                continue
            elif stripped.upper() in (
                "</OBJECTIVE>",
                "<\\OBJECTIVE>",
                "<\\OBJECTIVE>",
            ):  # handle different closing formats
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


@app.route("/")
def index():
    current_level = 1  # Default to level 1
    total_levels = get_total_levels()
    objective, code = parse_level_content(current_level)
    return render_template("index.html", current_level=current_level, objective=objective, code=code, total_levels=total_levels)


@app.route("/get_level/<int:level_number>")
def get_level_route(level_number):
    objective, code = parse_level_content(level_number)
    if objective == "Objective not found." and code == "Code not found.":
        return jsonify({"status": "error", "message": "Level not found"}), 404
    return jsonify({"status": "success", "objective": objective, "code": code, "current_level": level_number})


@app.route("/start_record", methods=["POST"])
def start_record_route():
    try:
        recorder.start_recording()
        return jsonify({"status": "success", "message": "Recording started"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/stop_record", methods=["POST"])
def stop_record_route():
    try:
        result = recorder.stop_recording()
        if result and hasattr(result, "text"):
            transcription_text = result.text
            return jsonify({"status": "success", "transcription_text": transcription_text})
        elif result:
            # If result is not None but doesn't have .text, it's an unexpected format
            print(f"Unexpected result format: {type(result)} - {result}")
            return jsonify({"status": "error", "message": "Transcription format unexpected."}), 500
        else:
            return jsonify({"status": "success", "message": "No audio data recorded or transcription failed"})
    except Exception as e:
        print(f"Error in /stop_record: {e}")  # Log the full error on the server
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/ai_modify_code", methods=["POST"])
def ai_modify_code_route():
    try:
        data = request.get_json()
        current_code = data.get("current_code")
        transcription = data.get("transcription")

        if not current_code or not transcription:
            return jsonify({"status": "error", "message": "Missing current_code or transcription"}), 400

        print(f"Calling Claude with code:\n{current_code}\nInstruction: {transcription}")
        modified_code = claude.generate_modified_code(current_code, transcription)
        print(f"Claude returned modified code:\n{modified_code}")

        return jsonify({"status": "success", "modified_code": modified_code})
    except Exception as e:
        print(f"Error in /ai_modify_code: {e}")
        return jsonify({"status": "error", "message": f"Error processing with AI: {str(e)}"}), 500


if __name__ == "__main__":
    app.run(debug=True)

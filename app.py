import glob
import os
import re
import subprocess
import sys
import tempfile

from flask import Flask, jsonify, render_template, request

import claude
from file_runner import process_level_file, write_and_run
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
    """Return objective text, code text, and testing text for the given level number."""
    level_file_path = os.path.join("levels", f"level{level_number}.txt")
    objective_lines = []
    code_lines = []
    testing_lines = []
    current_section = None

    if not os.path.exists(level_file_path):
        return "Objective not found.", "Code not found.", "Testing not found."

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
            ):
                current_section = None
                continue
            elif stripped.upper() == "<CODE>":
                current_section = "code"
                continue
            elif stripped.upper() in ("</CODE>", "<\\CODE>", "<\\CODE>"):
                current_section = None
                continue
            elif stripped.upper() == "<TESTING>":
                current_section = "testing"
                continue
            elif stripped.upper() in ("</TESTING>", "<\\TESTING>", "<\\TESTING>"):
                current_section = None
                continue

            # Collect lines for current section
            if current_section == "objective":
                objective_lines.append(line)
            elif current_section == "code":
                code_lines.append(line)
            elif current_section == "testing":
                testing_lines.append(line)

    objective_text = "\n".join(objective_lines).strip()
    code_text = "\n".join(code_lines).strip()
    testing_text = "\n".join(testing_lines).strip()
    return objective_text, code_text, testing_text


@app.route("/")
def index():
    current_level = request.args.get("level", "1")
    objective, code, testing = parse_level_content(current_level)
    total_levels = get_total_levels()
    return render_template(
        "index.html",
        current_level=current_level,
        objective=objective,
        code=code,
        testing=testing,
        total_levels=total_levels,
    )


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


def run_code_against_tests(modified_code, testing):
    """Write a temp level file and run file_runner.py, returning the test output."""
    import os
    import subprocess
    import tempfile

    # Compose a temporary level file
    with tempfile.NamedTemporaryFile(mode="w+", suffix=".txt", delete=False) as tmp_level:
        tmp_level.write("<CODE>\n" + modified_code + "\n<\\CODE>\n")
        tmp_level.write("<TESTING>\n" + testing + "\n<\\TESTING>\n")
        tmp_level_path = tmp_level.name
    # Run file_runner.py on the temporary level file
    try:
        result = subprocess.run(
            ["python", "file_runner.py", tmp_level_path], capture_output=True, text=True, timeout=10
        )
        test_output = result.stdout + ("\n" + result.stderr if result.stderr else "")
    except Exception as e:
        test_output = f"Error running tests: {e}"
    finally:
        os.unlink(tmp_level_path)
    return test_output


@app.route("/ai_modify_code", methods=["POST"])
def ai_modify_code_route():
    try:
        data = request.get_json()
        current_code = data.get("current_code")
        transcription = data.get("transcription")
        current_level = data.get("current_level", 1)  # Default to level 1 if not provided

        if not current_code or not transcription:
            return jsonify({"status": "error", "message": "Missing current_code or transcription"}), 400

        print(f"Calling Claude with code:\n{current_code}\nInstruction: {transcription}")
        modified_code = claude.generate_modified_code(current_code, transcription)
        print(f"Claude returned modified code:\n{modified_code}")

        testing = data.get("testing")
        if not testing:
            # Fetch testing block from the level file
            _, _, testing = parse_level_content(current_level)
            if not testing or testing == "Testing not found.":
                return jsonify(
                    {
                        "status": "error",
                        "message": "Missing testing block for test execution and could not fetch from level file.",
                    }
                ), 400

        test_output = run_code_against_tests(modified_code, testing)

        return jsonify({"status": "success", "modified_code": modified_code, "test_output": test_output})
    except Exception as e:
        print(f"Error in /ai_modify_code: {e}")
        return jsonify({"status": "error", "message": f"Error processing with AI: {str(e)}"}), 500


@app.route("/run_code", methods=["POST"])
def run_code_route():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"status": "error", "message": "No data provided"}), 400

        current_level = data.get("current_level", "1")
        modified_code = data.get("modified_code")

        if not modified_code:
            return jsonify({"status": "error", "message": "No code provided"}), 400

        # Get the testing code from the level file
        level_file_path = os.path.join("levels", f"level{current_level}.txt")
        _, testing = process_level_file(level_file_path)

        # Create a temporary file to run the code
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as temp_file:
            temp_path = temp_file.name
            write_and_run(modified_code, testing, temp_path)

            # Check if the file exists and run it
            if os.path.exists(temp_path):
                result = subprocess.run([sys.executable, temp_path], capture_output=True, text=True)
                os.unlink(temp_path)  # Clean up the temporary file

                if result.returncode == 0:
                    # All tests passed
                    next_level = str(int(current_level) + 1)
                    return jsonify(
                        {
                            "status": "success",
                            "message": "Congratulations! All tests passed!",
                            "next_level": next_level,
                        }
                    )
                else:
                    # Tests failed
                    return jsonify({"status": "error", "message": "Tests failed", "error": result.stderr}), 400
            else:
                return jsonify({"status": "error", "message": "Failed to create temporary file"}), 500

    except Exception as e:
        print(f"Error in /run_code: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True)

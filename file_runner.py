import re
import subprocess
import sys
from pathlib import Path


def extract_blocks(text, block_name):
    pattern = r"<" + block_name + r">(.*?)<\\" + block_name + r">"
    match = re.search(pattern, text, re.DOTALL)
    return match.group(1).strip() if match else ""


def process_level_file(level_path):
    with open(level_path, "r") as f:
        content = f.read()
    code = extract_blocks(content, "CODE")
    testing = extract_blocks(content, "TESTING")
    return code, testing


def write_and_run(code, testing, output_path):
    with open(output_path, "w") as f:
        f.write(code + "\n\n")
        f.write(testing + "\n")
    # Run the file and print output
    result = subprocess.run([sys.executable, output_path], capture_output=True, text=True)
    print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)


def main():
    if len(sys.argv) < 2:
        print("Usage: python file_runner.py <level_file>")
        sys.exit(1)
    level_file = sys.argv[1]
    code, testing = process_level_file(level_file)
    output_py = Path(level_file).with_suffix(".run.py")
    write_and_run(code, testing, output_py)


if __name__ == "__main__":
    main()

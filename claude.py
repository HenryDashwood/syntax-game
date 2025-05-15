import re
import sys

import anthropic

from utils import getenv

client = anthropic.Anthropic(api_key=getenv("ANTHROPIC_API_KEY"))


def extract_blocks(text, block_name):
    pattern = r"<" + block_name + r">(.*?)<\\" + block_name + r">"
    match = re.search(pattern, text, re.DOTALL)
    return match.group(1).strip() if match else ""


def generate_modified_code(current_code: str, modification_instruction: str) -> str:
    prompt_content = f"""You are an AI assistant that modifies code based on user instructions.

Original Code:
```python
{current_code}
```

User's instruction to modify the code: "{modification_instruction}"

Please provide only the complete, modified code block. Do not include any explanations or surrounding text outside the code block.
Ensure the output is ONLY the raw code, without any ```python or ``` markers.

Modified Code Only:"""

    response = client.messages.create(
        model="claude-3-5-sonnet-20240620",
        max_tokens=1024,
        system="Only return content inside code blocks. Do not include any surrounding text, commentary, or explanation. Don't include backticks or anything like that.",
        messages=[
            {
                "role": "user",
                "content": prompt_content,
            },
        ],
        stop_sequences=["\n```"],  # Attempt to stop Claude before it closes a code block if it adds one.
    )

    generated_text = "\n".join(block.text for block in response.content if hasattr(block, "text"))

    # Clean up potential leading/trailing backticks or 'python' keyword if Claude still adds them.
    cleaned_code = generated_text.strip()
    if cleaned_code.startswith("```python\n"):
        cleaned_code = cleaned_code[len("```python\n") :]
    if cleaned_code.startswith("```\n"):
        cleaned_code = cleaned_code[len("```\n") :]
    if cleaned_code.endswith("\n```"):
        cleaned_code = cleaned_code[: -len("\n```")]
    if cleaned_code.endswith("```"):
        cleaned_code = cleaned_code[: -len("```")]

    return cleaned_code.strip()


if __name__ == "__main__":
    # Simplified main for basic testing if needed
    if len(sys.argv) < 3:
        print('Usage: python claude.py <path_to_code_file> "<modification_instruction>"')
        print("Example: python claude.py ./levels/level1.txt \"change 'there' to 10\"")
        sys.exit(1)

    code_file_path = sys.argv[1]
    instruction = sys.argv[2]

    try:
        with open(code_file_path, "r") as f:
            original_code = f.read()
        # If the file is a level file, extract just the code part
        if "<CODE>" in original_code:
            original_code = extract_blocks(original_code, "CODE")

    except FileNotFoundError:
        print(f"Error: File not found at {code_file_path}")
        sys.exit(1)

    print(f"Original Code (from {code_file_path}):\n{original_code}\n")
    print(f"Instruction: {instruction}\n")
    modified_code = generate_modified_code(original_code, instruction)
    print("Claude response (modified code):\n", modified_code)

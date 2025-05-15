import re
import sys

import anthropic

from utils import getenv

client = anthropic.Anthropic(api_key=getenv("ANTHROPIC_API_KEY"))


def extract_blocks(text, block_name):
    pattern = r"<" + block_name + r">(.*?)<\\" + block_name + r">"
    match = re.search(pattern, text, re.DOTALL)
    return match.group(1).strip() if match else ""


def generate_code(objective: str, code: str) -> str:
    response = client.messages.create(
        model="claude-3-5-sonnet-20240620",
        max_tokens=1024,
        messages=[
            {
                "role": "user",
                "content": f"Objective: {objective}\n\nCode: {code}",
            }
        ],
    )
    # Only join .text for blocks that have the text attribute
    return "\n".join(block.text for block in response.content if hasattr(block, "text"))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python claude.py <level_file>")
        sys.exit(1)
    level_file = sys.argv[1]
    with open(level_file, "r") as f:
        content = f.read()
    objective = extract_blocks(content, "OBJECTIVE")
    code = extract_blocks(content, "CODE")
    print(f"Objective: {objective}\n\nCode: {code}\n")
    response = generate_code(objective, code)
    print("Claude response:\n", response)

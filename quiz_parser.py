import random
import re
from typing import List, Dict, Any


def parse_quiz_file(file_path: str) -> List[Dict[str, Any]]:
    """
    Parse the quiz file and return list of questions.
    Each question dict: {'question': str, 'options': List[str], 'correct': int}
    Format: question\n=====\noption1\n=====\noption2\n... separated by +++++.
    Correct option can be marked with leading #. If no marker exists, the first
    option is treated as correct for backward compatibility.
    """
    questions = []
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    blocks = re.split(r"(?m)^\s*\+{5,}\s*$", content.strip())

    def clean_text(text: str, max_len: int) -> str:
        text = re.sub(r"\s+", " ", text).strip()
        if len(text) > max_len:
            text = text[: max_len - 3].rstrip() + "..."
        return text

    for block in blocks:
        parts = [
            part.strip()
            for part in re.split(r"(?m)^\s*={3,}\s*$", block.strip())
            if part.strip()
        ]
        if len(parts) < 5:  # question + 4 options
            continue

        question = clean_text(parts[0], 300)
        options = []
        correct = 0

        for index, raw_option in enumerate(parts[1:5]):
            option = raw_option.strip()
            if option.startswith("#"):
                correct = index
                option = option[1:].strip()
            options.append(clean_text(option, 100))

        if question and len(options) == 4 and all(options):
            questions.append(
                {"question": question, "options": options, "correct": correct}
            )

    return questions


def randomize_options(question: Dict[str, Any]) -> Dict[str, Any]:
    """
    Randomize the order of options and update correct index.
    """
    option_pairs = [
        {"text": option, "is_correct": index == question["correct"]}
        for index, option in enumerate(question["options"])
    ]
    random.shuffle(option_pairs)
    return {
        "question": question["question"],
        "options": [option["text"] for option in option_pairs],
        "correct": next(
            index for index, option in enumerate(option_pairs) if option["is_correct"]
        ),
    }

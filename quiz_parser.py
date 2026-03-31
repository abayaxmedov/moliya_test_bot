import random
from typing import List, Dict, Any


def parse_quiz_file(file_path: str) -> List[Dict[str, Any]]:
    """
    Parse the quiz file and return list of questions.
    Each question dict: {'question': str, 'options': List[str], 'correct': int}
    Format: question\n=====\noption1\n=====\noption2\n... separated by +++++
    Correct is the first option (index 0)
    """
    questions = []
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Split by +++++
    blocks = content.strip().split("+++++")

    def sanitize_option(option: str) -> str:
        option = option.strip().replace("\n", " ")
        if len(option) > 100:
            option = option[:97].rstrip() + "..."
        return option

    for block in blocks:
        lines = [line.strip() for line in block.strip().split("\n") if line.strip()]
        if len(lines) < 5:  # question + 4 options
            continue

        question = lines[0]
        options = []
        for line in lines[1:]:
            if line.startswith("====="):
                continue
            options.append(sanitize_option(line))

        if len(options) == 4:
            # Correct is the first option (index 0)
            correct = 0
            questions.append(
                {"question": question, "options": options, "correct": correct}
            )

    return questions


def randomize_options(question: Dict[str, Any]) -> Dict[str, Any]:
    """
    Randomize the order of options and update correct index.
    """
    opts = question["options"][:]
    correct_option = opts[question["correct"]]
    random.shuffle(opts)
    new_correct = opts.index(correct_option)
    return {"question": question["question"], "options": opts, "correct": new_correct}

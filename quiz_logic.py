import random
from typing import List, Dict, Any
from quiz_parser import parse_quiz_file, randomize_options


def get_random_questions(quiz_file: str, num: int = 20) -> List[Dict[str, Any]]:
    """
    Get num random questions from the file, with randomized options.
    """
    all_questions = parse_quiz_file(quiz_file)
    if len(all_questions) < num:
        num = len(all_questions)
    selected = random.sample(all_questions, num)
    return [randomize_options(q) for q in selected]

from typing import List, Dict, Any
from quiz_parser import parse_quiz_file, randomize_options


def split_questions_into_groups(
    questions: List[Dict[str, Any]], group_count: int
) -> List[List[Dict[str, Any]]]:
    """
    Split questions into consecutive groups without repeating questions.
    """
    if group_count <= 0:
        raise ValueError("group_count must be greater than zero")

    base_size, extra = divmod(len(questions), group_count)
    groups = []
    start = 0

    for group_index in range(group_count):
        group_size = base_size + int(group_index < extra)
        end = start + group_size
        groups.append(questions[start:end])
        start = end

    return groups


def get_group_questions(
    quiz_file: str, group_number: int, group_count: int = 8
) -> List[Dict[str, Any]]:
    """
    Return questions for the selected 1-based group number.
    """
    groups = split_questions_into_groups(parse_quiz_file(quiz_file), group_count)

    if group_number < 1 or group_number > len(groups):
        return []

    selected_group = groups[group_number - 1]
    questions = []

    for question_number, question in enumerate(selected_group, start=1):
        randomized = randomize_options(question)
        randomized["group_number"] = group_number
        randomized["group_question_number"] = question_number
        questions.append(randomized)

    return questions

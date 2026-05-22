import json
import os
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


def load_user_progress(progress_file: str) -> Dict[str, Any]:
    if not os.path.exists(progress_file):
        return {"users": {}}

    try:
        with open(progress_file, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return {"users": {}}

    if not isinstance(data, dict):
        return {"users": {}}
    if not isinstance(data.get("users"), dict):
        data["users"] = {}
    return data


def save_user_progress(progress_file: str, data: Dict[str, Any]) -> None:
    progress_dir = os.path.dirname(progress_file)
    if progress_dir:
        os.makedirs(progress_dir, exist_ok=True)

    tmp_file = f"{progress_file}.tmp"
    with open(tmp_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp_file, progress_file)


def get_next_group_questions(
    quiz_file: str,
    progress_file: str,
    user_id: int,
    group_count: int = 8,
) -> tuple[int, List[Dict[str, Any]]]:
    """
    Return the next group for the user and advance their next start position.
    """
    groups = split_questions_into_groups(parse_quiz_file(quiz_file), group_count)
    available_groups = [group for group in groups if group]
    if not available_groups:
        return 0, []

    progress = load_user_progress(progress_file)
    users = progress["users"]
    user_key = str(user_id)
    next_group = int(users.get(user_key, {}).get("next_group", 0)) % len(
        available_groups
    )
    users[user_key] = {"next_group": (next_group + 1) % len(available_groups)}
    save_user_progress(progress_file, progress)

    group_number = next_group + 1
    selected_group = available_groups[next_group]
    questions = []

    for question_number, question in enumerate(selected_group, start=1):
        randomized = randomize_options(question)
        randomized["group_number"] = group_number
        randomized["group_question_number"] = question_number
        questions.append(randomized)

    return group_number, questions

from aiogram import Router, F, Bot, Dispatcher
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    PollAnswer,
    Poll,
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.base import BaseStorage, StorageKey
from quiz_logic import get_random_questions
from config import QUIZ_FILE

router = Router()
active_polls: dict[str, tuple[int, int, int]] = {}


class QuizStates(StatesGroup):
    idle = State()
    quiz_active = State()


def build_storage_key(session_key: tuple[int, int, int]) -> StorageKey:
    bot_id, chat_id, user_id = session_key
    return StorageKey(bot_id=bot_id, chat_id=chat_id, user_id=user_id)


async def send_question(bot, chat_id: int, state: FSMContext):
    data = await state.get_data()
    questions = data["questions"]
    index = data["current_index"]

    if index >= len(questions):
        # End quiz
        score = data["score"]
        total = len(questions)
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="Restart Quiz", callback_data="restart")]
            ]
        )
        await bot.send_message(
            chat_id, f"✅ You answered {score}/{total} correctly", reply_markup=kb
        )
        await state.clear()
        return

    q = questions[index]

    # Ensure options are valid for Telegram (max 100 chars each)
    safe_options = []
    for opt in q["options"]:
        text = opt.strip().replace("\n", " ")
        if len(text) > 100:
            text = text[:97].rstrip() + "..."
        safe_options.append(text)

    # Send poll quiz
    try:
        poll_msg = await bot.send_poll(
            chat_id=chat_id,
            question=q["question"],
            options=safe_options,
            type="quiz",
            correct_option_id=q["correct"],
            open_period=30,
            is_anonymous=False,
        )
    except Exception as e:
        # Log or ignore and skip to next question
        print(f"Failed to send poll for question {index}: {e}")
        await state.update_data(current_index=index + 1)
        await send_question(bot, chat_id, state)
        return

    previous_poll_id = data.get("current_poll_id")
    if previous_poll_id:
        active_polls.pop(previous_poll_id, None)

    session_key = tuple(data["session_key"])
    active_polls[poll_msg.poll.id] = session_key

    # Store poll id and message id
    await state.update_data(
        current_poll_id=poll_msg.poll.id,
        poll_msg_id=poll_msg.message_id,
        answered=False,
    )


@router.message(F.text == "/start")
async def start_quiz(message: Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state == QuizStates.quiz_active:
        await message.answer(
            "Quiz already running. Finish it first or use /restart if available."
        )
        return

    # Get 20 random questions
    questions = get_random_questions(QUIZ_FILE, 20)

    await state.set_state(QuizStates.quiz_active)
    await state.update_data(
        questions=questions,
        current_index=0,
        score=0,
        answered=False,
        chat_id=message.chat.id,
        session_key=(state.key.bot_id, state.key.chat_id, state.key.user_id),
    )

    await send_question(message.bot, message.chat.id, state)


@router.poll_answer(QuizStates.quiz_active)
async def handle_poll_answer(poll_answer: PollAnswer, state: FSMContext):
    data = await state.get_data()
    if poll_answer.poll_id != data.get("current_poll_id"):
        return

    if data.get("answered", False):
        return

    user_option = poll_answer.option_ids[0] if poll_answer.option_ids else None
    q = data["questions"][data["current_index"]]
    correct = q["correct"]

    score = data["score"]
    if user_option == correct:
        score += 1

    await state.update_data(score=score, answered=True)
    active_polls.pop(poll_answer.poll_id, None)

    # Delete poll message
    chat_id = data["chat_id"]
    try:
        await poll_answer.bot.stop_poll(chat_id, data["poll_msg_id"])
    except Exception:
        pass

    try:
        await poll_answer.bot.delete_message(chat_id, data["poll_msg_id"])
    except Exception:
        pass

    # Next question
    index = data["current_index"] + 1
    await state.update_data(current_index=index, answered=False)
    await send_question(poll_answer.bot, chat_id, state)


@router.poll()
async def handle_poll_update(
    poll: Poll,
    bot: Bot,
    dispatcher: Dispatcher,
    fsm_storage: BaseStorage,
):
    if not poll.is_closed:
        return

    session_key = active_polls.get(poll.id)
    if session_key is None:
        return

    storage_key = build_storage_key(session_key)
    async with dispatcher.fsm.events_isolation.lock(key=storage_key):
        state = FSMContext(storage=fsm_storage, key=storage_key)
        if await state.get_state() != QuizStates.quiz_active.state:
            active_polls.pop(poll.id, None)
            return

        data = await state.get_data()
        if poll.id != data.get("current_poll_id"):
            active_polls.pop(poll.id, None)
            return

        if data.get("answered", False):
            active_polls.pop(poll.id, None)
            return

        # Timeout, delete poll message and next question
        active_polls.pop(poll.id, None)
        chat_id = data["chat_id"]
        try:
            await bot.delete_message(chat_id, data["poll_msg_id"])
        except Exception:
            pass

        index = data["current_index"] + 1
        await state.update_data(current_index=index, answered=False)
        await send_question(bot, chat_id, state)


@router.callback_query(F.data == "restart")
async def restart_quiz(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await start_quiz(callback.message, state)


# Ignore other messages during quiz
@router.message(QuizStates.quiz_active)
async def ignore_other(message: Message):
    pass

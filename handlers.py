import asyncio
import logging

from aiogram import Router, F, Bot
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    PollAnswer,
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from quiz_logic import get_next_group_questions
from config import GROUP_COUNT, PROGRESS_FILE, QUIZ_FILE

router = Router()
logger = logging.getLogger(__name__)

quiz_timers: dict[tuple[int, int, int], asyncio.Task] = {}
session_locks: dict[tuple[int, int, int], asyncio.Lock] = {}


class QuizStates(StatesGroup):
    idle = State()
    quiz_active = State()


def get_session_key_from_state(state: FSMContext) -> tuple[int, int, int]:
    return state.key.bot_id, state.key.chat_id, state.key.user_id


def get_session_key(data: dict, state: FSMContext | None = None) -> tuple[int, int, int]:
    session_key = data.get("session_key")
    if session_key is not None:
        return tuple(session_key)
    if state is None:
        raise RuntimeError("Session key is missing")
    return get_session_key_from_state(state)


def get_session_lock(session_key: tuple[int, int, int]) -> asyncio.Lock:
    lock = session_locks.get(session_key)
    if lock is None:
        lock = asyncio.Lock()
        session_locks[session_key] = lock
    return lock


def cancel_timer(session_key: tuple[int, int, int]) -> None:
    task = quiz_timers.get(session_key)
    current_task = asyncio.current_task()
    if task is None:
        return
    if task is current_task:
        return
    if not task.done():
        task.cancel()
    quiz_timers.pop(session_key, None)


def cleanup_runtime(session_key: tuple[int, int, int]) -> None:
    cancel_timer(session_key)
    lock = session_locks.get(session_key)
    if lock is not None and not lock.locked():
        session_locks.pop(session_key, None)


async def handle_question_timeout(
    bot: Bot,
    session_state: FSMContext,
    poll_id: str,
    timeout: int = 30,
) -> None:
    session_key = get_session_key_from_state(session_state)

    try:
        await asyncio.sleep(timeout)

        async with get_session_lock(session_key):
            if await session_state.get_state() != QuizStates.quiz_active.state:
                return

            data = await session_state.get_data()
            if data.get("current_poll_id") != poll_id:
                return
            if data.get("answered", False):
                return

            chat_id = data["chat_id"]
            next_index = data["current_index"] + 1
            await session_state.update_data(answered=True, current_index=next_index)

            try:
                await bot.stop_poll(chat_id, data["poll_msg_id"])
            except Exception:
                pass

            await send_question(bot, chat_id, session_state)
    except asyncio.CancelledError:
        return
    except Exception:
        logger.exception("Unexpected error while processing quiz timeout")
    finally:
        current_task = asyncio.current_task()
        if quiz_timers.get(session_key) is current_task:
            quiz_timers.pop(session_key, None)


def schedule_timeout(bot: Bot, state: FSMContext, poll_id: str, timeout: int = 30) -> None:
    session_key = get_session_key_from_state(state)
    cancel_timer(session_key)

    session_state = FSMContext(storage=state.storage, key=state.key)
    quiz_timers[session_key] = asyncio.create_task(
        handle_question_timeout(bot, session_state, poll_id, timeout)
    )


async def send_question(bot: Bot, chat_id: int, state: FSMContext) -> None:
    data = await state.get_data()
    session_key = get_session_key(data, state)
    questions = data["questions"]
    index = data["current_index"]

    if index >= len(questions):
        cleanup_runtime(session_key)
        score = data["score"]
        total = len(questions)
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="Qayta boshlash", callback_data="restart")]
            ]
        )
        await bot.send_message(
            chat_id,
            f"✅ Quiz tugadi. Siz {score}/{total} ta savolga to'g'ri javob berdingiz.",
            reply_markup=kb,
        )
        await state.clear()
        return

    q = questions[index]
    group_number = q.get("group_number", data.get("group_number"))
    question_number = q.get("group_question_number", index + 1)
    poll_question = f"{group_number}-guruh | {question_number}. {q['question']}"
    if len(poll_question) > 300:
        poll_question = poll_question[:297].rstrip() + "..."

    safe_options = []
    for opt in q["options"]:
        text = opt.strip().replace("\n", " ")
        if len(text) > 100:
            text = text[:97].rstrip() + "..."
        safe_options.append(text)

    try:
        poll_msg = await bot.send_poll(
            chat_id=chat_id,
            question=poll_question,
            options=safe_options,
            type="quiz",
            correct_option_id=q["correct"],
            open_period=30,
            is_anonymous=False,
        )
    except Exception:
        logger.exception("Failed to send poll for question %s", index)
        await state.update_data(current_index=index + 1)
        await send_question(bot, chat_id, state)
        return

    await state.update_data(
        current_poll_id=poll_msg.poll.id,
        poll_msg_id=poll_msg.message_id,
        answered=False,
    )
    schedule_timeout(bot, state, poll_msg.poll.id, timeout=30)


@router.message(F.text == "/start")
async def start_quiz(
    message: Message, state: FSMContext, user_id: int | None = None
) -> None:
    current_state = await state.get_state()
    if current_state == QuizStates.quiz_active.state:
        await message.answer("Quiz davom etmoqda. Avval joriy testni tugating.")
        return

    if user_id is None:
        user_id = message.from_user.id if message.from_user else message.chat.id
    group_number, questions = get_next_group_questions(
        QUIZ_FILE, PROGRESS_FILE, user_id, GROUP_COUNT
    )
    if not questions:
        await message.answer("Savollar topilmadi. Fayl formatini tekshiring.")
        return

    session_key = get_session_key_from_state(state)
    cleanup_runtime(session_key)

    await message.answer(
        f"{group_number}-guruh savollari boshlanadi. Jami {len(questions)} ta savol."
    )

    await state.set_state(QuizStates.quiz_active)
    await state.update_data(
        questions=questions,
        group_number=group_number,
        current_index=0,
        score=0,
        answered=False,
        chat_id=message.chat.id,
        session_key=session_key,
    )
    await send_question(message.bot, message.chat.id, state)


@router.poll_answer(QuizStates.quiz_active)
async def handle_poll_answer(poll_answer: PollAnswer, state: FSMContext) -> None:
    session_key = get_session_key_from_state(state)

    async with get_session_lock(session_key):
        data = await state.get_data()
        if poll_answer.poll_id != data.get("current_poll_id"):
            return
        if data.get("answered", False):
            return

        user_option = poll_answer.option_ids[0] if poll_answer.option_ids else None
        q = data["questions"][data["current_index"]]
        score = data["score"] + int(user_option == q["correct"])

        await state.update_data(score=score, answered=True)
        cancel_timer(session_key)

        chat_id = data["chat_id"]
        try:
            await poll_answer.bot.stop_poll(chat_id, data["poll_msg_id"])
        except Exception:
            pass

        await state.update_data(current_index=data["current_index"] + 1, answered=False)
        await send_question(poll_answer.bot, chat_id, state)


@router.callback_query(F.data == "restart")
async def restart_quiz(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    if data:
        cleanup_runtime(get_session_key(data, state))
    await state.clear()
    await callback.answer()
    if callback.message:
        await start_quiz(callback.message, state, user_id=callback.from_user.id)


@router.message(QuizStates.quiz_active)
async def ignore_other(message: Message) -> None:
    pass

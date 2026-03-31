import random
import os
from telegram import Update, Poll
from telegram.ext import (
    Application,
    CommandHandler,
    PollHandler,
    PollAnswerHandler,
    ContextTypes,
)

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN environment variable is not set.")

QUESTIONS_FILE = "MOLIYA uzb.txt"
SESSION_SIZE = 20

# In-memory state (keyed by chat_id)
user_sessions = {}
# poll_id -> chat_id mapping for callback handling
poll_to_chat = {}


def parse_questions(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    questions = []
    blocks = content.split("+++++")
    for block in blocks:
        if not block.strip():
            continue
        parts = block.strip().split("=====")
        if len(parts) < 5:
            continue

        question = parts[0].strip()
        options = [p.strip() for p in parts[1:5]]
        questions.append({"question": question, "options": options, "correct": 0})

    return questions


def make_session(questions):
    return {
        "questions": questions,
        "index": 0,
        "score": 0,
        "answered": False,
        "current_poll_id": None,
        "current_poll_msg_id": None,
        "current_correct_option_id": None,
    }


async def send_next_question(chat_id: int, context: ContextTypes.DEFAULT_TYPE):
    session = user_sessions.get(chat_id)
    if not session:
        return

    if session["index"] >= len(session["questions"]):
        score = session["score"]
        total = len(session["questions"])
        await context.bot.send_message(
            chat_id,
            f"✅ Quiz tugadi. Siz {score}/{total} ta savolga to'g'ri javob berdingiz.\n/start yozib qayta boshlashingiz mumkin.",
        )
        # Clear user session
        user_sessions.pop(chat_id, None)
        return

    q = session["questions"][session["index"]]
    options = q["options"].copy()
    correct_answer_text = options[q["correct"]]
    random.shuffle(options)
    correct_option_id = options.index(correct_answer_text)

    sent = await context.bot.send_poll(
        chat_id=chat_id,
        question=f"{session['index'] + 1}. {q['question']}",
        options=options,
        type="quiz",
        correct_option_id=correct_option_id,
        is_anonymous=False,
        open_period=30,
    )

    session["answered"] = False
    session["current_poll_id"] = sent.poll.id
    session["current_poll_msg_id"] = sent.message_id
    session["current_correct_option_id"] = correct_option_id

    poll_to_chat[sent.poll.id] = chat_id


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id

    active = user_sessions.get(chat_id)
    if active and active["index"] < len(active["questions"]):
        await update.message.reply_text(
            "⏳ Sizning quizingiz hozirda davom etmoqda. Iltimos, mavjud savolni tugatib, keyin /start yozing."
        )
        return

    all_questions = parse_questions(QUESTIONS_FILE)
    if not all_questions:
        await update.message.reply_text(
            "Savollar topilmadi. Fayl formatini tekshiring."
        )
        return

    chosen = random.sample(all_questions, min(SESSION_SIZE, len(all_questions)))
    user_sessions[chat_id] = make_session(chosen)

    await update.message.reply_text(
        f"🎯 Quiz boshlanadi! Jami {len(chosen)} ta savol. Har bir savolga 30 soniya. Javob berganingizdan so'ng keyingi savol darhol keladi."
    )

    await send_next_question(chat_id, context)


async def handle_poll_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    poll_answer = update.poll_answer
    poll_id = poll_answer.poll_id
    chat_id = poll_to_chat.get(poll_id)
    if chat_id is None:
        return

    session = user_sessions.get(chat_id)
    if not session or session["current_poll_id"] != poll_id:
        return

    if session["answered"]:
        return

    session["answered"] = True

    user_choice = poll_answer.option_ids[0] if poll_answer.option_ids else None
    correct_id = session["current_correct_option_id"]

    if user_choice is not None and user_choice == correct_id:
        session["score"] += 1
        await context.bot.send_message(chat_id, "✅ To'g'ri javob")
    else:
        current_q = session["questions"][session["index"]]
        correct_text = current_q["options"][current_q["correct"]]
        await context.bot.send_message(
            chat_id, f"❌ Noto'g'ri. To'g'ri javob: {correct_text}"
        )

    try:
        await context.bot.stop_poll(chat_id, session["current_poll_msg_id"])
    except Exception:
        pass

    try:
        await context.bot.delete_message(chat_id, session["current_poll_msg_id"])
    except Exception:
        pass

    session["index"] += 1
    await send_next_question(chat_id, context)


async def handle_poll(update: Update, context: ContextTypes.DEFAULT_TYPE):
    poll = update.poll
    if not poll.is_closed:
        return

    chat_id = poll_to_chat.pop(poll.id, None)
    if chat_id is None:
        return

    session = user_sessions.get(chat_id)
    if not session or session["current_poll_id"] != poll.id:
        return

    if session["answered"]:
        return

    # Vaqt tugadi
    session["answered"] = True
    await context.bot.send_message(
        chat_id, "⏰ Vaqt tugadi. Keyingi savolga o'tilmoqda..."
    )

    try:
        await context.bot.delete_message(chat_id, session["current_poll_msg_id"])
    except Exception:
        pass

    session["index"] += 1
    await send_next_question(chat_id, context)


def main():
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(PollAnswerHandler(handle_poll_answer))
    application.add_handler(PollHandler(handle_poll))
    application.run_polling()


if __name__ == "__main__":
    main()

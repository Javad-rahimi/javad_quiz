import os
import json
import random
import zipfile
from datetime import datetime, timedelta
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
import asyncio

TOKEN = 'bot_token'
OWNER_ID = 1234567890
DATA_DIR = 'users'
WINNER_FILE = 'weekly_winner.json'
QUESTIONS_FILE = 'questions.json'
ADMINS_FILE = 'admins.json'
ADS_FILE = 'ads.json'
VIP_FILE = "vip_users.json"

os.makedirs(DATA_DIR, exist_ok=True)

def load_admins():
    if os.path.exists(ADMINS_FILE):
        with open(ADMINS_FILE, "r", encoding="utf-8") as f:
            try:
                admins_list = json.load(f)
                if OWNER_ID not in admins_list:
                    admins_list.append(OWNER_ID)
                return admins_list
            except json.JSONDecodeError:
                return [OWNER_ID]
    return [OWNER_ID]

def save_admins(admin_list):
    with open(ADMINS_FILE, "w", encoding="utf-8") as f:
        json.dump(admin_list, f, ensure_ascii=False, indent=4)

ADMINS = load_admins()

def load_ads():
    if os.path.exists(ADS_FILE):
        with open(ADS_FILE, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {"channels": [], "enabled": False}
    return {"channels": [], "enabled": False}

def save_ads(ads_data):
    with open(ADS_FILE, "w", encoding="utf-8") as f:
        json.dump(ads_data, f, ensure_ascii=False, indent=4)

ads_data = load_ads()

user_states = {}
user_timers = {}

def load_questions():
    if os.path.exists(QUESTIONS_FILE):
        with open(QUESTIONS_FILE, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return
    return {
        "1": {"question": "نام دیگر شهر بابل چیست؟", "options": ["باربر", "بارکش", "بارفروش", "هیچکدام"], "answer": "بارفروش", "points": 1},
        "2": {"question": "به ربات چند نمره میدهید؟", "options": ["1", "2", "3", "4"], "answer": "3", "points": 1},
        "3": {"question": "نام سازنده چیست؟", "options": ["محمد", "جواد", "حسین","علی"], "answer": "جواد", "points": 1},
        "4": {"question": "سوال چهارم؟", "options": ["گزینه 1", "گزینه 2", "گزینه 3", "گزینه 4"], "answer": "گزینه 1", "points": 1},
        "5": {"question": "سوال پنجم؟", "options": ["گزینه 1", "گزینه 2", "گزینه 3", "گزینه 4"], "answer": "گزینه 2", "points": 1},
        "6": {"question": "سوال ششم؟", "options": ["گزینه 1", "گزینه 2", "گزینه 3", "گزینه 4"], "answer": "گزینه 3", "points": 1},
        "7": {"question": "سوال هفتم؟ (2 امتیاز)", "options": ["گزینه 1", "گزینه 2", "گزینه 3", "گزینه 4"], "answer": "گزینه 4", "points": 2},
        "8": {"question": "سوال هشتم؟ (2 امتیاز)", "options": ["گزینه 1", "گزینه 2", "گزینه 3", "گزینه 4"], "answer": "گزینه 1", "points": 2},
        "9": {"question": "سوال نهم؟ (2 امتیاز)", "options": ["گزینه 1", "گزینه 2", "گزینه 3", "گزینه 4"], "answer": "گزینه 2", "points": 2},
        "10": {"question": "سوال دهم؟ (3 امتیاز)", "options": ["گزینه 1", "گزینه 2", "گزینه 3", "گزینه 4"], "answer": "گزینه 3", "points": 3},
    }

def save_questions(q_data):
    with open(QUESTIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(q_data, f, ensure_ascii=False, indent=4)

questions = load_questions()

async def message_to_admins(bot, text):
    for admin_id in ADMINS:
        try:
            await bot.send_message(chat_id=admin_id, text=text)
        except Exception as e:
            print(f"Error sending to admin {admin_id}: {e}")

def save_user(user_id, data):
    filename = f"user-{user_id}.json"
    filepath = os.path.join(DATA_DIR, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_user(user_id):
    filename = f"user-{user_id}.json"
    filepath = os.path.join(DATA_DIR, filename)
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

async def search_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.chat_id not in ADMINS:
        return

    await update.message.reply_text("🔍 لطفاً نام یا یوزرنیم کاربر مورد نظر را وارد کنید:")
    user_states[update.message.chat_id] = "awaiting_search_query"

def can_edit_field(user_data, field):
    edit_times = user_data.get("last_edits", {})
    last_time_str = edit_times.get(field)
    if not last_time_str:
        return True
    try:
        last_time = datetime.fromisoformat(last_time_str)
        return (datetime.now() - last_time).days >= 7
    except:
        return True

def update_edit_time(user_data, field):
    if "last_edits" not in user_data:
        user_data["last_edits"] = {}
    user_data["last_edits"][field] = datetime.now().isoformat()

def delete_user_file(chat_id):
     for filename in os.listdir(DATA_DIR):
        if filename.startswith(f"{chat_id}_"):
            try:
                os.remove(os.path.join(DATA_DIR, filename))
                return True
            except Exception as e:
                print(f"Error deleting user file {filename}: {e}")
                return False
     return False

def load_vip_users():
    if os.path.exists(VIP_FILE):
        with open(VIP_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_vip_users(vip_list):
    with open(VIP_FILE, "w", encoding="utf-8") as f:
        json.dump(vip_list, f, ensure_ascii=False, indent=4)

def get_vip_user(uid):
    for user in vip_users:
        if user["id"] == uid:
            return user
    return None

vip_users = load_vip_users()

def save_winner(winner_id):
    with open(WINNER_FILE, "w") as f:
        json.dump({"winner": winner_id}, f)

def load_winner():
    if os.path.exists(WINNER_FILE):
        with open(WINNER_FILE, "r") as f:
            try:
                return json.load(f).get("winner")
            except json.JSONDecodeError:
                return None
    return None

async def question_timer(context: ContextTypes.DEFAULT_TYPE):
    job = context.job
    chat_id = job.data['chat_id']
    question_number = job.data['question_number']

    user_data = load_user(chat_id)
    if str(user_data.get('current_q')) != question_number:
        return

    await context.bot.send_message(chat_id=chat_id, text="⏰ وقتت تموم شد!")

    next_q_number = str(int(question_number) + 1)
    if next_q_number in questions:
        user_data['current_q'] = int(next_q_number)
        save_user(chat_id, user_data)
        await send_question(None, context, chat_id)
    else:
        prize = user_data.get('score', 0)
        await context.bot.send_message(chat_id=chat_id, text=f"🏆 آزمون تمام شد!\nامتیاز شما: {prize}")
        await context.bot.send_message(chat_id=chat_id, text="💳 شماره کارت خود را وارد کنید:")
        user_states[chat_id] = "awaiting_card"
        user_data["last_attempt_date"] = datetime.now().isoformat()
        save_user(chat_id, user_data)


    if chat_id in user_timers:
        del user_timers[chat_id]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    user_data = load_user(chat_id)

    if chat_id not in ADMINS and ads_data.get("enabled") and ads_data.get("channels"):
        is_member = True
        for channel_id in ads_data["channels"]:
            try:
                member = await context.bot.get_chat_member(chat_id=channel_id, user_id=chat_id)
                if member.status not in ["member", "administrator", "creator"]:
                    is_member = False
                    break
            except Exception as e:
                print(f"Error checking membership in channel {channel_id}: {e}")
                is_member = False

        if not is_member:
            keyboard = []
            for channel_id in ads_data["channels"]:
                try:
                    chat = await context.bot.get_chat(chat_id=channel_id)
                    invite_link = chat.invite_link if chat.invite_link else "https://t.me/" + chat.username
                    keyboard.append([InlineKeyboardButton(f"عضویت در کانال {chat.title}", url=invite_link)])
                except Exception as e:
                    print(f"Error getting channel info for {channel_id}: {e}")
                    continue

            keyboard.append([InlineKeyboardButton("✅ عضو شدم، بررسی کن", callback_data="check_membership")])
            markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text("برای استفاده از ربات، لطفاً در کانال‌های زیر عضو شوید:", reply_markup=markup)
            user_states[chat_id] = "awaiting_membership"
            return

    if user_data:
        user_name = user_data.get('name', 'کاربر')
        keyboard = [
            ["🚀 شروع آزمون", "💳 نحوه پرداخت جوایز"],
            ["📚 راهنما", "👤 مشخصات من", "🏆 برنده هفته", "❓ پشتیبانی"]
            ]
        markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text(f"👋 سلام {user_name} خوش آمدید!", reply_markup=markup)
        user_states[chat_id] = "none"
    else:
        keyboard = [
            ["📚 راهنما", "📝 ثبت نام", "❓ پشتیبانی"]
            ]
        markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text("🎉 خوش آمدید 🎉", reply_markup=markup)
        user_states[chat_id] = "none"

async def panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    if chat_id not in ADMINS:
        await update.message.reply_text("❌ شما ادمین نیستید.")
        return
    keyboard = [
        ["📊 آمار کلی", "📦 بکاپ کاربران", "🏆 انتخاب برنده", "🔎 جستجوی کاربر"],
        ["🛡️ کنترل ادمین", "👤 کنترل کاربران"],
        ["💳 کنترل پرداخت", "📢 ارسال پیام", "📣 تبلیغات", "❓ مدیریت سوالات"]
    ]
    markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text("📋 پنل مدیریت:", reply_markup=markup)
    user_states[chat_id] = "admin_panel"

async def send_question(update: Update, context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    user_data = load_user(chat_id)
    q_number_str = str(user_data.get('current_q', 1))
    question_data = questions.get(q_number_str)

    if not question_data:
        await context.bot.send_message(chat_id=chat_id, text="❌ سوالی موجود نیست یا آزمون تمام شده است.")
        prize = user_data.get('score', 0)
        await context.bot.send_message(chat_id=chat_id, text=f"🏆 آزمون تمام شد!\nامتیاز شما: {prize}")
        await context.bot.send_message(chat_id=chat_id, text="💳 شماره کارت خود را وارد کنید:")
        user_data["last_attempt_date"] = datetime.now().isoformat()
        save_user(chat_id, user_data)

        user_states[chat_id] = "awaiting_card"
        if chat_id in user_timers:
            del user_timers[chat_id]
        return

    options = question_data['options']
    random.shuffle(options)
    markup = ReplyKeyboardMarkup([[opt] for opt in options], resize_keyboard=True, one_time_keyboard=True)

    for job in context.job_queue.get_jobs_by_name(f"timer_{chat_id}_{user_timers.get(chat_id)}"):
        job.schedule_removal()

    user_timers[chat_id] = q_number_str
    context.job_queue.run_once(
        question_timer,
        5,
        data={'chat_id': chat_id, 'question_number': q_number_str},
        name=f"timer_{chat_id}_{q_number_str}"
    )

    await context.bot.send_message(
        chat_id=chat_id,
        text=question_data['question'],
        reply_markup=markup
    )

async def callback_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat.id
    data = query.data

    user_data = load_user(chat_id)
    state = user_states.get(chat_id)

    if data == "check_membership":
        is_member = True
        for channel_id in ads_data.get("channels", []):
            try:
                member = await context.bot.get_chat_member(chat_id=channel_id, user_id=chat_id)
                if member.status not in ["member", "administrator", "creator"]:
                    is_member = False
                    break
            except Exception as e:
                print(f"Error checking membership in channel {channel_id}: {e}")
                is_member = False
                break

        if is_member:
            user_data = load_user(chat_id)

            required_fields = ["name", "phone", "age", "province", "city"]
            if all(user_data.get(field) for field in required_fields):
                await context.bot.send_message(chat_id=chat_id, text="✅ عضویت شما تایید شد. اکنون می‌توانید از ربات استفاده کنید.")
                user_states[chat_id] = "none"
                keyboard = [
                    ["🚀 شروع آزمون", "💳 نحوه پرداخت جوایز"],
                    ["📚 راهنما", "👤 مشخصات من", "🏆 برنده هفته", "❓ پشتیبانی"]
                    ]
                markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
                await context.bot.send_message(chat_id=chat_id, text="منوی اصلی:", reply_markup=markup)
            else:
                await context.bot.send_message(chat_id=chat_id, text="✅ عضویت شما تایید شد. حالا میتوانید ثبت‌نام خود را کامل کنید.")
                user_states[chat_id] = "registering_name"

        else:
            await context.bot.send_message(chat_id=chat_id, text="❌ هنوز عضو تمام کانال‌های مورد نیاز نیستید. لطفاً دوباره تلاش کنید.")
            await start(update, context)
        return

    elif data.startswith("calculate_prize_"):
        user_id_to_calculate = int(data.split("_")[2])
        user_data = load_user(user_id_to_calculate)
        if user_data:
            user_data = load_user(user_id_to_calculate)
            user_name = user_data.get('name', 'ناشناس')
            user_score = user_data.get('score', 0)
            message_to_admins = (
                f"💰 درخواست محاسبه جایزه از کاربر:\n"
                f"👤 نام: {user_name}\n"
                f"🆔 یوزر آیدی: {user_id_to_calculate}\n"
                f"🏆 امتیاز: {user_score}\n"
                f"💳 شماره کارت: {user_data.get('card', '-')}\n"
                f"🏦 نام صاحب کارت: {user_data.get('card_name', '-')}"
            )
            for admin_id in ADMINS:
                await context.bot.send_message(chat_id=admin_id, text=message_to_admins)
            await context.bot.send_message(chat_id=chat_id, text="✅ درخواست محاسبه جایزه شما ثبت شد. ادمین به زودی بررسی می‌کند.")
        else:
            await context.bot.send_message(chat_id=chat_id, text="❌ اطلاعات کاربر یافت نشد.")
        return

    elif data.startswith("edit_"):
        edit_state_map = {
            "edit_name": "editing_name",
            "edit_phone": "editing_phone",
            "edit_age": "editing_age",
            "edit_province": "editing_province",
            "edit_city": "editing_city",
            "edit_card": "editing_card",
            "edit_card_name": "editing_card_name"
        }
        user_states[chat_id] = edit_state_map.get(data)
        prompts = {
            "editing_name": "✏️ لطفاً نام کامل جدید خود را وارد کنید:",
            "editing_phone": "📱 لطفاً شماره تماس جدید را وارد کنید (با +98 شروع):",
            "editing_age": "🎂 لطفاً سن جدید خود را وارد کنید (5 تا 100):",
            "editing_province": "🗺️ لطفاً نام استان جدید خود را وارد کنید:",
            "editing_city": "🏙️ لطفاً نام شهر جدید خود را وارد کنید:",
            "editing_card": "💳 لطفاً شماره کارت جدید را وارد کنید (۱۶ رقم):",
            "editing_card_name": "🏦 لطفاً نام جدید صاحب کارت را وارد کنید:"
        }
        state = user_states.get(chat_id)
        if state and (prompt := prompts.get(state)):
            await context.bot.send_message(chat_id=chat_id, text=prompt)
        else:
            await context.bot.send_message(chat_id=chat_id, text="❗ وضعیت ویرایش نامشخص است.")
        return

    elif data.startswith("reply_"):
        target_id = int(data.split("_")[1])
        context.user_data["reply_target"] = target_id
        await query.message.reply_text("✏️ لطفاً پاسخ خود را وارد کنید:")
        user_states[chat_id] = "replying_support"
        return

    else:
        await context.bot.send_message(chat_id=chat_id, text="❗ دستور ناشناخته.")


async def admin_panel_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    text = update.message.text.strip()
    state = user_states.get(chat_id, "none")

    if chat_id not in ADMINS:
        return

    if state.startswith("admin_paenl") or text in [
        "📊 آمار کلی",
        "📦 بکاپ کاربران",
        "🏆 انتخاب برنده",
        "🔎 جستجوی کاربر",
        "💳 کنترل پرداخت",
        "📢 ارسال پیام",
        "👤 کنترل کاربران",
        "🛡️ کنترل ادمین",
        "📣 تبلیغات",
        "❓ مدیریت سوالات"
        ]:
        if text == "📊 آمار کلی":
            total_users = 0
            tested_users = 0
            max_score = 0
            max_user = None

            for filename in os.listdir(DATA_DIR):
                if filename.endswith(".json"):
                    try:
                        filepath = os.path.join(DATA_DIR, filename)
                        with open(filepath, "r", encoding="utf-8") as f:
                            data = json.load(f)
                        uid = int(filename.split("-")[-1].replace(".json", ""))
                        if uid in ADMINS:
                            continue
                        total_users += 1
                        score = data.get("score", 0)
                        if score > 0:
                            tested_users += 1
                        if score > max_score:
                            max_score = score
                            max_user = (uid, data.get("name", "ناشناس"))
                    except Exception as e:
                        print(f"Error in stats for {filename}: {e}")

            total_vip = len(vip_users)

            msg = (
                f"📊 آمار کلی:\n"
                f"👥 تعداد کل کاربران: {total_users}\n"
                f"🧪 کاربران شرکت‌کننده در آزمون: {tested_users}\n"
                f"🌟 کاربران ویژه: {total_vip}\n"
            )
            if max_user:
                msg += f"🏆 بیشترین امتیاز: {max_score} (👤 {max_user[1]} | 🆔 {max_user[0]})"
            else:
                msg += "🏆 هنوز کاربری در آزمون شرکت نکرده."

            await update.message.reply_text(msg)
            user_states[chat_id] = "admin_panel"
        elif text == "📦 بکاپ کاربران":
            import zipfile
            from io import BytesIO

            zip_buffer = BytesIO()
            with zipfile.ZipFile(zip_buffer, "w") as zipf:
                for filename in os.listdir(DATA_DIR):
                    filepath = os.path.join(DATA_DIR, filename)
                    try:
                        zipf.write(filepath, arcname=filename)
                    except Exception as e:
                        print(f"Error adding {filename} to zip: {e}")

            zip_buffer.seek(0)
            await context.bot.send_document(
                chat_id=chat_id,
                document=zip_buffer,
                filename="backup_users.zip",
                caption="📦 فایل بکاپ کاربران (ZIP)"
            )
            user_states[chat_id] = "admin_panel"
        elif text == "🏆 انتخاب برنده":
            top_user = None
            top_score = -1

            for filename in os.listdir(DATA_DIR):
                if filename.endswith(".json"):
                    try:
                        filepath = os.path.join(DATA_DIR, filename)
                        with open(filepath, "r", encoding="utf-8") as f:
                            user_data = json.load(f)
                        uid = int(filename.split("-")[-1].replace(".json", ""))
                        if uid in ADMINS:
                            continue
                        score = user_data.get("score", 0)
                        if score > top_score:
                            top_score = score
                            top_user = (uid, user_data)
                    except Exception as e:
                        print(f"Error reading user file {filename}: {e}")

            if top_user:
                winner_id, winner_data = top_user
                save_winner(winner_id)
                name = winner_data.get('name', '-')
                if get_vip_user(winner_id):
                    name += " ⭐"

                await update.message.reply_text(
                    f"🏆 برنده هفته انتخاب شد:\n👤 {name}\n🆔 {winner_id}\nامتیاز: {top_score}"
                )
                try:
                    await context.bot.send_message(chat_id=winner_id, text="🎉 تبریک! شما برنده هفته شدید!")
                except:
                    pass
            else:
                await update.message.reply_text("❌ هیچ کاربری برای انتخاب وجود ندارد.")

            user_states[chat_id] = "admin_panel"
        elif text == "💳 کنترل پرداخت":
            await update.message.reply_text("💳 کنترل پرداخت در دست ساخت است.")
            user_states[chat_id] = "admin_panel"

        elif text == "📢 ارسال پیام":
            keyboard = [
                ["✉️ ارسال پیام به کاربر", "📨 ارسال پیام همگانی"],
                ["🔙 بازگشت"]
                        ]
            markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            await update.message.reply_text("گزینه ارسال پیام را انتخاب کنید:", reply_markup=markup)
            user_states[chat_id] = "admin_sending_message_menu"

        elif text == "👤 کنترل کاربران":
            keyboard = [
                ["👥 کاربران", "🌟 کاربران ویژه", "❌ حذف کاربر"],
                ["🔙 بازگشت"]
                        ]
            markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            await update.message.reply_text("گزینه کنترل کاربران را انتخاب کنید:", reply_markup=markup)
            user_states[chat_id] = "admin_user_control_menu"

        elif text == "🛡️ کنترل ادمین":
            keyboard = [
                ["🛡️ ادمین ها", "➕ افزودن ادمین", "➖ حذف ادمین"],
                ["🔙 بازگشت"]
                        ]
            markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            await update.message.reply_text("گزینه کنترل ادمین را انتخاب کنید:", reply_markup=markup)
            user_states[chat_id] = "admin_admin_control_menu"

        elif text == "📣 تبلیغات":
            keyboard = [
                ["➕ افزودن تبلیغات", "➖ حذف تبلیغات", "✅ فعال سازی تبلیغات", "❌ غیرفعال سازی تبلیغات"],
                ["🔙 بازگشت"]
                        ]
            markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            await update.message.reply_text("گزینه مدیریت تبلیغات را انتخاب کنید:", reply_markup=markup)
            user_states[chat_id] = "admin_ads_menu"

        elif text == "❓ مدیریت سوالات":
            keyboard = [
                ["➕ افزودن سوال", "➖ حذف سوال", "🔄 بارگذاری سوالات از فایل"],
                ["🔙 بازگشت"]
                        ]
            markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            await update.message.reply_text("گزینه مدیریت سوالات را انتخاب کنید:", reply_markup=markup)
            user_states[chat_id] = "admin_question_management_menu"

        elif text == "🔎 جستجوی کاربر":
            await search_user(update, context)

        elif text in [
            "📊 آمار کلی",
            "📦 بکاپ کاربران",
            "🏆 انتخاب برنده",
            "🔎 جستجوی کاربر",
            "💳 کنترل پرداخت",
            "📢 ارسال پیام",
            "👤 کنترل کاربران",
            "🛡️ کنترل ادمین",
            "📣 تبلیغات",
            "❓ مدیریت سوالات"
            ]:
            user_states[chat_id] = "admin_panel"

    elif state == "admin_sending_message_menu":
        if text == "✉️ ارسال پیام به کاربر":
            await update.message.reply_text(
                '🆔 آیدی عددی کاربر (یا چند آیدی با کاما جدا شده) و متن پیام را اینطوری بفرست:\n\n'
                'آیدی1,آیدی2,...\n'
                'متن'
                )
            user_states[chat_id] = "admin_awaiting_send_to_user"

        elif text == "📨 ارسال پیام همگانی":
            await update.message.reply_text("✍️ پیام همگانی را بفرست:")
            user_states[chat_id] = "admin_awaiting_broadcast"

        elif text == "🔙 بازگشت":
            await panel(update, context)
            return

    elif state == "admin_awaiting_broadcast":
        broadcast_message = text
        success_count = 0
        failed_count = 0
        skipped_admins = 0

        for filename in os.listdir(DATA_DIR):
            if filename.endswith(".json"):
                try:
                    filepath = os.path.join(DATA_DIR, filename)
                    with open(filepath, "r", encoding="utf-8") as f:
                        user_data = json.load(f)
                    uid = int(filename.split("-")[-1].replace(".json", ""))
                    if uid in ADMINS:
                        skipped_admins += 1
                        continue
                    await context.bot.send_message(chat_id=uid, text=f"📢 پیام از مدیریت:\n{text}")
                    success_count += 1
                except Exception as e:
                    print(f"Error broadcasting to {filename}: {e}")
                    failed_count += 1

        await update.message.reply_text(
            f"📨 پیام همگانی ارسال شد.\n"
            f"موفق: {success_count}\n"
            f"ناموفق: {failed_count}\n"
            f"رد شده (ادمین‌ها): {skipped_admins}"
        )
        user_states[chat_id] = "admin_sending_message_menu"

    elif state == "admin_awaiting_send_to_user":
        parts = text.split('\n', 1)
        if len(parts) < 2:
            await update.message.reply_text("❗ فرمت پیام اشتباه است. لطفاً آیدی‌ها و متن را در دو خط جداگانه بفرستید.")
            return

        user_ids_str = parts[0]
        message_text = parts[1]

        user_ids = []
        invalid_ids = []
        for uid_str in user_ids_str.split(','):
            try:
                uid = int(uid_str.strip())
                user_ids.append(uid)
            except ValueError:
                invalid_ids.append(uid_str.strip())

        if invalid_ids:
            await update.message.reply_text(f"❗ آیدی‌های نامعتبر یافت شد: {', '.join(invalid_ids)}")
            return

        sent_count = 0
        not_found_count = 0
        for uid in user_ids:
            user_data = load_user(uid)
            if user_data:
                try:
                    await context.bot.send_message(chat_id=uid, text=f"✉️ پیام از ادمین:\n{message_text}")
                    sent_count += 1
                except Exception as e:
                    print(f"Error sending message to user {uid}: {e}")
                    pass
            else:
                not_found_count += 1

        await update.message.reply_text(f"✅ پیام ارسال شد. تعداد موفق: {sent_count}. تعداد کاربر یافت نشد: {not_found_count}")
        user_states[chat_id] = "admin_panel"

    elif state == "admin_user_control_menu":
        if text == "👥 کاربران":
            users = os.listdir(DATA_DIR)
            if not users:
                await update.message.reply_text("📂 هیچ کاربری ثبت نشده.")
                return
            response = "👥 لیست کاربران:\n\n"
            for user_file in users:
                if user_file.endswith(".json"):
                    uid = int(user_file.split("-")[-1].replace(".json", ""))
                    data = load_user(uid)
                    name = data.get("name", "ناشناس")
                    response += f"👤 {name} - 🆔 {uid}\n"
            await update.message.reply_text(response)
    
        elif text == "🌟 کاربران ویژه":
            vip_list = [f"👤 {load_user(u['id']).get('name', '-')} - 🆔 {u['id']}" for u in vip_users]
            await update.message.reply_text("🌟 لیست کاربران ویژه:\n" + "\n".join(vip_list)
                                            if vip_list
                                            else "❌ هیچ کاربر ویژه‌ای ثبت نشده.")
    
        elif text == "❌ حذف کاربر":
            await update.message.reply_text("🆔 آیدی عددی کاربری که می‌خواهید حذف کنید را وارد کنید:")
            user_states[chat_id] = "admin_awaiting_delete_user_id"
            return

        elif text == "🔙 بازگشت":
            await panel(update, context)
            return

        else:
            await update.message.reply_text("❗ گزینه نامعتبر. لطفاً از دکمه‌ها استفاده کنید.")

    elif state == "admin_awaiting_delete_user_id":
        try:
            user_id_to_delete = int(text)
            if user_id_to_delete in ADMINS:
                 await update.message.reply_text("❌ نمی‌توانید ادمین را حذف کنید.")
            elif delete_user_file(user_id_to_delete):
                await update.message.reply_text(f"✅ کاربر با آیدی {user_id_to_delete} حذف شد.")
                try:
                    await context.bot.send_message(chat_id=user_id_to_delete, text="شما توسط ادمین حذف شدید.")
                except Exception as e:
                    print(f"Error sending deletion message to user {user_id_to_delete}: {e}")
                    pass
            else:
                await update.message.reply_text(f"❌ کاربری با آیدی {user_id_to_delete} یافت نشد.")
        except ValueError:
            await update.message.reply_text("❗ آیدی نامعتبر است. لطفاً یک عدد وارد کنید.")
        user_states[chat_id] = "admin_user_control_menu"

    elif state == "admin_admin_control_menu":
        if text == "🛡️ ادمین ها":
            response = "🛡️ لیست ادمین ها:\n\n"
            for admin_id in ADMINS:
                try:
                    chat_member = await context.bot.get_chat_member(chat_id=admin_id, user_id=admin_id)
                    user_name = chat_member.user.full_name
                    response += f"👤 {user_name} - 🆔 {admin_id}\n"
                except:
                    response += f"⚠️ ادمین نامعتبر یا یافت نشد: {admin_id}\n"
            await update.message.reply_text(response)

        elif text == "➕ افزودن ادمین":
            if chat_id != OWNER_ID:
                await update.message.reply_text("❌ فقط ادمین اصلی می‌تواند ادمین اضافه کند.")
                return
            await update.message.reply_text("🆔 آیدی عددی ادمین جدید را وارد کنید:")
            user_states[chat_id] = "admin_awaiting_add_admin_id"

        elif text == "➖ حذف ادمین":
            if chat_id != OWNER_ID:
                await update.message.reply_text("❌ فقط ادمین اصلی می‌تواند ادمین حذف کند.")
                return
            await update.message.reply_text("🆔 آیدی عددی ادمینی که می‌خواهید حذف کنید را وارد کنید:")
            user_states[chat_id] = "admin_awaiting_remove_admin_id"

        elif text == "🔙 بازگشت":
            await panel(update, context)
            return

    elif state == "admin_awaiting_add_admin_id":
        if chat_id != OWNER_ID:
             await update.message.reply_text("❌ شما اجازه این کار را ندارید.")
             user_states[chat_id] = "admin_admin_control_menu"
             return
        try:
            admin_id_to_add = int(text)
            if admin_id_to_add in ADMINS:
                await update.message.reply_text(f"❗ کاربر با آیدی {admin_id_to_add} از قبل ادمین است.")
            else:
                ADMINS.append(admin_id_to_add)
                save_admins(ADMINS)
                await update.message.reply_text(f"✅ کاربر با آیدی {admin_id_to_add} به لیست ادمین‌ها اضافه شد.")
            user_states[chat_id] = "admin_admin_control_menu"
        except ValueError:
            await update.message.reply_text("❗ آیدی نامعتبر است. لطفاً یک عدد وارد کنید.")
            user_states[chat_id] = "admin_admin_control_menu"

    elif state == "admin_awaiting_remove_admin_id":
        if chat_id != OWNER_ID:
             await update.message.reply_text("❌ شما اجازه این کار را ندارید.")
             user_states[chat_id] = "admin_admin_control_menu"
             return
        try:
            admin_id_to_remove = int(text)
            if admin_id_to_remove == OWNER_ID:
                 await update.message.reply_text("❌ نمی‌توانید ادمین اصلی را حذف کنید.")
            elif admin_id_to_remove in ADMINS:
                ADMINS.remove(admin_id_to_remove)
                save_admins(ADMINS)
                await update.message.reply_text(f"✅ ادمین با آیدی {admin_id_to_remove} از لیست ادمین‌ها حذف شد.")
            else:
                await update.message.reply_text(f"❌ ادمین با آیدی {admin_id_to_remove} یافت نشد.")
            user_states[chat_id] = "admin_admin_control_menu"
        except ValueError:
            await update.message.reply_text("❗ آیدی نامعتبر است. لطفاً یک عدد وارد کنید.")

    elif state == "admin_vip_menu":
        if text == "📋 لیست کاربران ویژه":
            response = "🌟 لیست کاربران ویژه:\n\n"
            for user in vip_users:
                uid = user["id"]
                bonus = user.get("bonus", 1)
                no_timer = user.get("no_timer", False)
                name = load_user(uid).get("name", "-")
                response += f"👤 {name} | 🆔 {uid} | 🎯 ضریب: {bonus} | ⏱️ بدون تایمر: {no_timer}\n"
            if not vip_users:
                response = "❌ لیست کاربران ویژه خالی است."
            await update.message.reply_text(response)

        elif text == "➕ افزودن کاربر ویژه":
            await update.message.reply_text("🆔 آیدی عددی کاربر را وارد کن:")
            user_states[chat_id] = "awaiting_add_vip"

        elif text == "➖ حذف کاربر ویژه":
            await update.message.reply_text("🆔 آیدی کاربری که می‌خوای حذف کنی را وارد کن:")
            user_states[chat_id] = "awaiting_remove_vip"

        elif text == "⚙️ تنظیمات کاربر ویژه":
            await update.message.reply_text("🆔 آیدی عددی کاربر برای تنظیمات را وارد کن:")
            user_states[chat_id] = "awaiting_configure_vip"

        elif text == "🔙 بازگشت":
            await panel(update, context)
            return

    elif state == "awaiting_add_vip":
        try:
            uid = int(text.strip())
            if get_vip_user(uid) is None:
                vip_users.append({"id": uid, "bonus": 1, "no_timer": False})
                save_vip_users(vip_users)
                await update.message.reply_text("✅ کاربر به لیست ویژه اضافه شد.")
            else:
                await update.message.reply_text("ℹ️ این کاربر قبلاً در لیست ویژه بوده است.")
        except:
            await update.message.reply_text("❗ آیدی نامعتبر است.")
        user_states[chat_id] = "admin_vip_menu"

    elif state == "awaiting_remove_vip":
        try:
            uid = int(text.strip())
            before = len(vip_users)
            vip_users[:] = [u for u in vip_users if u["id"] != uid]
            save_vip_users(vip_users)
            if len(vip_users) < before:
                await update.message.reply_text("✅ کاربر از لیست ویژه حذف شد.")
            else:
                await update.message.reply_text("❌ این کاربر در لیست ویژه نیست.")
        except:
            await update.message.reply_text("❗ آیدی نامعتبر است.")
        user_states[chat_id] = "admin_vip_menu"

    elif state == "awaiting_configure_vip":
        try:
            uid = int(text.strip())
            user = get_vip_user(uid)
            if user:
                context.user_data["vip_config_target"] = uid
                await update.message.reply_text(
                    f'⚙️ تنظیمات فعلی:\n🎯 ضریب: {user.get('bonus',1)}\n'
                    f'⏱️ بدون تایمر: {user.get('no_timer',False)}\n\n'
                    'ارسال کن مثلا:\nbonus=2\nیا\nno_timer=true یا false'
                )
                user_states[chat_id] = "configuring_vip"
            else:
                await update.message.reply_text("❌ کاربر در لیست ویژه نیست.")
                user_states[chat_id] = "admin_vip_menu"
        except:
            await update.message.reply_text("❗ آیدی نامعتبر است.")
            user_states[chat_id] = "admin_vip_menu"

    elif state == "configuring_vip":
        uid = context.user_data.get("vip_config_target")
        user = get_vip_user(uid)
        if not user:
            await update.message.reply_text("❌ کاربر یافت نشد.")
            user_states[chat_id] = "admin_vip_menu"
            return

        if text.startswith("bonus="):
            try:
                val = int(text.split("=")[1].strip())
                user["bonus"] = max(1, val)
                save_vip_users(vip_users)
                await update.message.reply_text(f"🎯 ضریب امتیاز روی {val} تنظیم شد.")
            except:
                await update.message.reply_text("❗ مقدار نامعتبر.")

        elif text.startswith("no_timer="):
            val = text.split("=")[1].strip().lower()
            user["no_timer"] = (val == "true")
            save_vip_users(vip_users)
            await update.message.reply_text(f"⏱️ بدون تایمر: {user['no_timer']}")

        else:
            await update.message.reply_text("❗ دستور نامعتبر. از bonus= یا no_timer= استفاده کن.")

        user_states[chat_id] = "admin_vip_menu"

    elif state == "admin_ads_menu":
        if text == "➕ افزودن تبلیغات":
            await update.message.reply_text("🆔 آیدی کانال (با پیشوند @ یا عددی) را وارد کنید:")
            user_states[chat_id] = "admin_awaiting_add_ad_channel"

        elif text == "➖ حذف تبلیغات":
            await update.message.reply_text("🆔 آیدی کانال برای حذف را وارد کنید:")
            user_states[chat_id] = "admin_awaiting_remove_ad_channel"

        elif text == "✅ فعال سازی تبلیغات":
            ads_data['enabled'] = True
            save_ads(ads_data)
            await update.message.reply_text("✅ تبلیغات فعال شد.")
            user_states[chat_id] = "admin_ads_menu"

        elif text == "❌ غیرفعال سازی تبلیغات":
            ads_data['enabled'] = False
            save_ads(ads_data)
            await update.message.reply_text("❌ تبلیغات غیرفعال شد.")
            user_states[chat_id] = "admin_ads_menu"

        elif text == "🔙 بازگشت":
            await panel(update, context)
            return

    elif state == "admin_awaiting_add_ad_channel":
        channel_id = text.strip()
        if not channel_id:
             await update.message.reply_text("❗ آیدی کانال نمی‌تواند خالی باشد.")
             return
        if channel_id not in ads_data['channels']:
            ads_data['channels'].append(channel_id)
            save_ads(ads_data)
            await update.message.reply_text(f"✅ کانال {channel_id} به لیست تبلیغات اضافه شد.")
        else:
            await update.message.reply_text(f"❗ کانال {channel_id} از قبل در لیست تبلیغات وجود دارد.")
        user_states[chat_id] = "admin_ads_menu"

    elif state == "admin_awaiting_remove_ad_channel":
        channel_id = text.strip()
        if not channel_id:
             await update.message.reply_text("❗ آیدی کانال نمی‌تواند خالی باشد.")
             return
        if channel_id in ads_data['channels']:
            ads_data['channels'].remove(channel_id)
            save_ads(ads_data)
            await update.message.reply_text(f"✅ کانال {channel_id} از لیست تبلیغات حذف شد.")
        else:
            await update.message.reply_text(f"❌ کانال {channel_id} در لیست تبلیغات یافت نشد.")
        user_states[chat_id] = "admin_ads_menu"

    elif state == "admin_question_management_menu":
        if text == "➕ افزودن سوال":
            await update.message.reply_text(
                '✍️ سوال جدید را در فرمت زیر وارد کنید:\n\n'
                'سوال\n'
                'گزینه1,گزینه2,گزینه3,گزینه4\n'
                'جواب صحیح\n'
                'امتیاز'
                )
            user_states[chat_id] = "admin_awaiting_add_question_data"

        elif text == "➖ حذف سوال":
            await update.message.reply_text("🔢 شماره سوال را وارد کنید:")
            user_states[chat_id] = "admin_awaiting_delete_question_number"

        elif text == "🔄 بارگذاری سوالات از فایل":
            await update.message.reply_text("📂 فایل questions.json را ارسال کن یا 'پیش‌نمایش سوالات' بنویس:")
            user_states[chat_id] = "admin_awaiting_questions_file_or_preview"

        elif text == "🔙 بازگشت":
            await panel(update, context)
            return

    elif state == "admin_awaiting_questions_file_or_preview":
        if text == "پیش‌نمایش سوالات":
            preview = "📋 لیست سوالات فعلی:\n\n"
            for qid, q in questions.items():
                preview += f"🔢 {qid}: {q['question']} (امتیاز: {q.get('points', 1)})\n"
            await update.message.reply_text(preview or "❌ سوالی یافت نشد.")
            user_states[chat_id] = "admin_panel"
        elif update.message.document:
            doc = update.message.document
            if doc.mime_type != "application/json":
                await update.message.reply_text("❌ فقط فایل JSON مجاز است.")
                return

            file = await doc.get_file()
            file_path = await file.download_to_drive(custom_path="/tmp/uploaded_questions.json")

            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                if "questions" not in data or not isinstance(data["questions"], list):
                    raise ValueError("فرمت فایل نادرست است. کلید 'questions' باید موجود باشد و لیست باشد.")

                new_questions = {}
                for item in data["questions"]:
                    qid = str(item.get("id"))
                    if not all(k in item for k in ("question", "options", "answer")):
                        raise ValueError(f"سوال با id {qid} ناقص است.")
                    new_questions[qid] = {
                        "question": item["question"],
                        "options": item["options"],
                        "answer": item["answer"],
                        "points": item.get("points", 1)
                    }

                save_questions(new_questions)
                questions.clear()
                questions.update(new_questions)
                questions.clear()
                questions.update(new_questions)

                await update.message.reply_text("✅ سوالات با موفقیت بارگذاری و جایگزین شدند.")

            except Exception as e:
                await update.message.reply_text(f"❌ خطا در بارگذاری فایل: {e}")

            user_states[chat_id] = "admin_panel"
        else:
            await update.message.reply_text("❗ لطفاً فایل questions.json یا 'پیش‌نمایش سوالات' را بفرستید.")

    elif state == "admin_awaiting_add_question_data":
        parts = text.split('\n')
        if len(parts) == 4:
            question_text = parts[0].strip()
            options_text = parts[1].strip()
            correct_answer = parts[2].strip()
            points_text = parts[3].strip()

            options = [opt.strip() for opt in options_text.split(',')]

            if not question_text or len(options) != 4 or correct_answer not in options or not points_text.isdigit():
                 await update.message.reply_text("❗ فرمت ورودی اشتباه است. لطفاً اطلاعات سوال را طبق فرمت خواسته شده وارد کنید.")
                 return

            points = int(points_text)
            next_q_number = max([int(k) for k in questions.keys()] or [0]) + 1
            questions[str(next_q_number)] = {
                "question": question_text,
                "options": options,
                "answer": correct_answer,
                "points": points
            }
            save_questions(questions)
            await update.message.reply_text(f"✅ سوال شماره {next_q_number} با موفقیت اضافه شد.")
            user_states[chat_id] = "admin_question_management_menu"
        else:
            await update.message.reply_text("❗ فرمت ورودی اشتباه است. لطفاً اطلاعات سوال را طبق فرمت خواسته شده وارد کنید.")

    elif state == "admin_awaiting_delete_question_number":
        try:
            q_number_to_delete = text.strip()
            if q_number_to_delete in questions:
                del questions[q_number_to_delete]
                save_questions(questions)
                await update.message.reply_text(f"✅ سوال شماره {q_number_to_delete} حذف شد.")
            else:
                await update.message.reply_text(f"❌ سوال شماره {q_number_to_delete} یافت نشد.")
            user_states[chat_id] = "admin_question_management_menu"
        except Exception as e:
            await update.message.reply_text("❗ ورودی نامعتبر است. لطفاً شماره سوال را به عدد وارد کنید.")
            print(f"Error deleting question: {e}")

    elif state == "admin_awaiting_questions_file":
        if update.message.document:
            file_id = update.message.document.file_id
            new_file = await context.bot.get_file(file_id)
            file_path = os.path.join(DATA_DIR, "new_questions.json")
            await new_file.download_to_drive(file_path)

            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    new_questions_data = json.load(f)
                questions.clear()
                questions.update(new_questions_data)
                save_questions(questions)
                await update.message.reply_text("✅ سوالات با موفقیت از فایل questions.json بارگذاری و جایگزین شدند.")
            except Exception as e:
                await update.message.reply_text(f"❌ خطایی در بارگذاری فایل سوالات رخ داد: {e}")
            finally:
                if os.path.exists(file_path):
                    os.remove(file_path)
            user_states[chat_id] = "admin_question_management_menu"
        else:
            await update.message.reply_text("❗ لطفاً فایل questions.json را ارسال کنید.")

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    text = update.message.text.strip()
    user_data = load_user(chat_id)
    state = user_states.get(chat_id, "none")

    if chat_id in ADMINS:
        if state.startswith("admin_") or text in [
            "📊 آمار کلی",
            "📦 بکاپ کاربران",
            "🏆 انتخاب برنده",
            "💳 کنترل پرداخت",
            "📢 ارسال پیام",
            "👤 کنترل کاربران",
            "🛡️ کنترل ادمین",
            "📣 تبلیغات",
            "❓ مدیریت سوالات"]:
             await admin_panel_handler(update, context)
             return

    if text == "📚 راهنما":
        await update.message.reply_text(
            "📚 راهنمای ربات:\n"
            "سلام! 👋\n"
            "به ربات جواد کوییز خوش آمدید. 🌟\n"
            "✅ با این ربات می‌توانید در یک آزمون ساده شرکت کنید.\n"
            "✅ در صورت پاسخ درست به سوالات، امتیاز دریافت خواهید کرد.\n"
            "✅ قبل از شروع آزمون باید ثبت‌نام کنید (شماره تلفن، نام کامل، سن، استان و شهر وارد شود).\n\n"
            "🔹 برای ثبت نام روی دکمه «ثبت نام» بزنید.\n"
            "🔹 برای شروع آزمون روی دکمه «شروع آزمون» کلیک کنید.\n"
            "🔹 منتظر اعلام نتایج و واریز جوایز توسط ادمین باشید.\n\n"
            "هر سوالی داشتی، بهم پیام بده! 🌸\n"
            "👨‍💻 سازنده: جواد\n"
            "📢 کانال رسمی: @Javad_Quiz_Channel"
        )

    elif text == "📝 ثبت نام":
        if user_data and user_data.get('name'):
             await update.message.reply_text("شما قبلا ثبت نام کرده‌اید.")
             keyboard = [
                    ["🚀 شروع آزمون", "💳 نحوه پرداخت جوایز"],
                    ["📚 راهنما", "👤 مشخصات من", "🏆 برنده هفته", "❓ پشتیبانی"]
                ]
             markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
             await update.message.reply_text("منوی اصلی:", reply_markup=markup)
             user_states[chat_id] = "none"
        else:
            keyboard = [["✅ ادامه"]]
            markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            await update.message.reply_text(
                "📜 قوانین ثبت نام در ربات:\n"
                "سلام کاربر عزیز! 🙌\n"
                "لطفاً قبل از شروع ثبت نام، با دقت قوانین زیر را مطالعه کنید:\n"
                "📱 وارد کردن شماره تلفن واقعی و معتبر الزامی است. (شماره باید با +98 شروع شده و ۱0 رقم باشد.)\n"
                "🧍‍♂️ نام و نام خانوادگی، سن، استان و شهر باید به صورت کامل و صحیح وارد شود.\n"
                "🎯 در صورت برنده شدن، جوایز فقط به شماره کارتی که ثبت کرده‌اید واریز می‌شود؛ بنابراین در وارد کردن اطلاعات دقت کنید.\n"
                "🚫 استفاده از اطلاعات نادرست یا جعلی باعث حذف شما از مسابقه و عدم واریز جایزه خواهد شد.\n"
                "🕐 زمان واریز جوایز توسط ادمین اعلام می‌شود. لطفاً تا اطلاع‌رسانی نهایی صبور باشید.\n"
                "📋 هر کاربر فقط یکبار اجازه ثبت نام و شرکت در آزمون را دارد.\n"
                "با زدن دکمه «ادامه» یعنی شما تمام قوانین را مطالعه کرده‌اید و آن‌ها را قبول دارید. ✅\n\n"
                "👨‍💻 سازنده: جواد\n"
                "📢 کانال رسمی: @Javad_Quiz_Channel"
                , reply_markup=markup)
            user_states[chat_id] = "awaiting_continue"

    elif text == "✅ ادامه" and state == "awaiting_continue":
        await update.message.reply_text(
            "📱 شماره موبایل را به صورت (**********98+) وارد کنید :\n"
            "❗این شماره تلفن باید در تلگرام عضو باشد "
            )
        user_states[chat_id] = "awaiting_phone"

    elif state == "awaiting_phone":
        if not (text.startswith("+98") and len(text) == 13 and text[1:].isdigit()):
            await update.message.reply_text("❗ شماره اشتباه است. شماره باید با +98 شروع شده و 10 رقم بعد از آن باشد. دوباره وارد کن:")
            return
        user_data['phone'] = text
        save_user(chat_id, user_data)
        await update.message.reply_text("👤 نام کامل خود را وارد کنید:")
        user_states[chat_id] = "awaiting_name"

    elif state == "awaiting_name":
        if len(text.split()) < 2 or not all(c.isalpha() or c.isspace() for c in text):
            await update.message.reply_text("❗ لطفاً نام و نام خانوادگی کامل و معتبر وارد کنید.")
            return
        user_data['name'] = text
        save_user(chat_id, user_data)
        await update.message.reply_text("🎂 سن خود را به عدد وارد کنید:")
        user_states[chat_id] = "awaiting_age"

    elif state == "awaiting_age":
        if not text.isdigit() or not (5 <= int(text) <= 100):
            await update.message.reply_text("❗ سن نامعتبر است. لطفاً یک عدد بین 5 تا 100 وارد کنید:")
            return
        user_data['age'] = int(text)
        save_user(chat_id, user_data)
        await update.message.reply_text("🗺️ نام استان خود را وارد کنید:")
        user_states[chat_id] = "awaiting_province"

    elif state == "awaiting_province":
        if not text.strip() or not all(c.isalpha() or c.isspace() for c in text):
             await update.message.reply_text("❗ نام استان نامعتبر است. دوباره وارد کنید:")
             return
        user_data['province'] = text.strip()
        save_user(chat_id, user_data)
        await update.message.reply_text("🏙️ نام شهر خود را وارد کنید:")
        user_states[chat_id] = "awaiting_city"

    elif state == "awaiting_city":
        if not text.strip() or not all(c.isalpha() or c.isspace() for c in text):
             await update.message.reply_text("❗ نام شهر نامعتبر است. دوباره وارد کنید:")
             return
        user_data['city'] = text.strip()
        user_data['score'] = 0
        save_user(chat_id, user_data)
        keyboard = [
            ["🚀 شروع آزمون", "💳 نحوه پرداخت جوایز"],
            ["📚 راهنما", "👤 مشخصات من", "🏆 برنده هفته", "❓ پشتیبانی"]
            ]
        markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text("✅ ثبت نام کامل شد!", reply_markup=markup)
        user_states[chat_id] = "none"

    elif state == "editing_name":
        if not can_edit_field(user_data, "name"):
            await update.message.reply_text("❌ شما در هفته گذشته این فیلد را ویرایش کرده‌اید. لطفاً بعداً دوباره تلاش کنید.")
            return
        if len(text.split()) < 2:
            await update.message.reply_text("❗ لطفاً نام کامل وارد کنید.")
            return
        user_data['name'] = text
        update_edit_time(user_data, "name")
        save_user(chat_id, user_data)
        await update.message.reply_text("✅ نام با موفقیت ویرایش شد.")
        await context.bot.send_message(chat_id=OWNER_ID, text=f"✏️ نام کاربر {chat_id} به: {text} تغییر یافت")
        user_states[chat_id] = "none"

    elif state == "editing_phone":
        if not can_edit_field(user_data, "phone"):
            await update.message.reply_text("❌ شما در هفته گذشته این فیلد را ویرایش کرده‌اید.")
            return
        if not (text.startswith("+98") and len(text) == 13 and text[1:].isdigit()):
            await update.message.reply_text("❗ شماره تماس نامعتبر است.")
            return
        user_data['phone'] = text
        update_edit_time(user_data, "phone")
        save_user(chat_id, user_data)
        await update.message.reply_text("✅ شماره تماس ذخیره شد.")
        await context.bot.send_message(chat_id=OWNER_ID, text=f"📱 شماره تماس کاربر {chat_id} تغییر کرد به: {text}")
        user_states[chat_id] = "none"

    elif state == "editing_age":
        if not can_edit_field(user_data, "age"):
            await update.message.reply_text("❌ شما اخیراً این فیلد را ویرایش کرده‌اید.")
            return
        if not text.isdigit() or not (5 <= int(text) <= 100):
            await update.message.reply_text("❗ سن نامعتبر است.")
            return
        user_data['age'] = int(text)
        update_edit_time(user_data, "age")
        save_user(chat_id, user_data)
        await update.message.reply_text("✅ سن ویرایش شد.")
        await context.bot.send_message(chat_id=OWNER_ID, text=f"🎂 سن کاربر {chat_id} تغییر کرد به: {text}")
        user_states[chat_id] = "none"

    elif state == "editing_province":
        if not can_edit_field(user_data, "province"):
            await update.message.reply_text("❌ ویرایش استان بیش از یکبار در هفته مجاز نیست.")
            return
        if not text.strip() or not all(c.isalpha() or c.isspace() for c in text):
            await update.message.reply_text("❗ نام استان نامعتبر است.")
            return
        user_data['province'] = text.strip()
        update_edit_time(user_data, "province")
        save_user(chat_id, user_data)
        await update.message.reply_text("✅ استان به‌روزرسانی شد.")
        await context.bot.send_message(chat_id=OWNER_ID, text=f"🗺️ استان کاربر {chat_id} تغییر کرد به: {text.strip()}")
        user_states[chat_id] = "none"

    elif state == "editing_city":
        if not can_edit_field(user_data, "city"):
            await update.message.reply_text("❌ این فیلد اخیراً ویرایش شده است.")
            return
        if not text.strip() or not all(c.isalpha() or c.isspace() for c in text):
            await update.message.reply_text("❗ نام شهر نامعتبر است.")
            return
        user_data['city'] = text.strip()
        update_edit_time(user_data, "city")
        save_user(chat_id, user_data)
        await update.message.reply_text("✅ شهر به‌روزرسانی شد.")
        await context.bot.send_message(chat_id=OWNER_ID, text=f"🏙️ شهر کاربر {chat_id} تغییر کرد به: {text.strip()}")
        user_states[chat_id] = "none"

    elif state == "editing_card":
        if not can_edit_field(user_data, "card"):
            await update.message.reply_text("❌ شما اخیراً این فیلد را تغییر داده‌اید.")
            return
        if not (text.isdigit() and len(text) == 16):
            await update.message.reply_text("❗ شماره کارت نامعتبر است.")
            return
        user_data['card'] = text
        update_edit_time(user_data, "card")
        save_user(chat_id, user_data)
        await update.message.reply_text("✅ شماره کارت ذخیره شد.")
        await context.bot.send_message(chat_id=OWNER_ID, text=f"💳 شماره کارت کاربر {chat_id} تغییر کرد به: {text}")
        user_states[chat_id] = "none"

    elif state == "editing_card_name":
        if not can_edit_field(user_data, "card_name"):
            await update.message.reply_text("❌ ویرایش این فیلد بیش از یک‌بار در هفته مجاز نیست.")
            return
        if not text.strip() or not all(c.isalpha() or c.isspace() for c in text):
            await update.message.reply_text("❗ نام صاحب کارت نامعتبر است.")
            return
        user_data['card_name'] = text.strip()
        update_edit_time(user_data, "card_name")
        save_user(chat_id, user_data)
        await update.message.reply_text("✅ نام صاحب کارت ذخیره شد.")
        await context.bot.send_message(chat_id=OWNER_ID, text=f"🏦 نام صاحب کارت کاربر {chat_id} تغییر کرد به: {text.strip()}")
        user_states[chat_id] = "none"

    elif text == "🚀 شروع آزمون":
        if chat_id not in ADMINS and ads_data.get("enabled") and ads_data.get("channels"):
            is_member = True
            for channel_id in ads_data["channels"]:
                try:
                    member = await context.bot.get_chat_member(chat_id=channel_id, user_id=chat_id)
                    if member.status not in ["member", "administrator", "creator"]:
                        is_member = False
                        break
                except Exception as e:
                    print(f"Error checking membership in channel {channel_id}: {e}")
                    is_member = True

            if not is_member:
                keyboard = []
                for channel_id in ads_data["channels"]:
                    try:
                        chat = await context.bot.get_chat(chat_id=channel_id)
                        invite_link = chat.invite_link if chat.invite_link else "https://t.me/" + chat.username
                        keyboard.append([InlineKeyboardButton(f"عضویت در کانال {chat.title}", url=invite_link)])
                    except Exception as e:
                        print(f"Error getting channel info for {channel_id}: {e}")
                        continue

                keyboard.append([InlineKeyboardButton("✅ عضو شدم، بررسی کن", callback_data="check_membership")])
                markup = InlineKeyboardMarkup(keyboard)
                await update.message.reply_text("برای استفاده از ربات، لطفاً در کانال‌های زیر عضو شوید:", reply_markup=markup)
                user_states[chat_id] = "awaiting_membership"
                return

        today = datetime.now().date()
        last_date_str = user_data.get("last_attempt_date")
        if last_date_str:
            try:
                last_date = datetime.fromisoformat(last_date_str).date()
                if last_date == today:
                    await update.message.reply_text("❗ شما امروز قبلاً در آزمون شرکت کرده‌اید. لطفاً فردا دوباره تلاش کنید.")
                    return
            except:
                pass

        user_data['score'] = 0
        user_data['current_q'] = 1
        user_data['last_attempt_date'] = datetime.now().isoformat()
        save_user(chat_id, user_data)

        await update.message.reply_text("✅ آزمون شروع شد!")
        await send_question(update, context, chat_id)
        user_states[chat_id] = "answering"
        keyboard = [
            ["🚀 شروع آزمون", "💳 نحوه پرداخت جوایز"],
            ["📚 راهنما", "👤 مشخصات من", "🏆 برنده هفته", "❓ پشتیبانی"]
            ]


    elif text == "🏆 برنده هفته":
        winner_id = load_winner()
        if winner_id:
            winner_data = load_user(int(winner_id))
            winner_name = winner_data.get('name', 'ناشناس')
            top_score = winner_data.get('score', 0)
            await update.message.reply_text(f"🏆 برنده هفته:\n👤 {winner_name} با امتیاز: {top_score}")
        else:
            await update.message.reply_text("❌ هنوز برنده‌ای اعلام نشده است.")

    elif state == "replying_support":
        target_id = context.user_data.get("reply_target")
        if target_id:
            try:
                await context.bot.send_message(chat_id=target_id, text=f"📬 پاسخ پشتیبانی:\n{text}")
                await update.message.reply_text("✅ پیام به کاربر ارسال شد.")
            except:
                await update.message.reply_text("❌ ارسال پیام به کاربر ناموفق بود.")
        else:
            await update.message.reply_text("❗ کاربر هدف یافت نشد.")
        user_states[chat_id] = "admin_panel"

    elif text == "👤 مشخصات من" and user_data:
        is_vip = get_vip_user(chat_id) is not None
        name = user_data.get('name', '-')
        if is_vip:
            name = f"{name} ⭐"
        response = (
            f"👤 مشخصات شما:\n"
            f"نام کامل: {name}\n"
            f"شماره تماس: {user_data.get('phone', '-')}\n"
            f"سن: {user_data.get('age', '-')}\n"
            f"استان: {user_data.get('province', '-')}\n"
            f"شهر: {user_data.get('city', '-')}\n"
            f"شماره کارت: {user_data.get('card', '-')}\n"
            f"نام صاحب کارت: {user_data.get('card_name', '-')}\n"
            f"امتیاز شما: {user_data.get('score', 0)}"
        )
        keyboard = [
            [InlineKeyboardButton("✏️ ویرایش نام", callback_data="edit_name")],
            [InlineKeyboardButton("📱 ویرایش شماره تماس", callback_data="edit_phone")],
            [InlineKeyboardButton("🎂 ویرایش سن", callback_data="edit_age")],
            [InlineKeyboardButton("🗺️ ویرایش استان", callback_data="edit_province")],
            [InlineKeyboardButton("🏙️ ویرایش شهر", callback_data="edit_city")],
            [InlineKeyboardButton("💳 تغییر شماره کارت", callback_data="edit_card")],
            [InlineKeyboardButton("🏦 تغییر نام صاحب کارت", callback_data="edit_card_name")]
        ]
        markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(response, reply_markup=markup)

    elif text == "💳 نحوه پرداخت جوایز" and user_data:
        keyboard = [[InlineKeyboardButton("محاسبه جایزه", callback_data=f"calculate_prize_{chat_id}")]]
        markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("نحوه پرداخت جوایز توسط ادمین محاسبه و پرداخت می‌گردد.", reply_markup=markup)

    elif text == "❓ پشتیبانی":
        await update.message.reply_text("📝 لطفاً پیام خود را برای پشتیبانی ارسال کنید:")
        user_states[chat_id] = "awaiting_support_message"

    elif state == "awaiting_support_message":
        support_msg = text
        user_states[chat_id] = "none"

        await update.message.reply_text("✅ پیام شما به پشتیبانی ارسال شد. پاسخ در صورت نیاز داده خواهد شد.")

        await message_to_admins(
            context.bot,
            f"""📩 پیام جدید پشتیبانی از کاربر:
👤 {user_data.get('name', '-')}
🆔 {chat_id}
✉️ پیام:
{support_msg}"""
        )

        try:
            await context.bot.send_message(
                chat_id=OWNER_ID,
                text="✏️ برای پاسخ به کاربر، روی دکمه زیر کلیک کن:",
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton("✏️ پاسخ به کاربر", callback_data=f"reply_{chat_id}")]]
                )
            )
        except:
            pass

        for admin_id in ADMINS:
            await context.bot.send_message(chat_id=admin_id, text=message_to_admins)
        await update.message.reply_text("✅ درخواست پشتیبانی شما ثبت و برای ادمین‌ها ارسال شد.")
        user_states[chat_id] = "none"

    elif state == "answering":
        if chat_id in user_timers:
            job_name = f"timer_{chat_id}_{user_timers[chat_id]}"
            current_jobs = context.job_queue.get_jobs_by_name(job_name)
            for job in current_jobs:
                job.schedule_removal()
            del user_timers[chat_id]

        current_q_number_str = str(user_data.get('current_q', 1))
        question_data = questions.get(current_q_number_str)

        if not question_data:
            await update.message.reply_text("❌ مشکلی در دریافت سوال پیش آمد.")
            user_states[chat_id] = "none"
            return

        correct_answer = question_data['answer']
        points = question_data.get('points', 1)

        if update.message.text == correct_answer:
            user_data['score'] = user_data.get('score', 0) + points
            save_user(chat_id, user_data)
        elif text == correct_answer:
            user_data['score'] = user_data.get('score', 0) + points
            await update.message.reply_text(f"✅ جواب درست بود! شما {points} امتیاز گرفتید.")
        else:
            await update.message.reply_text(f"❌ جواب اشتباه بود. جواب صحیح: {correct_answer}")

        next_q_number = int(current_q_number_str) + 1
        if str(next_q_number) in questions:
            user_data['current_q'] = next_q_number
            save_user(chat_id, user_data)
            await send_question(update, context, chat_id)
        else:
            prize = user_data.get('score', 0)
            await update.message.reply_text(f"🏆 آزمون تمام شد!\n'امتیاز شما: {prize}")
            await update.message.reply_text("💳 شماره کارت خود را وارد کنید:")
            user_states[chat_id] = "awaiting_card"

    elif state == "awaiting_card":
        if not (text.isdigit() and len(text) == 16):
            await update.message.reply_text("❗ شماره کارت نامعتبر است. شماره کارت باید ۱۶ رقم عددی باشد. دوباره وارد کن:")
            return
        user_data['card'] = text
        save_user(chat_id, user_data)
        await update.message.reply_text("🏦 نام صاحب کارت را وارد کنید:")
        user_states[chat_id] = "awaiting_card_name"

    elif state == "awaiting_card_name":
        if not text.strip() or not all(c.isalpha() or c.isspace() for c in text):
            await update.message.reply_text("❗ نام صاحب کارت نامعتبر است. دوباره وارد کنید:")
            return
        user_data['card_name'] = text.strip()
        save_user(chat_id, user_data)
        await update.message.reply_text("✅ اطلاعات کامل شد. منتظر تایید ادمین باشید.")
        await context.bot.send_message(
            chat_id=OWNER_ID,
            text=(
                '🎯 اطلاعات کاربر پس از آزمون:\n\n'
                f'👤 {user_data.get('name')}\n'
                f'📱 {user_data.get('phone')}\n'
                f'💳 {user_data.get('card')}\n'
                f'🏦 {user_data.get('card_name')}\n'
                f'🏆 امتیاز: {user_data.get('score', 0)}'
            )
        )
        keyboard = [
            ["🚀 شروع آزمون", "💳 نحوه پرداخت جوایز"],
            ["📚 راهنما", "👤 مشخصات من", "🏆 برنده هفته", "❓ پشتیبانی"]
            ]
        markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text("منوی اصلی:", reply_markup=markup)
        user_states[chat_id] = "none"
        user_data['current_q'] = 1

    else:
        await update.message.reply_text("❌ خطایی رخ داده است. لطفا دوباره تلاش کنید.")

def main():
    """Start the bot."""
    application = ApplicationBuilder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("panel", panel))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    application.add_handler(CallbackQueryHandler(callback_query_handler))
    print("Bot started!")
    application.run_polling(poll_interval=3.0)

if __name__ == "__main__":
    main()

import json
import telebot
from flask import Flask, request
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type
import logging
import time

# Loglash sozlamalari
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Environment o‘zgaruvchilarini yuklash
BOT_TOKEN = os.getenv("BOT_TOKEN", "7559962637:AAH8Xyb4roZWJ061WEYT2a5TAB9Epq4uFN8")
PAYMENT_CHANNEL = "@medstone_usmle"
OWNER_ID = int(os.getenv("OWNER_ID", 725821571))
CHANNELS = ["@medstone_usmle"]
TOKEN = "Ball"
Daily_bonus = 1
Per_Refer = 1

# Fanlar ro‘yxati
SUBJECTS = {
    "immunology": {"name": "Immunologiya", "desc": "Immun tizimi haqida"},
    "cardiology": {"name": "Kardiologiya", "desc": "Yurak va qon tomirlari"},
    "anatomy": {"name": "Anatomiya", "desc": "Inson tanasi tuzilishi"},
    "pathology": {"name": "Patologiya", "desc": "Kasalliklar tahlili"},
    "pharmacology": {"name": "Farmakologiya", "desc": "Dori vositalari"},
    "surgery": {"name": "Jarrohlik", "desc": "Operatsion texnikalar"},
    "pediatrics": {"name": "Pediatriya", "desc": "Bolalar salomatligi"},
    "neurology": {"name": "Nevrologiya", "desc": "Nerv tizimi kasalliklari"},
    "endocrinology": {"name": "Endokrinologiya", "desc": "Gormonal tizim"},
    "oncology": {"name": "Onkologiya", "desc": "Saraton kasalliklari"}
}

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

ADMIN_GROUP_USERNAME = "@endocrineqatnashchi"

# Google Sheets sozlamalari
SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
SPREADSHEET_NAME = os.getenv("SPREADSHEET_NAME", "Marafon")

# Google Sheets autentifikatsiyasi
creds_json = os.getenv("GOOGLE_SHEETS_CREDS")
if creds_json:
    creds_dict = json.loads(creds_json)
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, SCOPE)
    client = gspread.authorize(creds)
    sheet = client.open(SPREADSHEET_NAME).sheet1
    backup_sheet = client.open(SPREADSHEET_NAME).get_worksheet(1)
    video_catalog_sheet = client.open(SPREADSHEET_NAME).get_worksheet(2)
else:
    raise ValueError("Google Sheets credentials not found in environment variables!")

# Log yozuvlari uchun ro'yxat
log_messages = []

@app.route('/')
def hello_world():
    return 'Bot is running!'

@app.route(f'/{BOT_TOKEN}', methods=['POST'])
def receive_update():
    try:
        json_str = request.get_data().decode('UTF-8')
        update = telebot.types.Update.de_json(json_str)
        bot.process_new_updates([update])
        log_messages.append(json_str)
        app.logger.info(f"Received update: {json_str}")
        return '', 200
    except Exception as e:
        app.logger.error(f"Error processing update: {e}")
        return '', 500

@app.route('/logs')
def get_logs():
    return '<br>'.join(log_messages)

# Kanal tekshiruvi
def check(id):
    for channel in CHANNELS:
        check = bot.get_chat_member(channel, id)
        if check.status == 'left':
            return False
    return True

# Asosiy menyu
def menu(user_id, message_id=None):
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("👤 Hisobim", "🔗 Taklif linki")
    markup.row("🎁 Sovg‘alar", "📚 Fanlar")
    if user_id == OWNER_ID:
        markup.row("📊 Statistika", "📢 Broadcast")
    
    text = "🏠 Asosiy menyu:"
    if message_id:
        try:
            bot.edit_message_text(text, user_id, message_id, reply_markup=markup)
        except:
            bot.send_message(user_id, text, reply_markup=markup)
    else:
        bot.send_message(user_id, text, reply_markup=markup)

# Fanlar menyusi
def subjects_menu(user_id, message_id=None):
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    subject_buttons = [f"🎓 {info['name']}" for info in SUBJECTS.values()]
    for i in range(0, len(subject_buttons), 2):
        markup.row(*subject_buttons[i:i+2])
    markup.row("⬅️ Ortga")
    
    text = "📚 Fan tanlang:"
    if message_id:
        try:
            bot.edit_message_text(text, user_id, message_id, reply_markup=markup)
        except:
            bot.send_message(user_id, text, reply_markup=markup)
    else:
        bot.send_message(user_id, text, reply_markup=markup)

# Google Sheets-dan foydalanuvchilar ma'lumotlarini yuklash
@retry(stop=stop_after_attempt(3), wait=wait_fixed(2), retry=retry_if_exception_type(Exception))
def load_users_data():
    try:
        records = sheet.get_all_records()
        data = {
            "referred": {}, "referby": {}, "checkin": {}, "DailyQuiz": {},
            "balance": {}, "withd": {}, "id": {}, "refer": {}, "total": 0
        }
        for row in records:
            user_id = str(row['user_id'])
            data['referred'][user_id] = row.get('referred', 0)
            data['referby'][user_id] = row.get('referby', user_id)
            data['checkin'][user_id] = row.get('checkin', 0)
            data['DailyQuiz'][user_id] = row.get('DailyQuiz', "0")
            data['balance'][user_id] = row.get('balance', 0)
            data['withd'][user_id] = row.get('withd', 0)
            data['id'][user_id] = row.get('id', 0)
            data['refer'][user_id] = row.get('refer', False)
        data['total'] = len(data['referred'])
        logging.info(f"Loaded {data['total']} users from Google Sheets")
        return data
    except Exception as e:
        logging.error(f"Error loading data from Google Sheets: {e}")
        raise

# Foydalanuvchilar uchun backup funksiyasi
@retry(stop=stop_after_attempt(3), wait=wait_fixed(2), retry=retry_if_exception_type(Exception))
def backup_users_data(data):
    try:
        headers = ['user_id', 'referred', 'referby', 'checkin', 'DailyQuiz', 'balance', 'withd', 'id', 'refer']
        all_data = [headers]
        for user_id in data['referred']:
            row = [
                user_id,
                data['referred'].get(user_id, 0),
                data['referby'].get(user_id, user_id),
                data['checkin'].get(user_id, 0),
                data['DailyQuiz'].get(user_id, "0"),
                data['balance'].get(user_id, 0),
                data['withd'].get(user_id, 0),
                data['id'].get(user_id, 0),
                data['refer'].get(user_id, False)
            ]
            all_data.append(row)
        backup_sheet.update(values=all_data, range_name='A1')
        logging.info("Backup saved successfully")
    except Exception as e:
        logging.error(f"Backup error: {e}")
        raise

# Foydalanuvchilar uchun Google Sheets-ga ma'lumotlarni saqlash
@retry(stop=stop_after_attempt(3), wait=wait_fixed(2), retry=retry_if_exception_type(Exception))
def save_users_data(data):
    try:
        if not data['referred']:
            logging.warning("Data is empty, skipping save to avoid data loss")
            return
        backup_users_data(data)
        headers = ['user_id', 'referred', 'referby', 'checkin', 'DailyQuiz', 'balance', 'withd', 'id', 'refer']
        all_data = [headers]
        for user_id in data['referred']:
            row = [
                user_id,
                data['referred'].get(user_id, 0),
                data['referby'].get(user_id, user_id),
                data['checkin'].get(user_id, 0),
                data['DailyQuiz'].get(user_id, "0"),
                data['balance'].get(user_id, 0),
                data['withd'].get(user_id, 0),
                data['id'].get(user_id, 0),
                data['refer'].get(user_id, False)
            ]
            all_data.append(row)
        sheet.update(values=all_data, range_name='A1')
        logging.info("Data saved successfully to Google Sheets")
    except Exception as e:
        logging.error(f"Error saving data to Google Sheets: {e}")
        raise

# Videolarni yuborish
def send_videos(user_id, video_file_ids, message_id=None):
    for video_file_id in video_file_ids:
        bot.send_video(user_id, video_file_id, supports_streaming=True)
    if message_id:
        try:
            bot.edit_message_reply_markup(user_id, message_id, reply_markup=None)
        except:
            pass

# Video katalogini yuklash
@retry(stop=stop_after_attempt(3), wait=wait_fixed(2), retry=retry_if_exception_type(Exception))
def load_video_catalog(subject=None):
    try:
        records = video_catalog_sheet.get_all_records()
        catalog = {}
        for row in records:
            subject_key = row.get('subject', '').lower()
            index = str(row.get('index', ''))
            file_id = row.get('file_id', '')
            if subject_key and index and file_id:
                if subject is None or subject.lower() == subject_key:
                    catalog[f"{subject_key}_{index}"] = file_id
        logging.info(f"Loaded video catalog for {subject or 'all'} with {len(catalog)} entries")
        return catalog
    except Exception as e:
        logging.error(f"Error loading video catalog: {e}")
        return {}

# Video katalogini saqlash
@retry(stop=stop_after_attempt(3), wait=wait_fixed(2), retry=retry_if_exception_type(Exception))
def save_video_catalog(data):
    try:
        headers = ['subject', 'index', 'file_id']
        all_data = [headers]
        for key, file_id in data.items():
            subject_key, index = key.split('_', 1)
            all_data.append([subject_key, index, file_id])
        video_catalog_sheet.update(values=all_data, range_name='A1')
        logging.info(f"Video catalog saved with {len(data)} entries")
        return True
    except Exception as e:
        logging.error(f"Error saving video catalog: {e}")
        return False

# Sovg‘a videolarini yuborish
def send_gift_video(user_id, subject, message_id=None):
    data = load_users_data()
    catalog = load_video_catalog(subject)
    balance = data['balance'].get(str(user_id), 0)
    video_count = balance // 5
    sent_videos = []

    if video_count == 0:
        text = "⚠️ Ballaringiz yetarli emas! Do‘stlaringizni taklif qilib ball to‘plang!"
        if message_id:
            try:
                bot.edit_message_text(text, user_id, message_id, reply_markup=None)
            except:
                bot.send_message(user_id, text)
        else:
            bot.send_message(user_id, text)
        menu(user_id, message_id)
        return

    for i in range(1, video_count + 1):
        video_index = str(i)
        key = f"{subject.lower()}_{video_index}"
        if key in catalog:
            bot.send_video(user_id, catalog[key], supports_streaming=True)
            sent_videos.append(video_index)
        else:
            text = f"⚠️ {SUBJECTS[subject]['name']} {video_index}-dars topilmadi. Admin bilan bog‘laning!"
            if message_id:
                try:
                    bot.edit_message_text(text, user_id, message_id, reply_markup=None)
                except:
                    bot.send_message(user_id, text)
            else:
                bot.send_message(user_id, text)
            menu(user_id, message_id)
            return

    if sent_videos:
        text = f"🎥 {', '.join(sent_videos)}-darslar jo‘natildi! {'Ajoyib!' if video_count >= 3 else 'Ko‘proq dars uchun do‘st taklif qiling!'}"
        if message_id:
            try:
                bot.edit_message_text(text, user_id, message_id, reply_markup=None)
            except:
                bot.send_message(user_id, text)
        else:
            bot.send_message(user_id, text)
    menu(user_id, message_id)

# /start buyrug‘i
@bot.message_handler(commands=['start'])
def start(message):
    try:
        user_id = str(message.chat.id)
        msg = message.text
        referrer = msg.split()[1] if len(msg.split()) > 1 else None
        data = load_users_data()

        if user_id not in data['referred']:
            data['referred'][user_id] = 0
            data['total'] = len(data['referred'])
        if user_id not in data['referby']:
            data['referby'][user_id] = referrer if referrer else user_id
            if referrer and referrer in data['referred']:
                data['referred'][referrer] += 1
                data['balance'][referrer] = data['balance'].get(referrer, 0) + Per_Refer
        if user_id not in data['checkin']:
            data['checkin'][user_id] = 0
        if user_id not in data['DailyQuiz']:
            data['DailyQuiz'][user_id] = "0"
        if user_id not in data['balance']:
            data['balance'][user_id] = 0
        if user_id not in data['withd']:
            data['withd'][user_id] = 0
        if user_id not in data['id']:
            data['id'][user_id] = len(data['referred'])
        save_users_data(data)

        markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(telebot.types.KeyboardButton("✅ Obunani tekshirish"))
        msg_start = """🎉 Marafonga xush kelibsiz!  
📚 7 kunlik BEPUL kursda bilim oling!  
👇 Kanalga qo‘shiling: @medstone_usmle"""
        bot.send_message(message.chat.id, msg_start, reply_markup=markup)
    except Exception as e:
        bot.send_message(message.chat.id, "⚠️ Xatolik! Keyinroq urinib ko‘ring.")
        bot.send_message(OWNER_ID, f"⚠️ /start xatoligi: {str(e)}")

# Kontakt ma'lumotlari
@bot.message_handler(content_types=['contact'])
def contact(message):
    if message.contact:
        contact = message.contact.phone_number
        username = message.from_user.username or message.from_user.first_name
        bot.send_message(ADMIN_GROUP_USERNAME, f"👤 @{username}\n📞 Raqam: {contact}")
        
        msg = """🎉 Sovg‘angizni oling!  
1️⃣ BEPUL bonus video darsni yuklab oling!  
2️⃣ 5 ta do‘st taklif qiling – 1 ta dars BEPUL!  
3️⃣ 10 ta do‘st – 2 ta dars!  
4️⃣ 15 ta do‘st – 3 ta dars!  
🔥 Ko‘proq do‘st taklif qiling, butun kursni BEPUL oling!"""
        bot.send_message(message.chat.id, msg)
        menu(message.chat.id)

# Taklif linkini yuborish
def send_invite_link(user_id, message_id=None):
    data = load_users_data()
    bot_name = bot.get_me().username
    user = str(user_id)

    if user not in data['referred']:
        data['referred'][user] = 0
    save_users_data(data)

    ref_link = f"https://telegram.me/{bot_name}?start={user_id}"
    msg = f"🔗 Taklif havolangiz: {ref_link}\n📚 Do‘stlaringizni taklif qiling va BEPUL darslar oling!"
    if message_id:
        try:
            bot.edit_message_text(msg, user_id, message_id, reply_markup=None)
        except:
            bot.send_message(user_id, msg)
    else:
        bot.send_message(user_id, msg)
    menu(user_id, message_id)

# Broadcast buyrug‘i
@bot.message_handler(commands=['broadcast'])
def handle_broadcast(message):
    if message.chat.id != OWNER_ID:
        bot.send_message(message.chat.id, "🚫 Faqat admin uchun!")
        return
    
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.row("✍️ Matn", "📸 Rasm")
    markup.row("🎥 Video", "⬅️ Ortga")
    bot.send_message(message.chat.id, "📢 Broadcast turini tanlang:", reply_markup=markup)
    bot.register_next_step_handler(message, process_broadcast_type)

def process_broadcast_type(message):
    try:
        if message.chat.id != OWNER_ID:
            return
        
        broadcast_type = message.text
        if broadcast_type == "⬅️ Ortga":
            menu(message.chat.id, message.message_id)
            return
        if broadcast_type not in ["✍️ Matn", "📸 Rasm", "🎥 Video"]:
            bot.send_message(message.chat.id, "⚠️ To‘g‘ri tanlov qiling!")
            handle_broadcast(message)
            return

        if broadcast_type == "✍️ Matn":
            msg = bot.send_message(message.chat.id, "📝 Matn kiriting (/filter <ball> qo‘shish mumkin):")
            bot.register_next_step_handler(msg, lambda m: process_broadcast(m, 'text'))
        elif broadcast_type == "📸 Rasm":
            msg = bot.send_message(message.chat.id, "📸 Rasm yuklang (izoh ixtiyoriy):")
            bot.register_next_step_handler(msg, lambda m: process_broadcast(m, 'photo'))
        elif broadcast_type == "🎥 Video":
            msg = bot.send_message(message.chat.id, "🎥 Video yuklang (izoh ixtiyoriy):")
            bot.register_next_step_handler(msg, lambda m: process_broadcast(m, 'video'))
        
    except Exception as e:
        bot.send_message(message.chat.id, f"⚠️ Xatolik: {str(e)}")
        bot.send_message(OWNER_ID, f"⚠️ Broadcast xatoligi: {str(e)}")

def process_broadcast(message, broadcast_type):
    try:
        if message.chat.id != OWNER_ID:
            return

        data = load_users_data()
        user_ids = list(data['referred'].keys())
        
        min_balance = 0
        if broadcast_type == 'text' and '/filter' in message.text:
            try:
                min_balance = int(message.text.split('/filter')[1].split()[0])
                message.text = message.text.split('/filter')[0].strip()
                user_ids = [uid for uid in user_ids if data['balance'].get(uid, 0) >= min_balance]
            except:
                bot.reply_to(message, "⚠️ Filtr xato! /filter <ball> formatidan foydalaning.")
                return

        if not user_ids:
            bot.reply_to(message, "🚫 Foydalanuvchilar topilmadi!")
            return

        success_count = 0
        fail_count = 0
        blocked_users = []

        bot.reply_to(message, f"📢 Broadcast boshlandi. Jami {len(user_ids)} foydalanuvchi.")

        for user_id in user_ids:
            try:
                if broadcast_type == 'text':
                    bot.send_message(int(user_id), message.text)
                elif broadcast_type == 'photo' and message.photo:
                    caption = message.caption or ""
                    bot.send_photo(int(user_id), message.photo[-1].file_id, caption=caption)
                elif broadcast_type == 'video' and message.video:
                    caption = message.caption or ""
                    bot.send_video(int(user_id), message.video.file_id, caption=caption)
                success_count += 1
                time.sleep(0.05)
            except Exception as e:
                fail_count += 1
                if "Forbidden" in str(e):
                    blocked_users.append(user_id)
                logging.error(f"Error sending to {user_id}: {str(e)}")

        if blocked_users:
            for user_id in blocked_users:
                if user_id in data['referred']:
                    del data['referred'][user_id]
                    del data['referby'][user_id]
                    del data['balance'][user_id]
                    del data['checkin'][user_id]
                    del data['DailyQuiz'][user_id]
                    del data['withd'][user_id]
                    del data['id'][user_id]
                    del data['refer'][user_id]
            save_users_data(data)

        bot.send_message(OWNER_ID, f"🎉 Broadcast yakunlandi!\n✅ Muvafaqiyatli: {success_count}\n❌ Muvaffaqiyatsiz: {fail_count}\n🚫 Bloklangan: {len(blocked_users)}")
        menu(OWNER_ID)

    except Exception as e:
        bot.reply_to(message, f"⚠️ Xatolik: {str(e)}")
        bot.send_message(OWNER_ID, f"⚠️ Broadcast xatoligi: {str(e)}")

# Matnli xabarlar
@bot.message_handler(content_types=['text'])
def send_text(message):
    try:
        user_id = message.chat.id
        text = message.text
        message_id = message.message_id

        if text == "✅ Obunani tekshirish":
            if check(user_id):
                data = load_users_data()
                user = str(user_id)
                username = message.from_user.username or message.from_user.first_name
                
                if user not in data['refer']:
                    data['refer'][user] = True
                    if user not in data['referby']:
                        data['referby'][user] = user
                    if int(data['referby'][user]) != user_id:
                        ref_id = data['referby'][user]
                        data['balance'][ref_id] = data['balance'].get(ref_id, 0) + Per_Refer
                        data['referred'][ref_id] = data['referred'].get(ref_id, 0) + 1
                        bot.send_message(ref_id, f"🎁 Do‘stingiz qo‘shildi! Sizga +{Per_Refer} {TOKEN}!")
                    save_users_data(data)

                markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
                markup.add(telebot.types.KeyboardButton("📞 Raqamni ulashish", request_contact=True))
                try:
                    bot.edit_message_text(f"👋 Salom, @{username}! Telefon raqamingizni ulashing:", user_id, message_id, reply_markup=markup)
                except:
                    bot.send_message(user_id, f"👋 Salom, @{username}! Telefon raqamingizni ulashing:", reply_markup=markup)
            else:
                markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
                markup.add(telebot.types.KeyboardButton("✅ Obunani tekshirish"))
                try:
                    bot.edit_message_text("🤖 Kanalga qo‘shiling: @medstone_usmle", user_id, message_id, reply_markup=markup)
                except:
                    bot.send_message(user_id, "🤖 Kanalga qo‘shiling: @medstone_usmle", reply_markup=markup)

        elif text == "👤 Hisobim":
            data = load_users_data()
            username = message.from_user.username or message.from_user.first_name
            balance = data['balance'].get(str(user_id), 0)
            try:
                bot.edit_message_text(f"👤 @{username}\n💰 Balans: {balance} {TOKEN}", user_id, message_id)
            except:
                bot.send_message(user_id, f"👤 @{username}\n💰 Balans: {balance} {TOKEN}")
            menu(user_id, message_id)

        elif text == "🔗 Taklif linki":
            send_invite_link(user_id, message_id)

        elif text == "🎁 Sovg‘alar":
            subjects_menu(user_id, message_id)

        elif text == "📚 Fanlar":
            subjects_menu(user_id, message_id)

        elif text == "📊 Statistika" and user_id == OWNER_ID:
            data = load_users_data()
            try:
                bot.edit_message_text(f"📈 Jami foydalanuvchilar: {data['total']}", user_id, message_id)
            except:
                bot.send_message(user_id, f"📈 Jami foydalanuvchilar: {data['total']}")
            menu(user_id, message_id)

        elif text == "📢 Broadcast" and user_id == OWNER_ID:
            handle_broadcast(message)

        elif text.startswith("🎓 "):
            subject_name = text.replace("🎓 ", "")
            subject_key = next((key for key, info in SUBJECTS.items() if info['name'] == subject_name), None)
            if subject_key:
                send_gift_video(user_id, subject_key, message_id)
            else:
                try:
                    bot.edit_message_text("⚠️ Noto‘g‘ri fan tanlandi!", user_id, message_id)
                except:
                    bot.send_message(user_id, "⚠️ Noto‘g‘ri fan tanlandi!")
                menu(user_id, message_id)

        elif text == "⬅️ Ortga":
            menu(user_id, message_id)

        else:
            try:
                bot.edit_message_text("⚠️ Iltimos, menyudan tugma tanlang!", user_id, message_id)
            except:
                bot.send_message(user_id, "⚠️ Iltimos, menyudan tugma tanlang!")
            menu(user_id, message_id)

    except Exception as e:
        bot.send_message(user_id, "⚠️ Xatolik! Keyinroq urinib ko‘ring.")
        bot.send_message(OWNER_ID, f"⚠️ Text xatoligi: {str(e)}")

# Kanal videolarini qayta ishlash
@bot.channel_post_handler(content_types=['video'])
def handle_channel_video_post(message):
    try:
        if message.chat.username != "marafonbotbazasi":
            return

        file_id = message.video.file_id
        caption = message.caption.strip().lower() if message.caption else None

        if not caption:
            bot.send_message(OWNER_ID, "⚠️ Videoda caption yo‘q!")
            return

        subject_key = None
        index = None
        for key in SUBJECTS.keys():
            if f'#{key}' in caption:
                subject_key = key
                index_part = caption.replace(f'#{key}', '').strip()
                index = index_part if index_part.isdigit() else '1'
                break
        if not subject_key or not index:
            bot.send_message(OWNER_ID, f"⚠️ Captionda noto‘g‘ri teglar: {caption}")
            return

        catalog = load_video_catalog()
        key = f"{subject_key}_{index}"
        if key in catalog:
            bot.send_message(OWNER_ID, f"⚠️ {subject_key} {index}-dars allaqachon mavjud!")
            return

        catalog[key] = file_id
        if save_video_catalog(catalog):
            bot.send_message(OWNER_ID, f"✅ {subject_key} {index}-dars saqlandi.")
        else:
            bot.send_message(OWNER_ID, "❌ Saqlashda xatolik!")

    except Exception as e:
        bot.send_message(OWNER_ID, f"❌ Video yozishda xatolik: {e}")

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)

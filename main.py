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
    "biochemistry": {"name": "Biochemistry", "category": "GENERAL PRINCIPLES"},
    "immunology": {"name": "Immunology", "category": "GENERAL PRINCIPLES"},
    "microbiology": {"name": "Microbiology", "category": "GENERAL PRINCIPLES"},
    "pathology": {"name": "Pathology", "category": "GENERAL PRINCIPLES"},
    "pharmacology": {"name": "Pharmacology", "category": "GENERAL PRINCIPLES"},
    "public_health_sciences": {"name": "Public Health Sciences", "category": "GENERAL PRINCIPLES"},
    "cardiovascular": {"name": "Cardiovascular", "category": "ORGAN SYSTEMS"},
    "endocrine": {"name": "Endocrine", "category": "ORGAN SYSTEMS"},
    "gastrointestinal": {"name": "Gastrointestinal", "category": "ORGAN SYSTEMS"},
    "hematology_oncology": {"name": "Hematology and Oncology", "category": "ORGAN SYSTEMS"},
    "musculoskeletal_skin_connective": {"name": "Musculoskeletal, Skin, and Connective Tissue", "category": "ORGAN SYSTEMS"},
    "neurology_special_senses": {"name": "Neurology and Special Senses", "category": "ORGAN SYSTEMS"},
    "psychiatry": {"name": "Psychiatry", "category": "ORGAN SYSTEMS"},
    "renal": {"name": "Renal", "category": "ORGAN SYSTEMS"},
    "reproductive": {"name": "Reproductive", "category": "ORGAN SYSTEMS"},
    "respiratory": {"name": "Respiratory", "category": "ORGAN SYSTEMS"}
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
    markup.row("📚 Fanlar")
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

# Toifalar menyusi
def categories_menu(user_id, message_id=None):
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    markup.add("GENERAL PRINCIPLES", "ORGAN SYSTEMS")
    markup.row("⬅️ Ortga")
    
    text = "📚 Toifa tanlang:"
    if message_id:
        try:
            bot.edit_message_text(text, user_id, message_id, reply_markup=markup)
        except:
            bot.send_message(user_id, text, reply_markup=markup)
    else:
        bot.send_message(user_id, text, reply_markup=markup)

# Fanlar menyusi
def subjects_menu(user_id, category, message_id=None):
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    subject_buttons = [f"📖 {info['name']}" for key, info in SUBJECTS.items() if info['category'] == category]
    for i in range(0, len(subject_buttons), 2):
        markup.row(*subject_buttons[i:i+2])
    markup.row("⬅️ Ortga")
    
    # Har bir fan bo‘yicha darslar sonini hisoblash
    catalog = load_video_catalog()
    lessons_count = {subject: 0 for subject in SUBJECTS}
    for key in catalog:
        subject_key = key.split('_')[0]
        if subject_key in lessons_count:
            lessons_count[subject_key] += 1
    
    text = f"📚 {category} fanlarini tanlang:\n\n"
    for subject_key, info in SUBJECTS.items():
        if info['category'] == category:
            text += f"📖 {info['name']} ({lessons_count.get(subject_key, 0)} ta dars)\n\n"
    
    if message_id:
        try:
            bot.edit_message_text(text, user_id, message_id, reply_markup=markup)
        except:
            bot.send_message(user_id, text, reply_markup=markup)
    else:
        bot.send_message(user_id, text, reply_markup=markup)

# Fan videolarini inline tugmalar sifatida ko‘rsatish
def show_subject_videos(user_id, subject, message_id=None):
    data = load_users_data()
    catalog = load_video_catalog(subject)
    user_id_str = str(user_id)
    balance = data['balance'].get(user_id_str, 0)
    free_video_accessed = data['free_video_accessed'].get(user_id_str, {})
    
    lessons_count = len([key for key in catalog if key.startswith(subject.lower())])
    available_videos = 0 if free_video_accessed.get(subject, False) else 1  # Bepul video hali olinmagan bo‘lsa
    available_videos += balance // 3  # Har 3 ball uchun 1 video
    
    text = f"📚 {SUBJECTS[subject]['name']} bo‘yicha darslar ({lessons_count} ta):\n\n"
    text += f"💰 Sizda {available_videos} ta darsga kirish imkoni bor.\n\n"
    text += "Ko‘proq videolarni qo‘lga kiritish uchun do‘stlaringizni taklif qiling yoki barcha videolarni hoziroq qo‘lga kiritish uchun obunani xarid qiling!"
    
    markup = telebot.types.InlineKeyboardMarkup(row_width=3)
    for i in range(1, lessons_count + 1):
        video_index = str(i)
        key = f"{subject.lower()}_{video_index}"
        if key in catalog:
            if i == 1 and not free_video_accessed.get(subject, False):
                markup.add(telebot.types.InlineKeyboardButton(f"📽️ Dars {i}", callback_data=f"video_{subject}_{i}"))
            elif i <= available_videos + 1:  # +1 chunki bepul video hisobga olinadi
                markup.add(telebot.types.InlineKeyboardButton(f"📽️ Dars {i}", callback_data=f"video_{subject}_{i}"))
            else:
                markup.add(telebot.types.InlineKeyboardButton(f"🔒 Dars {i}", callback_data=f"locked_{subject}_{i}"))
    markup.add(telebot.types.InlineKeyboardButton("⬅️ Ortga", callback_data=f"back_to_subjects_{SUBJECTS[subject]['category']}"))
    
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
            "balance": {}, "withd": {}, "id": {}, "refer": {},
            "phone_number": {}, "username": {}, "total": 0, "free_video_accessed": {}
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
            data['phone_number'][user_id] = row.get('phone_number', '')
            data['username'][user_id] = row.get('username', '')
            try:
                data['free_video_accessed'][user_id] = json.loads(row.get('free_video_accessed', '{}')) if row.get('free_video_accessed') else {}
            except json.JSONDecodeError:
                data['free_video_accessed'][user_id] = {}
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
        headers = ['user_id', 'referred', 'referby', 'checkin', 'DailyQuiz', 'balance', 'withd', 'id', 'refer', 'phone_number', 'username', 'free_video_accessed']
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
                data['refer'].get(user_id, False),
                data['phone_number'].get(user_id, ''),
                data['username'].get(user_id, ''),
                json.dumps(data['free_video_accessed'].get(user_id, {}))
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
        headers = ['user_id', 'referred', 'referby', 'checkin', 'DailyQuiz', 'balance', 'withd', 'id', 'refer', 'phone_number', 'username', 'free_video_accessed']
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
                data['refer'].get(user_id, False),
                data['phone_number'].get(user_id, ''),
                data['username'].get(user_id, ''),
                json.dumps(data['free_video_accessed'].get(user_id, {}))
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
        bot.send_video(user_id, video_file_id, supports_streaming=True, protect_content=True)
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

# Inline tugma callbacklarini qayta ishlash
@bot.callback_query_handler(func=lambda call: True)
def handle_video_callback(call):
    user_id = call.from_user.id
    data = call.data
    message_id = call.message.message_id

    if data.startswith("video_"):
        _, subject, video_index = data.split("_")
        send_gift_video(user_id, subject, video_index, message_id)
    elif data.startswith("locked_"):
        _, subject, video_index = data.split("_")
        text = f"🔒 {SUBJECTS[subject]['name']} {video_index}-dars uchun ballaringiz yetarli emas!\n\nDo‘stlaringizni taklif qilib hisobingizni to‘ldiring yoki hoziroq obunani xarid qiling!"
        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton("💳 Obuna xarid qilish", url="https://t.me/medstone_usmle_admin"))
        try:
            bot.edit_message_text(text, user_id, message_id, reply_markup=markup)
        except:
            bot.send_message(user_id, text, reply_markup=markup)
    elif data.startswith("back_to_subjects_"):
        _, category = data.split("_", 1)
        subjects_menu(user_id, category, message_id)

# Sovg‘a videolarini yuborish
def send_gift_video(user_id, subject, video_index, message_id=None):
    data = load_users_data()
    catalog = load_video_catalog(subject)
    user_id_str = str(user_id)
    balance = data['balance'].get(user_id_str, 0)
    free_video_accessed = data['free_video_accessed'].get(user_id_str, {})
    
    key = f"{subject.lower()}_{video_index}"
    if key not in catalog:
        text = f"⚠️ {SUBJECTS[subject]['name']} {video_index}-dars topilmadi!"
        if message_id:
            try:
                bot.edit_message_text(text, user_id, message_id)
            except:
                bot.send_message(user_id, text)
        else:
            bot.send_message(user_id, text)
        show_subject_videos(user_id, subject, message_id)
        return

    # Bepul video yoki balans tekshiruvi
    if video_index == "1" and not free_video_accessed.get(subject, False):
        bot.send_video(user_id, catalog[key], supports_streaming=True, protect_content=True)
        free_video_accessed[subject] = True
        data['free_video_accessed'][user_id_str] = free_video_accessed
        save_users_data(data)
        text = f"🎥 {SUBJECTS[subject]['name']} {video_index}-dars jo‘natildi!\n\nKo‘proq videolarni qo‘lga kiritish uchun do‘stlaringizni taklif qiling yoki barcha videolarni hoziroq qo‘lga kiritish uchun obunani xarid qiling!"
    elif int(video_index) <= (balance // 3) + (1 if not free_video_accessed.get(subject, False) else 0) + 1:
        bot.send_video(user_id, catalog[key], supports_streaming=True, protect_content=True)
        text = f"🎥 {SUBJECTS[subject]['name']} {video_index}-dars jo‘natildi!\n\nKo‘proq videolarni qo‘lga kiritish uchun do‘stlaringizni taklif qiling yoki barcha videolarni hoziroq qo‘lga kiritish uchun obunani xarid qiling!"
    else:
        text = f"🔒 {SUBJECTS[subject]['name']} {video_index}-dars uchun ballaringiz yetarli emas!\n\nDo‘stlaringizni taklif qilib hisobingizni to‘ldiring yoki hoziroq obunani xarid qiling!"
        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton("💳 Obuna xarid qilish", url="https://t.me/medstone_usmle_admin"))
        if message_id:
            try:
                bot.edit_message_text(text, user_id, message_id, reply_markup=markup)
            except:
                bot.send_message(user_id, text, reply_markup=markup)
        else:
            bot.send_message(user_id, text, reply_markup=markup)
        show_subject_videos(user_id, subject, message_id)
        return

    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton("💳 Obuna xarid qilish", url="https://t.me/medstone_usmle_admin"))
    if message_id:
        try:
            bot.edit_message_text(text, user_id, message_id, reply_markup=markup)
        except:
            bot.send_message(user_id, text, reply_markup=markup)
    else:
        bot.send_message(user_id, text, reply_markup=markup)
    show_subject_videos(user_id, subject, message_id)

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
        if user_id not in data['phone_number']:
            data['phone_number'][user_id] = ''
        if user_id not in data['username']:
            data['username'][user_id] = message.from_user.username or message.from_user.first_name
        if user_id not in data['free_video_accessed']:
            data['free_video_accessed'][user_id] = {}
        save_users_data(data)

        markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(telebot.types.KeyboardButton("✅ Obunani tekshirish"))
        msg_start = """🎉 Medstone Marafon botga xush kelibsiz!\n\n📚 USMLE step 1 ga tegishli barcha fanlar bo‘yicha birinchi darslarni mutlaqo bepul qo‘lga kiritish imkoniyati!\n\n👇 Lekin avval kanalga qo‘shiling:\n\n@medstone_usmle"""
        bot.send_message(message.chat.id, msg_start, reply_markup=markup)
    except Exception as e:
        bot.send_message(message.chat.id, "⚠️ Xatolik!\n\nKeyinroq qayta urinib ko‘ring.")
        bot.send_message(OWNER_ID, f"⚠️ /start xatoligi: {str(e)}")

# Kontakt ma'lumotlari
@bot.message_handler(content_types=['contact'])
def contact(message):
    if message.contact:
        user_id = str(message.chat.id)
        contact = message.contact.phone_number
        username = message.from_user.username or message.from_user.first_name
        bot.send_message(ADMIN_GROUP_USERNAME, f"👤 @{username}\n\n📞 Raqam: {contact}")
        
        # Google Sheets'ga telefon raqami va username'ni yozish
        data = load_users_data()
        data['phone_number'][user_id] = contact
        data['username'][user_id] = username
        save_users_data(data)
        
        msg = """🎉 Endi barcha fanlar bo‘yicha 1-dars mutlaqo bepul!\n\n📚 Fanlar bo‘limidan darslarni yuklab oling!\n\n🔥 3 ta do‘st taklif qiling – 1 ta qo‘shimcha dars BEPUL!\n6 ta do‘st – 2 ta dars!\n9 ta do‘st – 3 ta dars!\n\nKo‘proq do‘st taklif qiling, butun kursni BEPUL oling!"""
        bot.send_message(message.chat.id, msg)
        menu(message.chat.id)

# Taklif linkini yuborish
def send_invite_link(user_id, message_id=None):
    data = load_users_data()
    bot_name = bot.get_me().username
    user = str(user_id)

    if user not in data['referred']:
        data['referred'][user] = 0
        data['username'][user] = bot.get_chat(user_id).username or bot.get_chat(user_id).first_name
        data['free_video_accessed'][user] = {}
    save_users_data(data)

    ref_link = f"https://telegram.me/{bot_name}?start={user_id}"
    msg = f"Tibbiyot bo‘yicha barcha fanlarni qamrab olgan Medstone Academy barcha kurslarni mutlaqo bepul tarqatmoqda!\n\n📚 Do‘stlaringizni taklif qiling va BEPUL darslar oling!\n\n🔗 Taklif havolangiz: {ref_link}\n\n"
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
        bot.send_message(message.chat.id, f"⚠️ Xatolik!\n\n{str(e)}")
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
                bot.reply_to(message, "⚠️ Filtr xato!\n\n/filter <ball> formatidan foydalaning.")
                return

        if not user_ids:
            bot.reply_to(message, "🚫 Foydalanuvchilar topilmadi!")
            return

        success_count = 0
        fail_count = 0
        blocked_users = []

        bot.reply_to(message, f"📢 Broadcast boshlandi.\n\nJami {len(user_ids)} foydalanuvchi.")

        for user_id in user_ids:
            try:
                if broadcast_type == 'text':
                    bot.send_message(int(user_id), message.text)
                elif broadcast_type == 'photo' and message.photo:
                    caption = message.caption or ""
                    bot.send_photo(int(user_id), message.photo[-1].file_id, caption=caption)
                elif broadcast_type == 'video' and message.video:
                    caption = message.caption or ""
                    bot.send_video(int(user_id), message.video.file_id, caption=caption, protect_content=True)
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
                    del data['phone_number'][user_id]
                    del data['username'][user_id]
                    del data['free_video_accessed'][user_id]
            save_users_data(data)

        bot.send_message(OWNER_ID, f"🎉 Broadcast yakunlandi!\n\n✅ Muvafaqiyatli: {success_count}\n\n❌ Muvaffaqiyatsiz: {fail_count}\n\n🚫 Bloklangan: {len(blocked_users)}")
        menu(OWNER_ID)

    except Exception as e:
        bot.reply_to(message, f"⚠️ Xatolik!\n\n{str(e)}")
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
                        bot.send_message(ref_id, f"🎁 Do‘stingiz qo‘shildi!\n\nSizga +{Per_Refer} {TOKEN}!")
                    data['username'][user] = username
                    data['free_video_accessed'][user] = {}
                    save_users_data(data)

                markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
                markup.add(telebot.types.KeyboardButton("📞 Raqamni ulashish", request_contact=True))
                try:
                    bot.edit_message_text(f"👋 Salom, @{username}!\n\nTelefon raqamingizni ulashing:", user_id, message_id, reply_markup=markup)
                except:
                    bot.send_message(user_id, f"👋 Salom, @{username}!\n\nTelefon raqamingizni ulashing:", reply_markup=markup)
            else:
                markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
                markup.add(telebot.types.KeyboardButton("✅ Obunani tekshirish"))
                try:
                    bot.edit_message_text("🤖 Kanalga qo‘shiling:\n\n@medstone_usmle", user_id, message_id, reply_markup=markup)
                except:
                    bot.send_message(user_id, "🤖 Kanalga qo‘shiling:\n\n@medstone_usmle", reply_markup=markup)

        elif text == "👤 Hisobim":
            data = load_users_data()
            username = message.from_user.username or message.from_user.first_name
            balance = data['balance'].get(str(user_id), 0)
            try:
                bot.edit_message_text(f"👤 @{username}\n\n💰 Balans: {balance} {TOKEN}", user_id, message_id)
            except:
                bot.send_message(user_id, f"👤 @{username}\n\n💰 Balans: {balance} {TOKEN}")
            menu(user_id, message_id)

        elif text == "🔗 Taklif linki":
            send_invite_link(user_id, message_id)

        elif text == "📚 Fanlar":
            categories_menu(user_id, message_id)

        elif text in ["GENERAL PRINCIPLES", "ORGAN SYSTEMS"]:
            subjects_menu(user_id, text, message_id)

        elif text == "📊 Statistika" and user_id == OWNER_ID:
            data = load_users_data()
            try:
                bot.edit_message_text(f"📈 Jami foydalanuvchilar:\n\n{data['total']}", user_id, message_id)
            except:
                bot.send_message(user_id, f"📈 Jami foydalanuvchilar:\n\n{data['total']}")
            menu(user_id, message_id)

        elif text == "📢 Broadcast" and user_id == OWNER_ID:
            handle_broadcast(message)

        elif text.startswith("📖 "):
            subject_name = text.replace("📖 ", "")
            subject_key = next((key for key, info in SUBJECTS.items() if info['name'] == subject_name), None)
            if subject_key:
                show_subject_videos(user_id, subject_key, message_id)
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
        bot.send_message(user_id, "⚠️ Xatolik!\n\nKeyinroq qayta urinib ko‘ring.")
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
            bot.send_message(OWNER_ID, f"⚠️ Captionda noto‘g‘ri teglar:\n\n{caption}")
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
        bot.send_message(OWNER_ID, f"❌ Video yozishda xatolik:\n\n{e}")

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)

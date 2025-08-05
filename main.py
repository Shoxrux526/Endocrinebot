import json
import telebot
from flask import Flask, request
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type
import logging

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
    sheet = client.open(SPREADSHEET_NAME).sheet1  # Foydalanuvchilar uchun asosiy varaq
    backup_sheet = client.open(SPREADSHEET_NAME).get_worksheet(1)  # Foydalanuvchilar uchun backup varaq (indeks 1)
    video_catalog_sheet = client.open(SPREADSHEET_NAME).get_worksheet(2)  # Video katalogi uchun alohida varaq (indeks 2)
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
    for i in CHANNELS:
        check = bot.get_chat_member(i, id)
        if check.status != 'left':
            pass
        else:
            return False
    return True

bonus = {}

def menu(id):
    keyboard = telebot.types.ReplyKeyboardMarkup(True)
    keyboard.row('🆔 Mening hisobim')
    keyboard.row('🙌🏻 Maxsus linkim')
    keyboard.row('🎁 Mening sovg\'am')
    if id == OWNER_ID:
        keyboard.row('📊 Statistika')
        keyboard.row('📢 Broadcast')
    bot.send_message(id, "🏠 Asosiy menyu ⬇️", reply_markup=keyboard)

# Google Sheets-dan foydalanuvchilar ma'lumotlarini yuklash (retry bilan)
@retry(stop=stop_after_attempt(3), wait=wait_fixed(2), retry=retry_if_exception_type(Exception))
def load_users_data():
    try:
        records = sheet.get_all_records()
        data = {
            "referred": {},
            "referby": {},
            "checkin": {},
            "DailyQuiz": {},
            "balance": {},
            "withd": {},
            "id": {},
            "total": 0,
            "refer": {}
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

# Foydalanuvchilar uchun backup funksiyasi (retry bilan)
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

# Foydalanuvchilar uchun Google Sheets-ga ma'lumotlarni saqlash (backup bilan, retry bilan)
@retry(stop=stop_after_attempt(3), wait=wait_fixed(2), retry=retry_if_exception_type(Exception))
def save_users_data(data):
    try:
        if not data['referred']:
            logging.warning("Data is empty, skipping save to avoid data loss")
            return
        backup_users_data(data)  # Har safar saqlashdan oldin backup
        logging.info(f"Saving data for {len(data['referred'])} users to Google Sheets")
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

def send_videos(user_id, video_file_ids):
    for video_file_id in video_file_ids:
        bot.send_video(user_id, video_file_id, supports_streaming=True)

# Video katalogini Google Sheets-dan yuklash (retry bilan)
@retry(stop=stop_after_attempt(3), wait=wait_fixed(2), retry=retry_if_exception_type(Exception))
def load_video_catalog():
    try:
        records = video_catalog_sheet.get_all_records()
        catalog = {}
        for row in records:
            index = str(row.get('index', ''))
            file_id = row.get('file_id', '')
            if index and file_id:
                catalog[index] = file_id
        logging.info(f"Loaded video catalog with {len(catalog)} entries from Google Sheets")
        return catalog
    except Exception as e:
        logging.error(f"❌ Error loading video catalog from Google Sheets: {e}")
        return {}

# Video katalogini Google Sheets-ga saqlash (retry bilan)
@retry(stop=stop_after_attempt(3), wait=wait_fixed(2), retry=retry_if_exception_type(Exception))
def save_video_catalog(data):
    try:
        headers = ['index', 'file_id']
        all_data = [headers]
        for index, file_id in data.items():
            all_data.append([index, file_id])
        video_catalog_sheet.update(values=all_data, range_name='A1')
        logging.info(f"Video catalog saved successfully with {len(data)} entries to Google Sheets")
        return True
    except Exception as e:
        logging.error(f"❌ Error saving video catalog to Google Sheets: {e}")
        return False

def send_gift_video(user_id):
    data = load_users_data()
    catalog = load_video_catalog()
    balance = data['balance'].get(str(user_id), 0)
    video_count = balance // 5  # Har 5 ball uchun 1 video
    sent_videos = []

    if video_count == 0:
        bot.send_message(user_id, '⚠️ Kechirasiz, ballaringiz yetarli emas. Do‘stlaringizni taklif qilib, ball to‘plang! 🚀')
        return

    for i in range(1, video_count + 1):
        video_index = str(i)
        if video_index in catalog:
            bot.send_video(user_id, catalog[video_index], supports_streaming=True)
            sent_videos.append(video_index)
        else:
            bot.send_message(user_id, f"⚠️ {video_index}-dars video topilmadi. Admin bilan bog‘laning!")
            return

    if sent_videos:
        bot.send_message(user_id, f"🎥 {', '.join(sent_videos)}-dars videolar sizga jo‘natildi! {'Ajoyib natija!' if video_count >= 3 else 'Ko‘proq darslar uchun do‘stlaringizni taklif qiling!'} 🚀")
    else:
        bot.send_message(user_id, '⚠️ Hech qanday video topilmadi. Admin bilan bog‘laning!')

@bot.message_handler(commands=['start'])
def start(message):
    try:
        user = message.chat.id
        msg = message.text
        user = str(user)
        data = load_users_data()
        referrer = None if msg == '/start' else msg.split()[1]

        if user not in data['referred']:
            data['referred'][user] = 0
            data['total'] = len(data['referred'])
        if user not in data['referby']:
            data['referby'][user] = referrer if referrer else user
            if referrer and referrer in data['referred']:
                data['referred'][referrer] += 1
                data['balance'][referrer] = data['balance'].get(referrer, 0) + Per_Refer
        if user not in data['checkin']:
            data['checkin'][user] = 0
        if user not in data['DailyQuiz']:
            data['DailyQuiz'][user] = "0"
        if user not in data['balance']:
            data['balance'][user] = 0
        if user not in data['withd']:
            data['withd'][user] = 0
        if user not in data['id']:
            data['id'][user] = len(data['referred'])
        save_users_data(data)
        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton(
            text='📢 Marafon kanaliga qo‘shilish', url='https://t.me/medstone_usmle'))
        markup.add(telebot.types.InlineKeyboardButton(
            text='✅ Obunani tekshirish', callback_data='check'))
        msg_start = """🎉 Tabriklaymiz! Siz marafon qatnashchisi bo‘lishga juda yaqin qoldingiz!  

📚 Immunologiya bo‘yicha 7 kunlik BEPUL marafon davomida quyidagi mavzularni o‘rganamiz:  
\n\n✅ Qon hosil bo‘lishi va uning klinik ahamiyati  
\n✅ Suyak iligi ko‘chirib o‘tkazish  
\n✅ Suyak ko‘migi tuzilishi va uning klinik ahamiyati  
\n✅ Qon hosil bo'lish bilan bog‘liq kasalliklar  
\n✅ Anemiya turlari  

✨ Shu mavzulardagi eng so‘nggi yangiliklarni o‘zlashtirishni xohlasangiz, hoziroq marafon bo‘lib o‘tadigan kanalga qo‘shiling!"""
        bot.send_message(user, msg_start, reply_markup=markup)
    except Exception as e:
        bot.send_message(message.chat.id, "⚠️ Bu buyruqda xatolik yuz berdi, iltimos, admin xatoni tuzatishini kuting!")
        bot.send_message(OWNER_ID, f"⚠️ Botingizda xatolik: {str(e)}")

@bot.callback_query_handler(func=lambda call: call.data in ['account', 'ref_link', 'gift'])
def account_or_ref_link_handler(call):
    try:
        user_id = call.message.chat.id
        data = load_users_data()
        user = str(user_id)
        username = call.message.chat.username if call.message.chat.username else call.message.chat.first_name

        if call.data == 'account':
            balance = data['balance'].get(user, 0)
            markup = telebot.types.InlineKeyboardMarkup()
            markup.add(telebot.types.InlineKeyboardButton(text=f"💰 Balans: {balance} Ball", callback_data='balance'))
            msg = f"👤 Foydalanuvchi: @{username}\n💰 Balans: {balance} {TOKEN}"
            bot.send_message(call.message.chat.id, msg, reply_markup=markup)

        elif call.data == 'ref_link':
            send_invite_link(call.message.chat.id)

        elif call.data == 'gift':
            send_gift_video(user_id)

    except Exception as e:
        bot.send_message(call.message.chat.id, "⚠️ Bu buyruqda xatolik yuz berdi, iltimos, admin xatoni tuzatishini kuting!")
        bot.send_message(OWNER_ID, f"⚠️ Botingizda xatolik: {str(e)}")

@bot.callback_query_handler(func=lambda call: True)
def query_handler(call):
    try:
        ch = check(call.message.chat.id)
        if call.data == 'check':
            if ch:
                data = load_users_data()
                user_id = call.message.chat.id
                user = str(user_id)
                username = call.message.chat.username if call.message.chat.username else call.message.chat.first_name
                bot.answer_callback_query(callback_query_id=call.id, text='🎉 Siz kanalga qo‘shildingiz! Omad tilaymiz!')

                if user not in data['refer']:
                    data['refer'][user] = True

                    if user not in data['referby']:
                        data['referby'][user] = user
                    if int(data['referby'][user]) != user_id:
                        ref_id = data['referby'][user]
                        ref = str(ref_id)
                        if ref not in data['balance']:
                            data['balance'][ref] = 0
                        if ref not in data['referred']:
                            data['referred'][ref] = 0
                        data['balance'][ref] += Per_Refer
                        data['referred'][ref] += 1
                        bot.send_message(
                            ref_id,
                            f"🎁 Do‘stingiz kanalga qo‘shildi va siz +{Per_Refer} {TOKEN} ishlab oldingiz!"
                        )
                    save_users_data(data)

                markup = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
                markup.add(telebot.types.KeyboardButton(text='📞 Raqamni ulashish', request_contact=True))
                bot.send_message(call.message.chat.id, f"👋 Salom, @{username}! \nSizga bonuslarimizni bera olishimiz uchun telefon raqamingizni tasdiqlay olasizmi? \n\n⬇️ Buning uchun pastdagi tugmani bossangiz kifoya!", reply_markup=markup)
            else:
                bot.answer_callback_query(callback_query_id=call.id, text='⚠️ Siz hali kanalga qo‘shilmadingiz!')
                markup = telebot.types.InlineKeyboardMarkup()
                markup.add(telebot.types.InlineKeyboardButton(
                    text='✅ Obunani tekshirish', callback_data='check'))
                msg_start = "🤖 Ushbu botdan foydalanish uchun quyidagi kanalga qo‘shiling va Obunani tekshirish tugmasini bosing: \n\n📢 @medstone_usmle"
                bot.send_message(call.message.chat.id, msg_start, reply_markup=markup)
    except Exception as e:
        bot.send_message(call.message.chat.id, "⚠️ Bu buyruqda xatolik yuz berdi, iltimos, admin xatoni tuzatishini kuting!")
        bot.send_message(OWNER_ID, f"⚠️ Botingizda xatolik: {str(e)}")

@bot.message_handler(content_types=['contact'])
def contact(message):
    if message.contact is not None:
        contact = message.contact.phone_number
        username = message.from_user.username if message.from_user.username else message.from_user.first_name
        bot.send_message(ADMIN_GROUP_USERNAME, f"👤 Foydalanuvchi: @{username}\n📞 Telefon raqami: {contact}")

        inline_markup = telebot.types.InlineKeyboardMarkup()
        inline_markup.add(telebot.types.InlineKeyboardButton(text="🎁 Sovg‘angizni oling!", callback_data='gift'))
        gift_message = """🎉 Siz uchun maxsus tayyorlangan sovg‘alarni kutib oling!  

1️⃣ Medstone kanalining barcha a‘zolari, Shoxrux Botirov tomonidan tayyorlangan bonus video dars ni mehmondo‘stligimiz ramzi sifatida yuklab olishlari mumkin!\nBuning uchun pastdagi "Mening sovg‘am🎁" tugmasini bosing.  

2️⃣ 5 ta do‘stingizni taklif qiling va avval 650 ming so‘mdan sotilgan leksiyalar to‘plamidan 1 ta dolzarb mavzu ni BEPUL yutib oling!  

3️⃣ 10 ta do‘stingizni taklif qiling – 2 ta video dars ni case tahlillari bilan birga BEPUL qo‘lga kiriting!  

4️⃣ 15 ta do‘stingizni taklif qiling – 3 ta dars ni batafsil case tahlillari bilan BEPUL yutib oling!  

🔥 Har safar 5 ta do‘stingiz sizning havolangiz orqali kanalga qo‘shilsa, yangi video leksiyalarni qo‘lga kiritaverasiz – hatto butun kursni ham BEPUL olishingiz mumkin!  

📎 Maxsus linkingizni oling va do‘stlaringizni jamoamizga taklif qiling! Bu faqat sizga tegishli havola bo‘lib, har bir do‘stingiz sizga 1 ball olib keladi.  

⬇️ "Maxsus linkim" tugmasini bosing va linkingizni oling!  

📊 Ballaringizni esa "Mening hisobim" tugmasi orqali kuzatib borishingiz mumkin!"""
        bot.send_message(message.chat.id, gift_message, reply_markup=inline_markup)
        menu(message.chat.id)

def send_invite_link(user_id):
    data = load_users_data()
    bot_name = bot.get_me().username
    user = str(user_id)

    if user not in data['referred']:
        data['referred'][user] = 0
    save_users_data(data)

    ref_link = f'https://telegram.me/{bot_name}?start={user_id}'
    msg = (f"📚 Immunologiya bo‘yicha OCHIQ DARSLAR \n\n" \
           f"✨ USMLE Step 1 asosidagi unikal kurslar asosida tayyorlangan BEPUL marafon da qatnashmoqchi bo‘lsangiz, quyidagi havola orqali jamoamizga qo‘shiling! \n\n" \
           f"⏳ Vaqt va joylar chegaralangan – shoshiling! \n\n" \
           f"👩‍⚕️ Marafon bakalavr, ordinator va shifokorlar uchun mo‘ljallangan va butunlay bepul! \n\n" \
           f"🔗 Taklif havolangiz: {ref_link}")
    bot.send_message(user_id, msg)

@bot.message_handler(commands=['broadcast'])
def handle_broadcast(message):
    try:
        if message.chat.id != OWNER_ID:
            bot.reply_to(message, "🚫 Bu buyruq faqat admin uchun mavjud!")
            return
        
        markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        markup.add(
            telebot.types.KeyboardButton("✍️ Matn"),
            telebot.types.KeyboardButton("📸 Rasm"),
            telebot.types.KeyboardButton("🎥 Video")
        )
        bot.reply_to(message, "📢 Broadcast turini tanlang:", reply_markup=markup)
        
        bot.register_next_step_handler(message, process_broadcast_type)
        
    except Exception as e:
        bot.reply_to(message, f"⚠️ Xatolik yuz berdi: {str(e)}")
        bot.send_message(OWNER_ID, f"⚠️ Broadcast xatoligi: {str(e)}")

def process_broadcast_type(message):
    try:
        if message.chat.id != OWNER_ID:
            return
        
        broadcast_type = message.text
        if broadcast_type not in ["✍️ Matn", "📸 Rasm", "🎥 Video"]:
            bot.reply_to(message, "⚠️ Iltimos, to‘g‘ri tanlov qiling! Qayta urining:", reply_markup=telebot.types.ReplyKeyboardRemove())
            handle_broadcast(message)
            return

        if broadcast_type == "✍️ Matn":
            msg = bot.send_message(message.chat.id, "📝 Yuboriladigan matn ni kiriting (Markdown qo‘llab-quvvatlanadi):\nFiltrlash uchun: /filter <ball> (masalan, /filter 10)")
            bot.register_next_step_handler(msg, lambda m: process_broadcast(m, 'text'))
        elif broadcast_type == "📸 Rasm":
            msg = bot.send_message(message.chat.id, "📸 Yuboriladigan rasm ni yuklang va izoh qo‘shing (ixtiyoriy):")
            bot.register_next_step_handler(msg, lambda m: process_broadcast(m, 'photo'))
        elif broadcast_type == "🎥 Video":
            msg = bot.send_message(message.chat.id, "🎥 Yuboriladigan video ni yuklang va izoh qo‘shing (ixtiyoriy):")
            bot.register_next_step_handler(msg, lambda m: process_broadcast(m, 'video'))
        
    except Exception as e:
        bot.reply_to(message, f"⚠️ Xatolik yuz berdi: {str(e)}")
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
                bot.reply_to(message, "⚠️ Filtrda xato! /filter <ball> formatidan foydalaning.")
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

        result_msg = f"🎉 Broadcast yakunlandi!\n" \
                     f"✅ Muvafaqiyatli: {success_count}\n" \
                     f"❌ Muvaffaqiyatsiz: {fail_count}\n" \
                     f"🚫 Bloklangan foydalanuvchilar: {len(blocked_users)}"
        bot.send_message(OWNER_ID, result_msg)
        
        bot.send_message(OWNER_ID, "🏠 Broadcast yakunlandi. Asosiy menyuga qaytish:", reply_markup=telebot.types.ReplyKeyboardRemove())
        menu(OWNER_ID)

    except Exception as e:
        bot.reply_to(message, f"⚠️ Xatolik yuz berdi: {str(e)}")
        bot.send_message(OWNER_ID, f"⚠️ Broadcast xatoligi: {str(e)}")

@bot.message_handler(content_types=['text'])
def send_text(message):
    try:
        if message.text == '🆔 Mening hisobim':
            data = load_users_data()
            user_id = message.chat.id
            user = str(user_id)
            username = message.from_user.username if message.from_user.username else message.from_user.first_name
            balance = data['balance'].get(user, 0)
            markup = telebot.types.InlineKeyboardMarkup()
            markup.add(telebot.types.InlineKeyboardButton(text=f"💰 Balans: {balance} Ball", callback_data='balance'))
            msg = f"👤 Foydalanuvchi: @{username}\n💰 Balans: {balance} {TOKEN}"
            bot.send_message(message.chat.id, msg, reply_markup=markup)
        elif message.text == '🙌🏻 Maxsus linkim':
            send_invite_link(message.chat.id)
        elif message.text == '🎁 Mening sovg\'am':
            send_gift_video(message.chat.id)
        elif message.text == "📊 Statistika":
            if message.chat.id == OWNER_ID:
                user_id = message.chat.id
                data = load_users_data()
                msg = f"📈 Jami foydalanuvchilar: {data['total']} ta"
                bot.send_message(user_id, msg)
            else:
                bot.send_message(message.chat.id, "🚫 Ushbu buyruq faqat bot egasiga mavjud!")
        elif message.text == "📢 Broadcast":
            if message.chat.id == OWNER_ID:
                bot.send_message(message.chat.id, "📢 Broadcast uchun /broadcast buyrug‘ini ishlatishingiz mumkin!")
            else:
                bot.send_message(message.chat.id, "🚫 Bu buyruq faqat admin uchun!")
    except Exception as e:
        bot.send_message(message.chat.id, "⚠️ Bu buyruqda xatolik yuz berdi, iltimos, admin xatoni tuzatishini kuting!")
        bot.send_message(OWNER_ID, f"⚠️ Botingizda xatolik: {str(e)}")

@bot.channel_post_handler(content_types=['video'])
def handle_channel_video_post(message):
    try:
        # Faqat sizning kanalga tegishli postlar ishlovchi bo‘lishi kerak
        if message.chat.username != "marafonbotbazasi":
            return

        file_id = message.video.file_id
        caption = message.caption.strip() if message.caption else None

        if not caption or not caption.isdigit():
            bot.send_message(OWNER_ID, f"⚠️ Kanalga video yuklandi, lekin caption noto‘g‘ri edi: {caption}")
            return

        index = caption
        catalog = load_video_catalog()

        if index in catalog:
            bot.send_message(OWNER_ID, f"⚠️ {index}-raqamli video allaqachon mavjud! O‘zgartirmadi.")
            return

        catalog[index] = file_id
        saved = save_video_catalog(catalog)

        if saved:
            bot.send_message(OWNER_ID, f"✅ {index}-dars video Google Sheets'ga yozildi.")
        else:
            bot.send_message(OWNER_ID, "❌ Xatolik: Google Sheets'ga yozib bo‘lmadi.")

    except Exception as e:
        bot.send_message(OWNER_ID, f"❌ Kanaldan video yozishda xatolik: {e}")

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)

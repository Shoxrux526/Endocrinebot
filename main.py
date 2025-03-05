import json
import telebot
from flask import Flask, request
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
from dotenv import load_dotenv
import time

# Muhit o'zgaruvchilarini yuklash
load_dotenv()

# TOKEN DETAILS
TOKEN = "Ball"
BOT_TOKEN = os.getenv("BOT_TOKEN", "7559962637:AAH8Xyb4roZWJ061WEYT2a5TAB9Epq4uFN8")
PAYMENT_CHANNEL = "@medstone_usmle"
OWNER_ID = int(os.getenv("OWNER_ID", 725821571))
CHANNELS = ["@medstone_usmle"]
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
    sheet = client.open(SPREADSHEET_NAME).sheet1
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
    bot.send_message(id, "Asosiy menyu👇", reply_markup=keyboard)

# Google Sheets-dan ma'lumotlarni yuklash
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
            data['total'] = max(data['total'], row.get('id', 0))
        return data
    except Exception as e:
        print(f"Error loading data from Google Sheets: {e}")
        return {
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

# Google Sheets-ga ma'lumotlarni saqlash
def save_users_data(data):
    try:
        sheet.clear()
        headers = ['user_id', 'referred', 'referby', 'checkin', 'DailyQuiz', 'balance', 'withd', 'id', 'refer']
        sheet.append_row(headers)
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
            sheet.append_row(row)
    except Exception as e:
        print(f"Error saving data to Google Sheets: {e}")

def send_videos(user_id, video_file_ids):
    for video_file_id in video_file_ids:
        bot.send_video(user_id, video_file_id, supports_streaming=True)

def send_gift_video(user_id):
    data = load_users_data()
    balance = data['balance'].get(str(user_id), 0)
    if 0 <= balance < 10:
        video_file_ids = ["https://t.me/marafonbotbazasi/10", "https://t.me/marafonbotbazasi/11"]
        send_videos(user_id, video_file_ids)
        bot.send_message(user_id, '1-dars video sizga jo‘natildi.')
    elif 10 <= balance < 20:
        video_file_ids = ["https://t.me/marafonbotbazasi/11", "https://t.me/marafonbotbazasi/12"]
        send_videos(user_id, video_file_ids)
        bot.send_message(user_id, '1-dars va 2-dars videolar sizga jo‘natildi.')
    elif 20 <= balance < 30:
        video_file_ids = ["https://t.me/marafonbotbazasi/11", "https://t.me/marafonbotbazasi/12", "https://t.me/marafonbotbazasi/13"]
        send_videos(user_id, video_file_ids)
        bot.send_message(user_id, '1-dars, 2-dars, va 3-dars videolar sizga jo‘natildi.')
    elif 30 <= balance < 40:
        video_file_ids = ["https://t.me/marafonbotbazasi/11", "https://t.me/marafonbotbazasi/12", "https://t.me/marafonbotbazasi/13", "https://t.me/marafonbotbazasi/14"]
        send_videos(user_id, video_file_ids)
        bot.send_message(user_id, '1-dars, 2-dars, 3-dars va 4-dars videolari sizga jo‘natildi.') 
    elif 40 <= balance < 50:
        video_file_ids = ["https://t.me/marafonbotbazasi/11", "https://t.me/marafonbotbazasi/12", "https://t.me/marafonbotbazasi/13", "https://t.me/marafonbotbazasi/14", "https://t.me/marafonbotbazasi/15"]
        send_videos(user_id, video_file_ids)
        bot.send_message(user_id, '1-dars, 2-dars, 3-dars, 4-dars va 5-dars videolari sizga jo‘natildi.') 
    else:
        bot.send_message(user_id, 'Kechirasiz, ballaringiz yetarli emas.')

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
            data['total'] += 1
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
            data['id'][user] = data['total'] + 1
        save_users_data(data)
        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton(
            text='Marafon kanaliga qo‘shilish', url='https://t.me/medstone_usmle'))
        markup.add(telebot.types.InlineKeyboardButton(
            text='Obunani tekshirish', callback_data='check'))
        msg_start = """Tabriklayman! Siz marafon qatnashchisi bo'lishga yaqin qoldingiz.

Biokimyo bo'yicha 7 kunlik bepul marafon davomida quyidagi mavzularni o'rganamiz:

✅- DNK tuzilishi va klinik ahamiyati
\n✅- DNK metillanishining klinikada muhimligi
\n✅- Purin metabolizmi va uning klinik ahamiyati
\n✅- Podagra kasalligi
\n✅- Podagra kasalligining davosi

Shu mavzulardagi eng so'nggi yangiliklarni o'zlashtirishni xohlasangiz hoziroq marafon bo'lib o'tadigan kanalga qo'shiling."""
        bot.send_message(user, msg_start, reply_markup=markup)
    except Exception as e:
        bot.send_message(message.chat.id, "Bu buyruqda xatolik bor, iltimos admin xatoni tuzatishini kuting")
        bot.send_message(OWNER_ID, f"Botingizda xatolik bor: {str(e)}")

@bot.callback_query_handler(func=lambda call: True)
def query_handler(call):
    try:
        ch = check(call.message.chat.id)
        if call.data == 'check':
            if ch:
                data = load_users_data()
                user_id = call.message.chat.id
                user = str(user_id)
                username = call.message.chat.username
                bot.answer_callback_query(callback_query_id=call.id, text='Siz kanalga qo‘shildingiz, omad tilaymiz')

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
                            f"Do'stingiz kanalga qo'shildi va siz +{Per_Refer} {TOKEN} ishlab oldingiz"
                        )
                    save_users_data(data)

                markup = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
                markup.add(telebot.types.KeyboardButton(text='Raqamni ulashish', request_contact=True))
                bot.send_message(call.message.chat.id, f"Salom, @{username}! \nSizga bonuslarimizni bera olishimiz uchun raqamingizni tasdiqlay olasizmi?\n\nPastdagi maxsus tugmani bossangiz kifoya.", reply_markup=markup)
            else:
                bot.answer_callback_query(callback_query_id=call.id, text='Siz hali kanalga qo‘shilmadingiz')
                markup = telebot.types.InlineKeyboardMarkup()
                markup.add(telebot.types.InlineKeyboardButton(
                    text='Obunani tekshirish', callback_data='check'))
                msg_start = "Ushbu botdan foydalanish uchun quyidagi kanalga qo‘shiling\nva Obunani tekshirish tugmasini bosing\n\n - @medstone_usmle"
                bot.send_message(call.message.chat.id, msg_start, reply_markup=markup)
    except Exception as e:
        bot.send_message(call.message.chat.id, "Bu buyruqda xatolik bor, iltimos admin xatoni tuzatishini kuting")
        bot.send_message(OWNER_ID, f"Botingizda xatolik bor: {str(e)}")

@bot.message_handler(content_types=['contact'])
def contact(message):
    if message.contact is not None:
        contact = message.contact.phone_number
        username = message.from_user.username
        bot.send_message(ADMIN_GROUP_USERNAME, f"Foydalanuvchi: @{username}\nTelefon raqami: {contact}")

        inline_markup = telebot.types.InlineKeyboardMarkup()
        inline_markup.add(telebot.types.InlineKeyboardButton(text="Sovg'angiz👇", callback_data='gift'))
        gift_message = """Siz uchun tayyorlab qo'ygan sovg'alarimizni kutib oling🤗

1️⃣. Kanalimizning yangi mehmonlari uchun Shoxrux Botirov tomonidan maxsus tayyorlangan bonus video darsni raqamingizni tasdiqlash orqali qabul qilib oling
Uni pastdagi "Mening sovgʻam🎁" tugmasini bosish orqali olishingiz mumkin.

2️⃣. Bor yo'g'i 10 ta odam qo'shish orqali avval 650 mingdan sotilgan leksiyalar to'plamiga mansub 1 ta dolzarb mavzu leksiyasini BEPUL olish imkoniyati

3️⃣. 20 ta odam qo'shish orqali avval 650 mingdan sotilgan leksiyalar to'plamiga mansub 2 ta video darsni case tahlillari bilan birga BEPUL olish imkoniyati.

4️⃣. 30 ta odam qo'shish orqali yuqoridagi pullik kanalga tegishli 3 ta darsni batafsil case tahlillari bilan BEPUL qo'lga kiritish imkoniyati.

Shu tariqa har safar 10 ta odam sizning havolangiz orqali kanalga qo'shilsa yangi video leksiyalarni qo'lga kiritib boraverasiz.

Xatto butun boshli kursni ham qo'lga kirita olasiz.🤗

Taklif qilish uchun maxsus linkingizni oling va do'stlaringizni jamoamizga taklif qiling.
Sizning maxsus linkingiz bu faqat sizga tegishli havola bo'lib, u orqali kanalga qo'shilgan har bir doʻstingiz sizga 1️⃣ ball olib keladi.

Maxsus linkingizni olish uchun pastdagi "Maxsus linkim" tugmasini bosing.

Ballaringizni ko'rish uchun pastdagi "Mening hisobim" tugmasini bosing"""
        bot.send_message(message.chat.id, gift_message, reply_markup=inline_markup)
        menu(message.chat.id)

@bot.callback_query_handler(func=lambda call: call.data in ['account', 'ref_link', 'gift'])
def account_or_ref_link_handler(call):
    try:
        user_id = call.message.chat.id
        data = load_users_data()
        user = str(user_id)
        username = call.message.chat.username

        if call.data == 'account':
            balance = data['balance'].get(user, 0)
            markup = telebot.types.InlineKeyboardMarkup()
            markup.add(telebot.types.InlineKeyboardButton(text=f"Balans: {balance} Ball", callback_data='balance'))
            msg = f"Foydalanuvchi: {username}\nBalans: {balance} {TOKEN}"
            bot.send_message(call.message.chat.id, msg, reply_markup=markup)

        elif call.data == 'ref_link':
            send_invite_link(call.message.chat.id)

        elif call.data == 'gift':
            send_gift_video(user_id)

    except Exception as e:
        bot.send_message(call.message.chat.id, "Bu buyruqda xatolik bor, iltimos admin xatoni tuzatishini kuting")
        bot.send_message(OWNER_ID, f"Botingizda xatolik bor: {str(e)}")

def send_invite_link(user_id):
    data = load_users_data()
    bot_name = bot.get_me().username
    user = str(user_id)

    if user not in data['referred']:
        data['referred'][user] = 0
    save_users_data(data)

    ref_link = f'https://telegram.me/{bot_name}?start={user_id}'
    msg = (f"Biokimyo bo'yicha OCHIQ DARSLAR\n\nUSMLE step 1 bo'yicha unikal hisoblangan kurslar asosida tayyorlangan BEPUL marafonda "
           f"qatnashmoqchi bo'lsangiz quyidagi havola orqali jamoamizga qo'shiling!\n\n"
           f"Vaqt va joylar chegaralangan ekanligini unutmang azizlar!\n\n"
           f"Marafon bakalavr, ordinator va shifokorlar uchun mo'ljallangan va butunlay bepul.\n\n"
           f"Taklifnoma havolasi: {ref_link}")
    bot.send_message(user_id, msg)

# Broadcast funksiyasi (ReplyKeyboardMarkup bilan)
@bot.message_handler(commands=['broadcast'])
def handle_broadcast(message):
    try:
        if message.chat.id != OWNER_ID:
            bot.reply_to(message, "Bu buyruq faqat admin uchun mavjud!")
            return
        
        # ReplyKeyboardMarkup yaratish
        markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        markup.add(
            telebot.types.KeyboardButton("Matn"),
            telebot.types.KeyboardButton("Rasm"),
            telebot.types.KeyboardButton("Video")
        )
        bot.reply_to(message, "Broadcast turini tanlang:", reply_markup=markup)
        
        # Keyingi xabarni olish uchun handler qo‘shish
        bot.register_next_step_handler(message, process_broadcast_type)
        
    except Exception as e:
        bot.reply_to(message, f"Xatolik yuz berdi: {str(e)}")
        bot.send_message(OWNER_ID, f"Broadcast xatoligi: {str(e)}")

def process_broadcast_type(message):
    try:
        if message.chat.id != OWNER_ID:
            return
        
        broadcast_type = message.text
        if broadcast_type not in ["Matn", "Rasm", "Video"]:
            bot.reply_to(message, "Iltimos, to‘g‘ri tanlov qiling! Qayta urining:", reply_markup=telebot.types.ReplyKeyboardRemove())
            handle_broadcast(message)  # Qayta menyu ko‘rsatish
            return

        if broadcast_type == "Matn":
            msg = bot.send_message(message.chat.id, "Yuboriladigan matnni kiriting (Markdown qo'llab-quvvatlanadi):\nFiltrlash uchun: '/filter <ball>' (masalan, /filter 10)")
            bot.register_next_step_handler(msg, lambda m: process_broadcast(m, 'text'))
        elif broadcast_type == "Rasm":
            msg = bot.send_message(message.chat.id, "Yuboriladigan rasmni yuklang va izoh qo'shing (ixtiyoriy):")
            bot.register_next_step_handler(msg, lambda m: process_broadcast(m, 'photo'))
        elif broadcast_type == "Video":
            msg = bot.send_message(message.chat.id, "Yuboriladigan videoni yuklang va izoh qo'shing (ixtiyoriy):")
            bot.register_next_step_handler(msg, lambda m: process_broadcast(m, 'video'))
        
    except Exception as e:
        bot.reply_to(message, f"Xatolik yuz berdi: {str(e)}")
        bot.send_message(OWNER_ID, f"Broadcast xatoligi: {str(e)}")

def process_broadcast(message, broadcast_type):
    try:
        if message.chat.id != OWNER_ID:
            return

        data = load_users_data()
        user_ids = list(data['referred'].keys())
        
        # Filtrlash
        min_balance = 0
        if broadcast_type == 'text' and '/filter' in message.text:
            try:
                min_balance = int(message.text.split('/filter')[1].split()[0])
                message.text = message.text.split('/filter')[0].strip()
                user_ids = [uid for uid in user_ids if data['balance'].get(uid, 0) >= min_balance]
            except:
                bot.reply_to(message, "Filtrda xato! /filter <ball> formatidan foydalaning.")
                return

        if not user_ids:
            bot.reply_to(message, "Foydalanuvchilar topilmadi!")
            return

        success_count = 0
        fail_count = 0
        blocked_users = []

        bot.reply_to(message, f"Broadcast boshlandi. Jami {len(user_ids)} foydalanuvchi.")

        for user_id in user_ids:
            try:
                if broadcast_type == 'text':
                    bot.send_message(int(user_id), message.text, parse_mode='Markdown')
                elif broadcast_type == 'photo' and message.photo:
                    caption = message.caption or ""
                    bot.send_photo(int(user_id), message.photo[-1].file_id, caption=caption, parse_mode='Markdown')
                elif broadcast_type == 'video' and message.video:
                    caption = message.caption or ""
                    bot.send_video(int(user_id), message.video.file_id, caption=caption, parse_mode='Markdown')
                success_count += 1
                time.sleep(0.05)  # Telegram API limiti uchun kechikish
            except Exception as e:
                fail_count += 1
                if "Forbidden" in str(e):
                    blocked_users.append(user_id)
                print(f"Xato {user_id} uchun: {str(e)}")

        # Bloklangan foydalanuvchilarni o'chirish
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

        # Yakunlov xabarini admin uchun yuborish va menyu qaytarish
        result_msg = f"Broadcast yakunlandi!\n" \
                    f"Muvafaqiyatli: {success_count}\n" \
                    f"Muvaffaqiyatsiz: {fail_count}\n" \
                    f"Bloklangan foydalanuvchilar: {len(blocked_users)}"
        bot.send_message(OWNER_ID, result_msg)
        
        # Adminni asosiy menyu ga qaytarish
        bot.send_message(OWNER_ID, "Broadcast yakunlandi. Asosiy menyu:", reply_markup=telebot.types.ReplyKeyboardRemove())
        menu(OWNER_ID)  # Asosiy menyu tugmalarini qayta ko‘rsatish

    except Exception as e:
        bot.reply_to(message, f"Xatolik yuz berdi: {str(e)}")
        bot.send_message(OWNER_ID, f"Broadcast xatoligi: {str(e)}")

@bot.message_handler(content_types=['text'])
def send_text(message):
    try:
        if message.text == '🆔 Mening hisobim':
            data = load_users_data()
            user_id = message.chat.id
            user = str(user_id)
            balance = data['balance'].get(user, 0)
            markup = telebot.types.InlineKeyboardMarkup()
            markup.add(telebot.types.InlineKeyboardButton(text=f"Balans: {balance} Ball", callback_data='balance'))
            msg = f"Foydalanuvchi: {message.from_user.username}\nBalans: {balance} {TOKEN}"
            bot.send_message(message.chat.id, msg, reply_markup=markup)
        elif message.text == '🙌🏻 Maxsus linkim':
            send_invite_link(message.chat.id)
        elif message.text == '🎁 Mening sovg\'am':
            send_gift_video(message.chat.id)
        elif message.text == "📊 Statistika":
            if message.chat.id == OWNER_ID:
                user_id = message.chat.id
                data = load_users_data()
                msg = "Jami foydalanuvchilar: {} foydalanuvchilar"
                msg = msg.format(data['total'])
                bot.send_message(user_id, msg)
            else:
                bot.send_message(message.chat.id, "Ushbu buyruq faqat bot egasiga mavjud.")
        elif message.text == "📢 Broadcast":
            if message.chat.id == OWNER_ID:
                bot.send_message(message.chat.id, "Broadcast uchun /broadcast buyrug'ini ishlatishingiz mumkin!")
            else:
                bot.send_message(message.chat.id, "Bu buyruq faqat admin uchun!")
    except Exception as e:
        bot.send_message(message.chat.id, "Bu buyruqda xatolik bor, iltimos admin xatoni tuzatishini kuting")
        bot.send_message(OWNER_ID, f"Botingizda xatolik bor: {str(e)}")

@bot.message_handler(content_types=['video'])
def handle_video(message):
    video_file_id = message.video.file_id
    bot.send_message(message.chat.id, f"Video fayl ID si: {video_file_id}")

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)

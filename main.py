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
    bot.send_message(id, "🏠 **Asosiy menyu** ⬇️", reply_markup=keyboard, parse_mode='MarkdownV2')

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
        bot.send_message(user_id, '🎥 **1\-dars video** sizga muvaffaqiyatli jo\'natildi\! 🚀\n\nKeyingi darslarni olish uchun do\'stlaringizni taklif qiling\!', parse_mode='MarkdownV2')
    elif 10 <= balance < 20:
        video_file_ids = ["https://t.me/marafonbotbazasi/11", "https://t.me/marafonbotbazasi/12"]
        send_videos(user_id, video_file_ids)
        bot.send_message(user_id, '🎥 **1\-dars va 2\-dars videolar** sizga jo\'natildi\! ✨\n\nYana ko\'proq darslarni qo\'lga kiritish uchun do\'stlaringizni taklif qiling\!', parse_mode='MarkdownV2')
    elif 20 <= balance < 30:
        video_file_ids = ["https://t.me/marafonbotbazasi/11", "https://t.me/marafonbotbazasi/12", "https://t.me/marafonbotbazasi/13"]
        send_videos(user_id, video_file_ids)
        bot.send_message(user_id, '🎥 **1\-dars, 2\-dars va 3\-dars videolar** sizga jo\'natildi\! 👏\n\nSizning samaradorligingizga havas qilsa arziydi\!', parse_mode='MarkdownV2')
    elif 30 <= balance < 40:
        video_file_ids = ["https://t.me/marafonbotbazasi/11", "https://t.me/marafonbotbazasi/12", "https://t.me/marafonbotbazasi/13", "https://t.me/marafonbotbazasi/14"]
        send_videos(user_id, video_file_ids)
        bot.send_message(user_id, '🎥 **1\-dars, 2\-dars, 3\-dars va 4\-dars videolar** sizga jo\'natildi\! 🌟\n\nButun kursni qo\'lga kiritishga yaqinlashib qoldingiz\!', parse_mode='MarkdownV2')
    elif 40 <= balance < 50:
        video_file_ids = ["https://t.me/marafonbotbazasi/11", "https://t.me/marafonbotbazasi/12", "https://t.me/marafonbotbazasi/13", "https://t.me/marafonbotbazasi/14", "https://t.me/marafonbotbazasi/15"]
        send_videos(user_id, video_file_ids)
        bot.send_message(user_id, '🎥 **1\-dars, 2\-dars, 3\-dars, 4\-dars va 5\-dars videolar** sizga jo\'natildi\! 🎉\nTabriklaymiz, Siz juda yaxshi natija ko\'rsatyabsiz\!', parse_mode='MarkdownV2')
    else:
        bot.send_message(user_id, '⚠️ **Kechirasiz**, ballaringiz yetarli emas\!\n🚀 Do\'stlaringizni taklif qilib, ko\'proq ball to\'plang\!', parse_mode='MarkdownV2')

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
            text='📢 Marafon kanaliga qo\'shilish', url='https://t.me/medstone_usmle'))
        markup.add(telebot.types.InlineKeyboardButton(
            text='✅ Obunani tekshirish', callback_data='check'))
        msg_start = """🎉 **Tabriklaymiz\!** Siz marafon qatnashchisi bo\'lishga juda yaqin qoldingiz\!

📚 **Biokimyo bo\'yicha 7 kunlik BEPUL marafon** davomida quyidagilarni o\'rganamiz:
\n\n✅ **DNK tuzilishi** va uning klinik ahamiyati
\n✅ **DNK metillanishi**ning klinikada muhimligi
\n✅ **Purin metabolizmi** va uning klinik ahamiyati
\n✅ **Podagra kasalligi** haqida
\n✅ **Podagra davosi**

✨ Shu mavzulardagi eng so\'nggi yangiliklarni o\'zlashtirishni xohlasangiz, hoziroq **marafon kanaliga qo\'shiling**\!"""
        bot.send_message(user, msg_start, reply_markup=markup, parse_mode='MarkdownV2')
    except Exception as e:
        bot.send_message(message.chat.id, "⚠️ **Xatolik yuz berdi\!** Iltimos, admin xatoni tuzatishini kuting\!", parse_mode='MarkdownV2')
        bot.send_message(OWNER_ID, f"⚠️ **Botingizda xatolik:** {str(e)}", parse_mode='MarkdownV2')

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
                            f"🎁 **Do\'stingiz kanalga qo\'shildi\!**\nSiz **\+{Per_Refer} {TOKEN}** ishlab oldingiz\!",
                            parse_mode='MarkdownV2'
                        )
                    save_users_data(data)

                markup = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
                markup.add(telebot.types.KeyboardButton(text='📞 Raqamni ulashish', request_contact=True))
                bot.send_message(call.message.chat.id, f"👋 **Salom, @{username}\!**\nBiz sizga bonuslarni bera olishimiz uchun **telefon raqamingizni tasdiqlay olasizmi**\?\n\n⬇️ Buning uchun pastdagi tugmani bossangiz kifoya\!", reply_markup=markup, parse_mode='MarkdownV2')
            else:
                bot.answer_callback_query(callback_query_id=call.id, text='⚠️ Siz hali kanalga qo‘shilmadingiz!')
                markup = telebot.types.InlineKeyboardMarkup()
                markup.add(telebot.types.InlineKeyboardButton(
                    text='✅ Obunani tekshirish', callback_data='check'))
                msg_start = "🤖 **Botdan foydalanish uchun** quyidagi kanalga qo\'shiling va **Obunani tekshirish** tugmasini bosing:\n\n📢 **@medstone_usmle**"
                bot.send_message(call.message.chat.id, msg_start, reply_markup=markup, parse_mode='MarkdownV2')
    except Exception as e:
        bot.send_message(call.message.chat.id, "⚠️ **Xatolik yuz berdi\!** Iltimos, admin xatoni tuzatishini kuting\!", parse_mode='MarkdownV2')
        bot.send_message(OWNER_ID, f"⚠️ **Botingizda xatolik:** {str(e)}", parse_mode='MarkdownV2')

@bot.message_handler(content_types=['contact'])
def contact(message):
    if message.contact is not None:
        contact = message.contact.phone_number
        username = message.from_user.username
        bot.send_message(ADMIN_GROUP_USERNAME, f"👤 **Foydalanuvchi:** @{username}\n📞 **Telefon raqami:** {contact}", parse_mode='MarkdownV2')

        inline_markup = telebot.types.InlineKeyboardMarkup()
        inline_markup.add(telebot.types.InlineKeyboardButton(text="🎁 Sovg\'angizni oling!", callback_data='gift'))
        gift_message = """🎉 **Siz uchun maxsus tayyorlangan sovg\'alarni kutib oling\!**

1️⃣ **Kanalimizning barcha qatnashchilari ** Shoxrux Botirov tomonidan maxsus tayyorlangan **bonus video dars**ni mehmondo\'stligimiz ramzi sifatida yuklab olishlari mumkin\nBuning uchun pastdagi **"Mening sovg\'am🎁"** tugmasini bosing\.

2️⃣ **10 ta do\'stingizni taklif qiling** – avval 650 ming so\'mdan sotilgan leksiyalar to\'plamidan **1 ta dolzarb mavzu**ni BEPUL qo\'lga kiriting\!

3️⃣ **20 ta do\'stingizni taklif qiling** – **2 ta video dars**ni case tahlillari bilan birga BEPUL qo\'lga kiriting\!

4️⃣ **30 ta do\'stingizni taklif qiling** – **3 ta dars**ni batafsil case tahlillari bilan BEPUL oling\!

🔥 Har safar **10 ta do\'stingiz** sizning havolangiz orqali kanalga qo\'shilsa, yangi video leksiyalarni qo\'lga kiritib boraverasiz – shu tarzda hatto **butun kursni** ham BEPUL yutib olishingiz mumkin\!

📎 **Maxsus linkingizni oling** va do\'stlaringizni jamoamizga taklif qiling\! Bu faqat sizga tegishli havola bo\'lib, u orqali kanalga qo\'shilgan har bir do\'stingiz sizga **1 ball** olib keladi\.

⬇️ **"Maxsus linkim"** tugmasini bosing va linkingizni oling\!
📊 Ballaringizni esa **"Mening hisobim"** tugmasi orqali kuzatib borishingiz mumkin\!"""
        bot.send_message(message.chat.id, gift_message, reply_markup=inline_markup, parse_mode='MarkdownV2')
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
            markup.add(telebot.types.InlineKeyboardButton(text=f"💰 Balans: {balance} Ball", callback_data='balance'))
            msg = f"👤 **Foydalanuvchi:** @{username}\n💰 **Balans:** {balance} {TOKEN}"
            bot.send_message(call.message.chat.id, msg, reply_markup=markup, parse_mode='MarkdownV2')
        elif call.data == 'ref_link':
            send_invite_link(call.message.chat.id)
        elif call.data == 'gift':
            send_gift_video(user_id)

    except Exception as e:
        bot.send_message(call.message.chat.id, "⚠️ **Xatolik yuz berdi\!** Iltimos, admin xatoni tuzatishini kuting\!", parse_mode='MarkdownV2')
        bot.send_message(OWNER_ID, f"⚠️ **Botingizda xatolik:** {str(e)}", parse_mode='MarkdownV2')

def send_invite_link(user_id):
    data = load_users_data()
    bot_name = bot.get_me().username
    user = str(user_id)

    if user not in data['referred']:
        data['referred'][user] = 0
    save_users_data(data)

    ref_link = f'https://telegram.me/{bot_name}?start={user_id}'
    msg = (f"📚 **Biokimyo bo\'yicha OCHIQ DARSLAR**\n\n"
           f"✨ **USMLE Step 1** asosidagi unikal kurslar asosida tayyorlangan **BEPUL marafon**da qatnashmoqchi bo\'lsangiz, quyidagi havola orqali jamoamizga qo\'shiling\!\n\n"
           f"⏳ **Vaqt va joylar chegaralangan** – shoshiling\!\n\n"
           f"👩‍⚕️ Marafon **bakalavrlar, ordinatorlar va shifokorlar** uchun mo\'ljallangan va **butunlay bepul**\!\n\n"
           f"🔗 **Taklifnoma havolangiz:** {ref_link}")
    bot.send_message(user_id, msg, parse_mode='MarkdownV2')

@bot.message_handler(commands=['broadcast'])
def handle_broadcast(message):
    try:
        if message.chat.id != OWNER_ID:
            bot.reply_to(message, "🚫 **Bu buyruq faqat admin uchun\!**", parse_mode='MarkdownV2')
            return
        
        markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        markup.add(
            telebot.types.KeyboardButton("✍️ Matn"),
            telebot.types.KeyboardButton("📸 Rasm"),
            telebot.types.KeyboardButton("🎥 Video")
        )
        bot.reply_to(message, "📢 **Broadcast turini tanlang:**", reply_markup=markup, parse_mode='MarkdownV2')
        
        bot.register_next_step_handler(message, process_broadcast_type)
        
    except Exception as e:
        bot.reply_to(message, f"⚠️ **Xatolik yuz berdi:** {str(e)}", parse_mode='MarkdownV2')
        bot.send_message(OWNER_ID, f"⚠️ **Broadcast xatoligi:** {str(e)}", parse_mode='MarkdownV2')

def process_broadcast_type(message):
    try:
        if message.chat.id != OWNER_ID:
            return
        
        broadcast_type = message.text
        if broadcast_type not in ["✍️ Matn", "📸 Rasm", "🎥 Video"]:
            bot.reply_to(message, "⚠️ **Iltimos, to\'g\'ri tanlov qiling\!** Qayta urining:", reply_markup=telebot.types.ReplyKeyboardRemove(), parse_mode='MarkdownV2')
            handle_broadcast(message)
            return

        if broadcast_type == "✍️ Matn":
            msg = bot.send_message(message.chat.id, "📝 Yuboriladigan **matnni** kiriting \(Markdown qo\'llab\-quvvatlanadi\):\nFiltrlash uchun: **/filter <ball>** \(masalan, /filter 10\)", parse_mode='MarkdownV2')
            bot.register_next_step_handler(msg, lambda m: process_broadcast(m, 'text'))
        elif broadcast_type == "📸 Rasm":
            msg = bot.send_message(message.chat.id, "📸 Yuboriladigan **rasmni** yuklang va izoh qo\'shing \(ixtiyoriy\):", parse_mode='MarkdownV2')
            bot.register_next_step_handler(msg, lambda m: process_broadcast(m, 'photo'))
        elif broadcast_type == "🎥 Video":
            msg = bot.send_message(message.chat.id, "🎥 Yuboriladigan **videoni** yuklang va izoh qo\'shing \(ixtiyoriy\):", parse_mode='MarkdownV2')
            bot.register_next_step_handler(msg, lambda m: process_broadcast(m, 'video'))
        
    except Exception as e:
        bot.reply_to(message, f"⚠️ **Xatolik yuz berdi:** {str(e)}", parse_mode='MarkdownV2')
        bot.send_message(OWNER_ID, f"⚠️ **Broadcast xatoligi:** {str(e)}", parse_mode='MarkdownV2')

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
                bot.reply_to(message, "⚠️ **Filtrda xato\!** /filter <ball> formatidan foydalaning\.", parse_mode='MarkdownV2')
                return

        if not user_ids:
            bot.reply_to(message, "🚫 **Foydalanuvchilar topilmadi\!**", parse_mode='MarkdownV2')
            return

        success_count = 0
        fail_count = 0
        blocked_users = []

        bot.reply_to(message, f"📢 **Broadcast boshlandi\.**\nJami **{len(user_ids)} foydalanuvchi**ga xabar yuboriladi\.", parse_mode='MarkdownV2')

        for user_id in user_ids:
            try:
                if broadcast_type == 'text':
                    bot.send_message(int(user_id), message.text, parse_mode='MarkdownV2')
                elif broadcast_type == 'photo' and message.photo:
                    caption = message.caption or ""
                    bot.send_photo(int(user_id), message.photo[-1].file_id, caption=caption, parse_mode='MarkdownV2')
                elif broadcast_type == 'video' and message.video:
                    caption = message.caption or ""
                    bot.send_video(int(user_id), message.video.file_id, caption=caption, parse_mode='MarkdownV2')
                success_count += 1
                time.sleep(0.05)
            except Exception as e:
                fail_count += 1
                if "Forbidden" in str(e):
                    blocked_users.append(user_id)
                print(f"Xato {user_id} uchun: {str(e)}")

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

        result_msg = f"🎉 **Broadcast yakunlandi\!**\n" \
                     f"✅ **Muvafaqiyatli:** {success_count} ta\n" \
                     f"❌ **Muvaffaqiyatsiz:** {fail_count} ta\n" \
                     f"🚫 **Bloklangan foydalanuvchilar:** {len(blocked_users)} ta"
        bot.send_message(OWNER_ID, result_msg, parse_mode='MarkdownV2')
        
        bot.send_message(OWNER_ID, "🏠 **Broadcast yakunlandi\!**\nAsosiy menyuga qaytish:", reply_markup=telebot.types.ReplyKeyboardRemove(), parse_mode='MarkdownV2')
        menu(OWNER_ID)

    except Exception as e:
        bot.reply_to(message, f"⚠️ **Xatolik yuz berdi:** {str(e)}", parse_mode='MarkdownV2')
        bot.send_message(OWNER_ID, f"⚠️ **Broadcast xatoligi:** {str(e)}", parse_mode='MarkdownV2')

@bot.message_handler(content_types=['text'])
def send_text(message):
    try:
        if message.text == '🆔 Mening hisobim':
            data = load_users_data()
            user_id = message.chat.id
            user = str(user_id)
            balance = data['balance'].get(user, 0)
            markup = telebot.types.InlineKeyboardMarkup()
            markup.add(telebot.types.InlineKeyboardButton(text=f"💰 Balans: {balance} Ball", callback_data='balance'))
            msg = f"👤 **Foydalanuvchi:** @{message.from_user.username}\n💰 **Balans:** {balance} {TOKEN}"
            bot.send_message(message.chat.id, msg, reply_markup=markup, parse_mode='MarkdownV2')
        elif message.text == '🙌🏻 Maxsus linkim':
            send_invite_link(message.chat.id)
        elif message.text == '🎁 Mening sovg\'am':
            send_gift_video(message.chat.id)
        elif message.text == "📊 Statistika":
            if message.chat.id == OWNER_ID:
                user_id = message.chat.id
                data = load_users_data()
                msg = f"📈 **Jami foydalanuvchilar:** {data['total']} ta"
                bot.send_message(user_id, msg, parse_mode='MarkdownV2')
            else:
                bot.send_message(message.chat.id, "🚫 **Ushbu buyruq faqat bot egasiga mavjud\!**", parse_mode='MarkdownV2')
        elif message.text == "📢 Broadcast":
            if message.chat.id == OWNER_ID:
                bot.send_message(message.chat.id, "📢 **Broadcast uchun** /broadcast buyrug\'ini ishlatishingiz mumkin\!", parse_mode='MarkdownV2')
            else:
                bot.send_message(message.chat.id, "🚫 **Bu buyruq faqat admin uchun\!**", parse_mode='MarkdownV2')
    except Exception as e:
        bot.send_message(message.chat.id, "⚠️ **Xatolik yuz berdi\!** Iltimos, admin xatoni tuzatishini kuting\!", parse_mode='MarkdownV2')
        bot.send_message(OWNER_ID, f"⚠️ **Botingizda xatolik:** {str(e)}", parse_mode='MarkdownV2')

@bot.message_handler(content_types=['video'])
def handle_video(message):
    video_file_id = message.video.file_id
    bot.send_message(message.chat.id, f"🎥 **Video fayl ID si:** {video_file_id}", parse_mode='MarkdownV2')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)

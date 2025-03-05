# ... (kodning boshqa qismlari o'zgarmagan holda qoldiriladi) ...

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
            text='📢 Marafon kanaliga qo‘shilish', url='https://t.me/medstone_usmle'))
        markup.add(telebot.types.InlineKeyboardButton(
            text='✅ Obunani tekshirish', callback_data='check'))
        msg_start = """🎉 **Tabriklaymiz!** Siz marafon qatnashchisi bo‘lishga bir qadam yaqin qoldingiz!  

📚 **Biokimyo bo‘yicha 7 kunlik BEPUL marafon** davomida quyidagi mavzularni o‘rganamiz:  
✅ **DNK tuzilishi** va uning klinik ahamiyati  
✅ **DNK metillanishi**ning klinikada muhimligi  
✅ **Purin metabolizmi** va uning klinik ahamiyati  
✅ **Podagra kasalligi** haqida  
✅ **Podagra davosi**  

✨ Shu mavzulardagi eng so‘nggi yangiliklarni o‘zlashtirishni xohlasangiz, hoziroq marafon bo‘lib o‘tadigan kanalga qo‘shiling!"""
        bot.send_message(user, msg_start, reply_markup=markup, parse_mode='Markdown')
    except Exception as e:
        bot.send_message(message.chat.id, "⚠️ Bu buyruqda xatolik yuz berdi, iltimos, admin xatoni tuzatishini kuting!")
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
                            f"🎁 Do‘stingiz kanalga qo‘shildi va siz **+{Per_Refer} {TOKEN}** ishlab oldingiz!"
                        )
                    save_users_data(data)

                markup = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
                markup.add(telebot.types.KeyboardButton(text='📞 Raqamni ulashish', request_contact=True))
                bot.send_message(call.message.chat.id, f"👋 **Salom, @{username}!** \nSizga bonuslarimizni bera olishimiz uchun telefon raqamingizni tasdiqlaysizmi? \n\n⬇️ Pastdagi tugmani bosing – shu yetarli!", reply_markup=markup, parse_mode='Markdown')
            else:
                bot.answer_callback_query(callback_query_id=call.id, text='⚠️ Siz hali kanalga qo‘shilmadingiz!')
                markup = telebot.types.InlineKeyboardMarkup()
                markup.add(telebot.types.InlineKeyboardButton(
                    text='✅ Obunani tekshirish', callback_data='check'))
                msg_start = "🤖 Ushbu botdan foydalanish uchun quyidagi kanalga qo‘shiling va **Obunani tekshirish** tugmasini bosing: \n\n📢 **@medstone_usmle**"
                bot.send_message(call.message.chat.id, msg_start, reply_markup=markup, parse_mode='Markdown')
    except Exception as e:
        bot.send_message(call.message.chat.id, "⚠️ Bu buyruqda xatolik yuz berdi, iltimos, admin xatoni tuzatishini kuting!")
        bot.send_message(OWNER_ID, f"⚠️ Botingizda xatolik: {str(e)}")

@bot.message_handler(content_types=['contact'])
def contact(message):
    if message.contact is not None:
        contact = message.contact.phone_number
        username = message.from_user.username
        bot.send_message(ADMIN_GROUP_USERNAME, f"👤 **Foydalanuvchi:** @{username}\n📞 **Telefon raqami:** {contact}", parse_mode='Markdown')

        inline_markup = telebot.types.InlineKeyboardMarkup()
        inline_markup.add(telebot.types.InlineKeyboardButton(text="🎁 Sovg‘angizni oling!", callback_data='gift'))
        gift_message = """🎉 **Siz uchun maxsus sovg‘alar tayyor!**  

1️⃣ **Yangi qatnashchilar uchun:** Shoxrux Botirov tomonidan tayyorlangan **bonus video dars**ni raqamingizni tasdiqlash orqali oling! Pastdagi **"Mening sovg‘am🎁"** tugmasini bosing.  

2️⃣ **10 ta do‘st taklif qiling** – avval 650 ming so‘mdan sotilgan leksiyalar to‘plamidan **1 ta dolzarb mavzu**ni BEPUL oling!  

3️⃣ **20 ta do‘st taklif qiling** – **2 ta video dars**ni case tahlillari bilan birga BEPUL qo‘lga kiriting!  

4️⃣ **30 ta do‘st taklif qiling** – **3 ta dars**ni batafsil case tahlillari bilan BEPUL oling!  

🔥 Har safar 10 ta do‘st sizning havolangiz orqali qo‘shilsa, yangi video leksiyalarni qo‘lga kiriting – hatto **butun kursni** ham BEPUL olishingiz mumkin!  

📎 **Maxsus linkingizni oling** va do‘stlaringizni jamoamizga taklif qiling! Bu faqat sizga tegishli havola bo‘lib, har bir do‘stingiz sizga **1 ball** olib keladi.  

⬇️ **"Maxsus linkim"** tugmasini bosing va linkingizni oling!  
📊 Ballaringizni **"Mening hisobim"** tugmasi orqali ko‘ring!"""
        bot.send_message(message.chat.id, gift_message, reply_markup=inline_markup, parse_mode='Markdown')
        menu(message.chat.id)

def send_gift_video(user_id):
    data = load_users_data()
    balance = data['balance'].get(str(user_id), 0)
    if 0 <= balance < 10:
        video_file_ids = ["https://t.me/marafonbotbazasi/10", "https://t.me/marafonbotbazasi/11"]
        send_videos(user_id, video_file_ids)
        bot.send_message(user_id, '🎥 **1-dars video** sizga muvaffaqiyatli jo‘natildi! 🚀', parse_mode='Markdown')
    elif 10 <= balance < 20:
        video_file_ids = ["https://t.me/marafonbotbazasi/11", "https://t.me/marafonbotbazasi/12"]
        send_videos(user_id, video_file_ids)
        bot.send_message(user_id, '🎥 **1-dars va 2-dars videolar** sizga jo‘natildi! Yana do‘stlaringizni taklif qiling! ✨', parse_mode='Markdown')
    elif 20 <= balance < 30:
        video_file_ids = ["https://t.me/marafonbotbazasi/11", "https://t.me/marafonbotbazasi/12", "https://t.me/marafonbotbazasi/13"]
        send_videos(user_id, video_file_ids)
        bot.send_message(user_id, '🎥 **1-dars, 2-dars va 3-dars videolar** sizga jo‘natildi! Ajoyib ish! 👏', parse_mode='Markdown')
    elif 30 <= balance < 40:
        video_file_ids = ["https://t.me/marafonbotbazasi/11", "https://t.me/marafonbotbazasi/12", "https://t.me/marafonbotbazasi/13", "https://t.me/marafonbotbazasi/14"]
        send_videos(user_id, video_file_ids)
        bot.send_message(user_id, '🎥 **1-dars, 2-dars, 3-dars va 4-dars videolar** sizga jo‘natildi! Siz zo‘rsiz! 🌟', parse_mode='Markdown')
    elif 40 <= balance < 50:
        video_file_ids = ["https://t.me/marafonbotbazasi/11", "https://t.me/marafonbotbazasi/12", "https://t.me/marafonbotbazasi/13", "https://t.me/marafonbotbazasi/14", "https://t.me/marafonbotbazasi/15"]
        send_videos(user_id, video_file_ids)
        bot.send_message(user_id, '🎥 **1-dars, 2-dars, 3-dars, 4-dars va 5-dars videolar** sizga jo‘natildi! Butun kursga yaqinsiz! 🎉', parse_mode='Markdown')
    else:
        bot.send_message(user_id, '⚠️ Kechirasiz, ballaringiz yetarli emas. Do‘stlaringizni taklif qilib, ball to‘plang! 🚀', parse_mode='Markdown')

def send_invite_link(user_id):
    data = load_users_data()
    bot_name = bot.get_me().username
    user = str(user_id)

    if user not in data['referred']:
        data['referred'][user] = 0
    save_users_data(data)

    ref_link = f'https://telegram.me/{bot_name}?start={user_id}'
    msg = (f"📚 **Biokimyo bo‘yicha OCHIQ DARSLAR**  
✨ **USMLE Step 1** asosidagi unikal kurslardan tayyorlangan **BEPUL marafon**da qatnashmoqchi bo‘lsangiz, quyidagi havola orqali jamoamizga qo‘shiling!  

⏳ **Vaqt va joylar chegaralangan** – shoshiling!  
👩‍⚕️ Marafon bakalavrlar, ordinatorlar va shifokorlar uchun mo‘ljallangan va **butunlay bepul**!  

🔗 **Taklifnoma havolangiz:** {ref_link}")
    bot.send_message(user_id, msg, parse_mode='Markdown')

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
            bot.send_message(message.chat.id, msg, reply_markup=markup, parse_mode='Markdown')
        elif message.text == '🙌🏻 Maxsus linkim':
            send_invite_link(message.chat.id)
        elif message.text == '🎁 Mening sovg\'am':
            send_gift_video(message.chat.id)
        elif message.text == "📊 Statistika":
            if message.chat.id == OWNER_ID:
                user_id = message.chat.id
                data = load_users_data()
                msg = f"📈 **Jami foydalanuvchilar:** {data['total']} ta"
                bot.send_message(user_id, msg, parse_mode='Markdown')
            else:
                bot.send_message(message.chat.id, "🚫 Ushbu buyruq faqat bot egasiga mavjud!")
        elif message.text == "📢 Broadcast":
            if message.chat.id == OWNER_ID:
                bot.send_message(message.chat.id, "📢 Broadcast uchun **/broadcast** buyrug‘ini ishlatishingiz mumkin!")
            else:
                bot.send_message(message.chat.id, "🚫 Bu buyruq faqat admin uchun!")
    except Exception as e:
        bot.send_message(message.chat.id, "⚠️ Bu buyruqda xatolik yuz berdi, iltimos, admin xatoni tuzatishini kuting!")
        bot.send_message(OWNER_ID, f"⚠️ Botingizda xatolik: {str(e)}")

# ... (kodning qolgan qismlari o'zgarmagan holda qoldiriladi) ...

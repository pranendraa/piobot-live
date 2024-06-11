import json
import os
import httpx
import threading
import time
import pytz
import locale
from telegram import Update, Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackContext
from datetime import datetime
from io import StringIO
from logging import getLogger, basicConfig, INFO, WARNING
from dotenv import load_dotenv

from api.showroom import get_streaming_url, check_profile_live_status, get_history_live, get_id_history
from api.idn import get_livestreams, get_infodata, get_id_history_idn, get_history_live_idn
from api.tiktok import get_tt_room_id, is_user_tt_live, get_tt_stream_url

# set locale
locale.setlocale(locale.LC_ALL, 'id_ID.UTF-8')

# Konfigurasi logger
basicConfig(
    filename="log.txt",
    format="{asctime} - [{levelname[0]}] {name} [{module}:{lineno}] - {message}",
    datefmt="%Y-%m-%d %H:%M:%S",
    style="{",
    level=INFO
)

LOGGER = getLogger(__name__)
getLogger("httpx").setLevel(WARNING)

# Mendapatkan isi dari file .env di GitHub Gist
CONFIG_FILE_URL = os.getenv("CONFIG_FILE_URL", "")
response = httpx.get(CONFIG_FILE_URL)
env_content = response.text

# Membuat buffer string dan menulis isi .env ke dalamnya
env_buffer = StringIO(env_content)

# Memuat variabel dari buffer menggunakan load_dotenv
load_dotenv(stream=env_buffer)

# Mengambil nilai variabel dari file .env
TOKEN = os.getenv("TOKEN")
HEROKU_API_KEY = os.getenv("HEROKU_API_KEY")
HEROKU_APP_NAME = os.getenv("HEROKU_APP_NAME")
HEROKU_APP_URL = os.getenv("HEROKU_APP_URL")
PORT = int(os.getenv("PORT", 88))
CHANNEL_ID = os.getenv("CHANNEL_ID")
CHAT_ID = int(os.getenv("CHAT_ID", 0))

ROOM_IDS = json.loads(os.getenv("ROOM_IDS"))
IDN_USERS = json.loads(os.getenv("IDN_USERS"))
TT_USERS = json.loads(os.getenv("TT_USERS"))
TT_USERS_OTHERS = json.loads(os.getenv("TT_USERS_OTHERS"))

# Inisialisasi last_live_status dan last_live_status_idn
last_live_status = {room_id: False for room_id in ROOM_IDS}
last_live_status_idn = {channel_username: False for channel_username in IDN_USERS}
last_live_status_tiktok = {tiktok_username: False for tiktok_username in TT_USERS + TT_USERS_OTHERS}
# Inisialisasi dictionary untuk menyimpan slug
live_streams_slug_idn = {}
# Menyimpan view live terakhir untuk setiap pengguna TikTok
last_user_count_tiktok = {}
# menyimpan waktu mulai showroom
last_live_showroom_started_at = {}
# Simpan ID pesan yang dikirimkan saat live sedang berlangsung SR
sent_message_ids_sr = {}
# Simpan ID pesan yang dikirimkan saat live sedang berlangsung IDN
sent_message_ids_idn = {}
# Simpan ID pesan yang dikirimkan saat live sedang berlangsung TT
sent_message_ids_tt = {}
# Simpan waktu_mulai SR
last_waktu_mulai_sr = {}
# Simpan view_num SR
last_view_num_sr = {}

# Timezone
jakarta_timezone = pytz.timezone('Asia/Jakarta')
jakarta_timezone_now = datetime.now(jakarta_timezone).strftime("%A, %d %b %Y | %H:%M:%S WIB")
hari_jakarta = datetime.now(jakarta_timezone).strftime("%A")
tanggal_jakarta = datetime.now(jakarta_timezone).strftime("%d %B %Y")
waktu_jakarta = datetime.now(jakarta_timezone).strftime("%H:%M:%S WIB")

def start(update: Update, context: CallbackContext) -> None:
    # Memeriksa ID pengguna yang mengirim permintaan
    chat_id = update.effective_chat.id
    if chat_id == CHAT_ID:
        update.message.reply_text('Bot telah dimulai!')
    else:
        # Membuat tombol yang mengarah ke Anda sebagai pemilik
        reply_markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("Owner Telegram", url="https://t.me/pranendra")]
        ])
        update.message.reply_text('Maaf, Anda tidak memiliki izin untuk mengakses bot ini.\n'
                                  'Silahkan angkat kaki anda dari sini!',
                                  reply_markup=reply_markup)

def pesan_showroom(room_id):
    cek_live_sr = check_profile_live_status(room_id)
    if cek_live_sr is not None:
        room_url_key, is_onlive, image, current_live_started_at, share_url_live, view_num, is_premium = cek_live_sr
        
        # slicing room_url_key to get member name
        if room_url_key == "officialJKT48":
            name_member = "JKT48 Official SHOWROOM"
        else:
            name_member = room_url_key.split('_')[1] + " " + room_url_key.split('_')[0]
        
        if '?' in share_url_live:
            base_url = share_url_live.split('?')
            link_url_showroom = base_url[0]

        if is_onlive and not last_live_status[room_id]:
            streaming_url = get_streaming_url(room_id)
            
            waktu_mulai = datetime.fromtimestamp(current_live_started_at, tz=pytz.utc).astimezone(jakarta_timezone).strftime("%A, %d %b %Y | %H:%M:%S WIB")

            if is_premium:
                reply_markup = InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton("Showroom", url=f"{link_url_showroom}")
                    ]
                ])

                message = (
                    f"<b>{name_member}</b> sedang live <b>premium</b>!\n\n"
                    f"🗓️ {waktu_mulai}\n"
                )
            else:
                streaming_link = f"<pre>{streaming_url}</pre>"

                reply_markup = InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton("Showroom", url=f"{link_url_showroom}"),
                        InlineKeyboardButton("Fullscreen", url=f"https://player3.piobot.us.to/player/#{streaming_url}")
                    ]
                ])

                message = (
                    f"<b>{name_member}</b> sedang live{'!' if room_url_key=='officialJKT48' else ' <b>Showroom</b>.'}\n\n"
                    f"🗓️ {waktu_mulai}\n"
                    f"⚡ Streaming URL: {streaming_link}"
                )

            pesan = send_photo_and_text_to_channel(image, message, reply_markup)
            sent_message_ids_sr[room_id] = pesan.message_id

            last_waktu_mulai_sr[room_id] = waktu_mulai
            last_view_num_sr[room_id] = view_num
            last_live_showroom_started_at[room_id] = current_live_started_at
        elif not is_onlive and last_live_status[room_id]:
            current_live_started_at = last_live_showroom_started_at.get(room_id)
            if current_live_started_at:
                data_id = get_id_history(room_id, current_live_started_at)
                if data_id is not None:
                    result = get_history_live(data_id)
                    if result is not None:
                        waktu_mulai_history, waktu_selesai_history, durasi, viewers, active_viewers, total_gifts, comments, users_comments, rupiah_gold = result

                        waktu_mulai_history_without_z = waktu_mulai_history.replace("Z", "")
                        waktu_selesai_history_without_z = waktu_selesai_history.replace("Z", "")

                        waktu_mulai_jakarta = datetime.fromisoformat(waktu_mulai_history_without_z).astimezone(jakarta_timezone).strftime("%A, %d %b %Y | %H:%M:%S WIB")
                        waktu_selesai_jakarta = datetime.fromisoformat(waktu_selesai_history_without_z).astimezone(jakarta_timezone).strftime("%A, %d %b %Y | %H:%M:%S WIB")

                        formatted_rupiah_gold = locale.currency(rupiah_gold, grouping=True, symbol=True)
                        formatted_rupiah_gold = formatted_rupiah_gold.replace('Rp', 'Rp. ')

                        message = (
                            f"<b>{name_member}</b> telah selesai live{'!' if room_url_key=='officialJKT48' else ' <b>Showroom</b>.'}\n\n"
                            f"🕙 Durasi live: <b>{durasi}</b>\n"
                            f"⚡ Mulai: <b>{waktu_mulai_jakarta}</b>\n"
                            f"⚡ Selesai: <b>{waktu_selesai_jakarta}</b>\n"
                            f"👥 <b>{viewers}</b> dari <b>{active_viewers}</b> Penonton aktif\n"
                            f"💬 <b>{comments}</b> dari <b>{users_comments}</b> Pengguna\n"
                            f"🎁 <b>{total_gifts}G (± {formatted_rupiah_gold})</b>"
                        )

                        pesan_id = sent_message_ids_sr.get(room_id)
                        if pesan_id:
                            edit_photo_and_text_in_channel(message, pesan_id)

                else:
                    waktu_mulai_sr = last_waktu_mulai_sr.get(room_id)
                    waktu_selesai_sr = jakarta_timezone_now

                    # Ambil waktu mulai
                    start_time = datetime.strptime(waktu_mulai_sr, "%A, %d %b %Y | %H:%M:%S WIB")
                    end_time = datetime.strptime(waktu_selesai_sr, "%A, %d %b %Y | %H:%M:%S WIB")

                    # Hitung durasi
                    duration = end_time - start_time

                    # Konversi durasi ke dalam detik
                    total_seconds = duration.total_seconds()

                    # Hitung jam, menit, dan detik
                    hours = int(total_seconds // 3600)
                    minutes = int((total_seconds % 3600) // 60)
                    seconds = int(total_seconds % 60)

                    # Format durasi
                    formatted_duration = "{:02}:{:02}:{:02}".format(hours, minutes, seconds)

                    message = (
                            f"<b>{name_member}</b> telah selesai live{'!' if room_url_key=='officialJKT48' else ' <b>Showroom</b>.'}\n\n"
                            f"🕙 Durasi live: <b>{formatted_duration}</b>\n"
                            f"⚡ Mulai: <b>{waktu_mulai_sr}</b>\n"
                            f"⚡ Selesai: <b>{waktu_selesai_sr}</b>\n"
                            f"👥 <b>{last_view_num_sr[room_id]}</b>"
                        )

                    pesan_id = sent_message_ids_sr.get(room_id)
                    if pesan_id:
                        edit_photo_and_text_in_channel(message, pesan_id)

                    del last_waktu_mulai_sr[room_id]
                    del last_view_num_sr[room_id]
        last_live_status[room_id] = is_onlive

def pesan_idn(channel_username):
    slug = get_livestreams(channel_username)
    if slug:
        data_info = get_infodata(slug)
        if data_info:
            title, name, view_count, durasi_live, live_at_jakarta, end_at_jakarta, playback_url, is_status_online, image_url = data_info

            if is_status_online and not last_live_status_idn.get(channel_username, False):
                title_quote = f"<blockquote>{title}</blockquote>"
                streaming_link = f"<pre>{playback_url}</pre>"

                reply_markup = InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton("IDN APP", url=f"https://app.idn.media/?link=https://links.idn.media?type%3Dlive%26url%26slug%3D{slug}"),
                        InlineKeyboardButton("IDN WEB", url=f"https://www.idn.app/{channel_username}/live/{slug}")
                    ],
                    [InlineKeyboardButton("Fullscreen", url=f"https://player3.piobot.us.to/player/#{playback_url}")]
                ])
                
                message = (
                    f"<b>{name}</b> sedang live <b>IDN</b>.\n\n"
                    f"{title_quote}\n"
                    f"🗓️ {live_at_jakarta}\n"
                    f"⚡ Streaming URL: {streaming_link}"
                )
                
                pesan = send_photo_and_text_to_channel(image_url, message, reply_markup)
                sent_message_ids_idn[channel_username] = pesan.message_id

                last_live_status_idn[channel_username] = True
        live_streams_slug_idn[channel_username] = slug
    else:
        # Jika tidak ada slug, lanjutkan dengan slug sebelumnya
        slug = live_streams_slug_idn.get(channel_username)
        if slug:
            data_info = get_infodata(slug)
            if data_info:
                title, name, view_count, durasi_live, live_at_jakarta, end_at_jakarta, playback_url, is_status_online, image_url = data_info
                if not is_status_online and last_live_status_idn.get(channel_username, False):
                    last_live_status_idn[channel_username] = False

                    data_id = get_id_history_idn(slug)
                    if data_id:
                        result = get_history_live_idn(data_id)
                        if result is not None:
                            waktu_mulai_jakarta, waktu_selesai_jakarta, durasi, viewers, active_viewers, total_gifts, comments, users_comments, rupiah_gold = result
                            title_quote = f"<blockquote>{title}</blockquote>"

                            formatted_rupiah_gold = locale.currency(rupiah_gold, grouping=True, symbol=True)
                            formatted_rupiah_gold = formatted_rupiah_gold.replace('Rp', 'Rp. ')

                            message = (
                                f"<b>{name}</b> telah selesai live <b>IDN</b>.\n\n"
                                f"{title_quote}\n"
                                f"🕙 Durasi live: <b>{durasi}</b>\n"
                                f"⚡ Mulai: <b>{waktu_mulai_jakarta}</b>\n"
                                f"⚡ Selesai: <b>{waktu_selesai_jakarta}</b>\n"
                                f"👥 <b>{view_count}</b> dari <b>{active_viewers}</b> Penonton aktif\n"
                                f"💬 <b>{comments}</b> dari <b>{users_comments}</b> Pengguna\n"
                                f"🎁 <b>{total_gifts}G (± {formatted_rupiah_gold})</b>"
                            )

                            pesan_id = sent_message_ids_idn.get(channel_username)
                            if pesan_id:
                                edit_photo_and_text_in_channel(message, pesan_id)
                    else:
                        title_quote = f"<blockquote>{title}</blockquote>"

                        message = (
                            f"<b>{name}</b> telah selesai live <b>IDN</b>.\n\n"
                            f"{title_quote}\n"
                            f"🕙 Durasi live: <b>{durasi_live}</b>\n"
                            f"⚡ Mulai: <b>{live_at_jakarta}</b>\n"
                            f"⚡ Selesai: <b>{end_at_jakarta}</b>\n"
                            f"👥 <b>{view_count}</b>"
                        )

                        pesan_id = sent_message_ids_idn.get(channel_username)
                        if pesan_id:
                            edit_photo_and_text_in_channel(message, pesan_id)

            del live_streams_slug_idn[channel_username]

def pesan_tiktok(tiktok_username):
    room_id = get_tt_room_id(tiktok_username)
    if room_id:
        is_tt_live = is_user_tt_live(room_id)
        if is_tt_live:
            is_online, cover_url, title, nickname, userCount, liveUrl = is_tt_live
            data_tt_stream_url = get_tt_stream_url(room_id)
            if data_tt_stream_url:
                stream_url, create_time, finish_time = data_tt_stream_url
                
                if is_online and not last_live_status_tiktok[tiktok_username]:
                    title_quote = f"<blockquote>{title}</blockquote>"

                    if stream_url:
                        reply_markup = InlineKeyboardMarkup([
                            [
                                InlineKeyboardButton("Tiktok", url=f"https://www.tiktok.com/@{tiktok_username}/live"),
                                InlineKeyboardButton("Fullscreen", url=f"https://player3.piobot.us.to/player/#{stream_url}")
                            ]
                        ])
                        message = (
                            f"<b>{nickname}</b> sedang live <b>Tiktok</b>.\n\n"
                            f"{title_quote}\n"
                            f"🗓️ {create_time}\n"
                            f"⚡ Streaming URL: <pre>{stream_url}</pre>"
                        )
                    else:
                        reply_markup = InlineKeyboardMarkup([
                            [
                                InlineKeyboardButton("Tiktok", url=f"https://www.tiktok.com/@{tiktok_username}/live"),
                                InlineKeyboardButton("Fullscreen", url=f"https://player3.piobot.us.to/player/#{liveUrl}")
                            ]
                        ])
                        message = (
                            f"<b>{nickname}</b> sedang live <b>Tiktok</b>.\n\n"
                            f"{title_quote}\n"
                            f"🗓️ {create_time}\n"
                            f"⚡ Streaming URL: <pre>{liveUrl}</pre>"
                        )
                    
                    pesan = send_photo_and_text_to_channel(cover_url, message, reply_markup)
                    sent_message_ids_tt[tiktok_username] = pesan.message_id

                    last_user_count_tiktok[tiktok_username] = userCount
                elif not is_online and last_live_status_tiktok[tiktok_username]:
                    stream_url, create_time, finish_time = data_tt_stream_url
                    title_quote = f"<blockquote>{title}</blockquote>"

                    # Ambil waktu mulai
                    start_time = datetime.strptime(create_time, "%A, %d %b %Y | %H:%M:%S WIB")
                    end_time = datetime.strptime(finish_time, "%A, %d %b %Y | %H:%M:%S WIB")

                    # Hitung durasi
                    duration = end_time - start_time

                    # Konversi durasi ke dalam detik
                    total_seconds = duration.total_seconds()

                    # Hitung jam, menit, dan detik
                    hours = int(total_seconds // 3600)
                    minutes = int((total_seconds % 3600) // 60)
                    seconds = int(total_seconds % 60)

                    # Format durasi
                    formatted_duration = "{:02}:{:02}:{:02}".format(hours, minutes, seconds)

                    message = (
                        f"<b>{nickname}</b> telah selesai live <b>Tiktok</b>.\n\n"
                        f"{title_quote}\n"
                        f"🕙 Durasi live: <b>{formatted_duration}</b>\n"
                        f"⚡ Mulai: <b>{create_time}</b>\n"
                        f"⚡ Selesai: <b>{finish_time}</b>\n"
                        f"👥 <b>± {last_user_count_tiktok[tiktok_username]}</b>"
                    )

                    pesan_id = sent_message_ids_tt.get(tiktok_username)
                    if pesan_id:
                        edit_photo_and_text_in_channel(message, pesan_id)
                    
                    del last_user_count_tiktok[tiktok_username]
                last_live_status_tiktok[tiktok_username] = is_online

def pesan_tiktok_private(tiktok_username):
    room_id = get_tt_room_id(tiktok_username)
    if room_id:
        is_tt_live = is_user_tt_live(room_id)
        if is_tt_live:
            is_online, cover_url, title, nickname, userCount, liveUrl = is_tt_live
            data_tt_stream_url = get_tt_stream_url(room_id)
            if data_tt_stream_url:
                stream_url, create_time, finish_time = data_tt_stream_url
                if is_online and not last_live_status_tiktok[tiktok_username]:
                    title_quote = f"<blockquote>{title}</blockquote>"
                    
                    if stream_url:
                        reply_markup = InlineKeyboardMarkup([
                            [
                                InlineKeyboardButton("Tiktok", url=f"https://www.tiktok.com/@{tiktok_username}/live"),
                                InlineKeyboardButton("Fullscreen", url=f"https://player3.piobot.us.to/player/#{stream_url}")
                            ]
                        ])
                        message = (
                            f"<b>{nickname}</b> sedang live <b>Tiktok</b>.\n\n"
                            f"{title_quote}\n"
                            f"🗓️ {create_time}\n"
                            f"⚡ Streaming URL: <pre>{stream_url}</pre>"
                        )
                    else:
                        reply_markup = InlineKeyboardMarkup([
                            [
                                InlineKeyboardButton("Tiktok", url=f"https://www.tiktok.com/@{tiktok_username}/live"),
                                InlineKeyboardButton("Fullscreen", url=f"https://player3.piobot.us.to/player/#{liveUrl}")
                            ]
                        ])
                        message = (
                            f"<b>{nickname}</b> sedang live <b>Tiktok</b>.\n\n"
                            f"{title_quote}\n"
                            f"🗓️ {create_time}\n"
                            f"⚡ Streaming URL: <pre>{liveUrl}</pre>"
                        )
                    
                    pesan = send_photo_and_text_to_user(cover_url, message, reply_markup)
                    sent_message_ids_tt[tiktok_username] = pesan.message_id

                    last_user_count_tiktok[tiktok_username] = userCount
                elif not is_online and last_live_status_tiktok[tiktok_username]:
                    stream_url, create_time, finish_time = data_tt_stream_url
                    title_quote = f"<blockquote>{title}</blockquote>"

                    start_time = datetime.strptime(create_time, "%A, %d %b %Y | %H:%M:%S WIB")
                    end_time = datetime.strptime(finish_time, "%A, %d %b %Y | %H:%M:%S WIB")

                    duration = end_time - start_time

                    total_seconds = duration.total_seconds()

                    hours = int(total_seconds // 3600)
                    minutes = int((total_seconds % 3600) // 60)
                    seconds = int(total_seconds % 60)

                    formatted_duration = "{:02}:{:02}:{:02}".format(hours, minutes, seconds)

                    message = (
                        f"<b>{nickname}</b> telah selesai live <b>Tiktok</b>.\n\n"
                        f"{title_quote}\n"
                        f"🕙 Durasi live: <b>{formatted_duration}</b>\n"
                        f"⚡ Mulai: <b>{create_time}</b>\n"  # Gunakan waktu mulai asli
                        f"⚡ Selesai: <b>{finish_time}</b>\n"
                        f"👥 <b>± {last_user_count_tiktok[tiktok_username]}</b>"
                    )

                    pesan_id = sent_message_ids_tt.get(tiktok_username)
                    if pesan_id:
                        edit_photo_and_text_in_user(message, pesan_id)

                    del last_user_count_tiktok[tiktok_username]
                last_live_status_tiktok[tiktok_username] = is_online

def send_to_channel(text: str):
    bot = Bot(token=TOKEN)
    bot.send_message(chat_id=CHANNEL_ID, text=text, parse_mode='HTML')

def send_to_user(text: str):
    bot = Bot(token=TOKEN)
    bot.send_message(chat_id=CHAT_ID, text=text, parse_mode='HTML')

# send to channel
def send_photo_and_text_to_channel(photo: str, text: str, reply_markup: InlineKeyboardMarkup):
    bot = Bot(token=TOKEN)
    message = bot.send_photo(chat_id=CHANNEL_ID, photo=photo, caption=text, reply_markup=reply_markup, parse_mode='HTML')
    return message

# edit in channel
def edit_photo_and_text_in_channel(text: str, message_id: int):
    bot = Bot(token=TOKEN)
    bot.edit_message_caption(chat_id=CHANNEL_ID, message_id=message_id, caption=text, reply_markup=None, parse_mode='HTML')

# send to user
def send_photo_and_text_to_user(photo: str, text: str, reply_markup: InlineKeyboardMarkup):
    bot = Bot(token=TOKEN)
    message = bot.send_photo(chat_id=CHAT_ID, photo=photo, caption=text, reply_markup=reply_markup, parse_mode='HTML')
    return message

# edit in user
def edit_photo_and_text_in_user(text: str, message_id: int):
    bot = Bot(token=TOKEN)
    bot.edit_message_caption(chat_id=CHAT_ID, message_id=message_id, caption=text, reply_markup=None, parse_mode='HTML')

def job_showroom():
    while True:
        for room_id in ROOM_IDS:
            pesan_showroom(room_id)
        time.sleep(60)

def job_idn():
    while True:
        for channel_username in IDN_USERS:
            pesan_idn(channel_username)
        time.sleep(60)

def job_tiktok():
    while True:
        for tiktok_username in TT_USERS:
            pesan_tiktok(tiktok_username)
        time.sleep(120)

def job_tiktok_others():
    while True:
        for tiktok_username in TT_USERS_OTHERS:
            pesan_tiktok_private(tiktok_username)
        time.sleep(120)

def job_send_request():
    while True:
        httpx.get(
            HEROKU_APP_URL,
            headers = {
                "User-Agent": "Not a RoBot"
            },
            timeout=5
        )
        time.sleep(500)

def restart(update: Update, context: CallbackContext) -> None:
    chat_id = update.effective_chat.id
    if chat_id == CHAT_ID:
        try:
            headers = {
                "Accept": "application/vnd.heroku+json; version=3",
                "Authorization": "Bearer " + HEROKU_API_KEY
            }
            url = f"https://api.heroku.com/apps/{HEROKU_APP_NAME}/dynos"

            message = update.message.reply_text("Silahkan tunggu...")
            time.sleep(5)
            context.bot.deleteMessage(chat_id = update.message.chat_id,
                                       message_id = message.message_id)
            httpx.delete(url, headers=headers)
        except Exception as e:
            print(e)
            update.message.reply_text("Failed to restart Heroku app. Please try again later.")
    else:
        # Membuat tombol yang mengarah ke Anda sebagai pemilik
        reply_markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("Owner Telegram", url="https://t.me/pranendra")]
        ])
        update.message.reply_text('Maaf, Anda tidak memiliki izin untuk mengakses bot ini.\n'
                                  'Silahkan angkat kaki anda dari sini!',
                                  reply_markup=reply_markup)

def log(update: Update, context: CallbackContext) -> None:
    # Memeriksa ID pengguna yang mengirim perintah
    chat_id = update.effective_chat.id
    if chat_id == CHAT_ID:
        # Membuat file log Heroku
        with open('log.txt', 'rb') as log_file:
            # Mengirim file log ke CHAT_ID
            context.bot.send_document(chat_id=CHAT_ID, document=log_file)
    else:
        # Membuat tombol yang mengarah ke Anda sebagai pemilik
        reply_markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("Owner Telegram", url="https://t.me/pranendra")]
        ])
        update.message.reply_text('Maaf, Anda tidak memiliki izin untuk mengakses bot ini.\n'
                                  'Silahkan angkat kaki anda dari sini!',
                                  reply_markup=reply_markup)

def main() -> None:
    updater = Updater(TOKEN, use_context=True)

    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler(["restart", "r"], restart))
    dispatcher.add_handler(CommandHandler(["log", "l"], log))

    updater.start_webhook(listen="0.0.0.0", port=int(PORT), url_path=TOKEN, webhook_url=HEROKU_APP_URL + TOKEN)

    send_to_user("<b>Bot berhasil dimulai ulang!</b>\n<pre>"
                 f"Hari    : {hari_jakarta}\n"
                 f"Tanggal : {tanggal_jakarta}\n"
                 f"Waktu   : {waktu_jakarta}</pre>")
    send_to_channel("<b>Bot berhasil dimulai ulang!</b>\n<pre>"
                    f"Hari    : {hari_jakarta}\n"
                    f"Tanggal : {tanggal_jakarta}\n"
                    f"Waktu   : {waktu_jakarta}</pre>")
    LOGGER.info('Bot telah dimulai!')

    # Menjalankan job() dalam thread terpisah
    threading.Thread(target=job_showroom).start()
    threading.Thread(target=job_idn).start()
    threading.Thread(target=job_tiktok).start()
    threading.Thread(target=job_tiktok_others).start()
    threading.Thread(target=job_send_request).start() 

if __name__ == '__main__':
    main()

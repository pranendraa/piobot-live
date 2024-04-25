import time
import requests
import pytz
from datetime import datetime
from logging import basicConfig, getLogger, INFO

# Konfigurasi logger
basicConfig(
    filename="log.txt",
    format="{asctime} - [{levelname[0]}] {name} [{module}:{lineno}] - {message}",
    datefmt="%Y-%m-%d %H:%M:%S",
    style="{",
    level=INFO
)

LOGGER = getLogger("update")

jakarta_timezone = pytz.timezone('Asia/Jakarta')

# headers for the api
headers = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 10; SM-A107F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.105 Mobile Safari/537.36",
}

def get_streaming_url(room_id):
    try:
        url = f"https://www.showroom-live.com/api/live/streaming_url?room_id={room_id}"

        response = requests.get(url, headers=headers)
        data = response.json()

        streaming_url_list = data.get("streaming_url_list", [])
        for stream in streaming_url_list:
            if stream["type"] == "hls" and stream["label"] == "original quality":
                return stream["url"]

        return None
    except Exception as e:
        LOGGER.warning("Error get stream url showroom: ", e)

def check_profile_live_status(room_id):
    try:
        api = f"https://www.showroom-live.com/api/room/profile?room_id={room_id}"

        response = requests.get(api, headers=headers)
        data = response.json()

        room_url_key = data["room_url_key"]
        is_onlive = data["is_onlive"]
        image = data["image"]
        current_live_started_at = data["current_live_started_at"]
        share_url_live = data["share_url_live"]
        premium_room_type = data["premium_room_type"]

        if premium_room_type == 1:
            is_premium = True
        else:
            is_premium = False

        return room_url_key, is_onlive, image, current_live_started_at, share_url_live, is_premium
    except Exception as e:
        LOGGER.warning("Error:", e, "\nGunakan room_id yang valid!!")

def get_id_history(room_id, current_live_started_at):
    try:
        api = f"https://api.crstlnz.my.id/api/recent?sort=date&page=1&filter=all&order=-1&perpage=1&search=&room_id={room_id}&group=jkt48&type=showroom"

        waktu_mulai = datetime.fromtimestamp(current_live_started_at, tz=pytz.utc).astimezone(jakarta_timezone).strftime("%A, %d %b %Y | %H:%M:%S WIB")
        
        while True:
            response = requests.get(api, headers=headers)
            if response.status_code == 200:
                data = response.json()
                recents = data.get("recents", [])
                if recents:
                    for recent in recents:
                        api_room_id = recent.get("room_id")
                        start = recent["live_info"]["date"]["start"]
                        # Hapus "Z" dari string tanggal
                        start_without_z = start.replace("Z", "")
                        api_waktu_mulai = datetime.fromisoformat(start_without_z).astimezone(jakarta_timezone).strftime("%A, %d %b %Y | %H:%M:%S WIB")
                        if api_room_id == room_id and api_waktu_mulai == waktu_mulai:
                            data_id = recent.get("data_id")
                            return data_id
                # Jika data tidak ditemukan, tunggu sebentar sebelum mencoba lagi
                time.sleep(30)  # Anda bisa sesuaikan interval waktu menunggu
            else:
                return f"Failed to fetch data: {response.status_code}"
    except Exception as e:
        LOGGER.warning(f"Error Get ID History SR: {e}")

def get_history_live(data_id):
    try:
        api = f"https://api.crstlnz.my.id/api/recent/{data_id}"

        response = requests.get(api, headers=headers)
        data = response.json()

        waktu_mulai = data["live_info"]["date"]["start"]
        waktu_selesai = data["live_info"]["date"]["end"]
        viewers = data["live_info"]["viewers"]["num"]
        active_viewers = data["live_info"]["viewers"]["active"]
        total_gifts = data["total_gifts"]
        comments = data["live_info"]["comments"]["num"]
        users_comments = data["live_info"]["comments"]["users"]

        # hitung durasi
        durasi = calculate_duration_hhmmss(waktu_mulai, waktu_selesai)

        rupiah_gold = total_gifts * 105

        # format angka ada titiknya
        viewers = format_angka(viewers)
        active_viewers = format_angka(active_viewers)
        total_gifts = format_angka(total_gifts)
        comments = format_angka(comments)
        users_comments = format_angka(users_comments)

        return waktu_mulai, waktu_selesai, durasi, viewers, active_viewers, total_gifts, comments, users_comments, rupiah_gold
    except Exception as e:
        LOGGER.warning("Error Get History Live SR:", e)

def convert_seconds_to_hms(seconds):
    hours = seconds // 3600
    seconds -= hours * 3600
    minutes = seconds // 60
    seconds -= minutes * 60
    return int(hours), int(minutes), int(seconds)

def calculate_duration_hhmmss(start_str, end_str):
    start_time = datetime.strptime(start_str, "%Y-%m-%dT%H:%M:%S.%fZ")
    end_time = datetime.strptime(end_str, "%Y-%m-%dT%H:%M:%S.%fZ")
    duration = end_time - start_time
    total_seconds = duration.total_seconds()
    hours, minutes, seconds = convert_seconds_to_hms(total_seconds)
    return "{:02d}:{:02d}:{:02d}".format(hours, minutes, seconds)

def format_angka(angka):
    return '{:,.0f}'.format(angka).replace(',', '.')

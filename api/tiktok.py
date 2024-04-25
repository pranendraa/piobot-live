import requests
import re
import pytz
from  datetime import datetime
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
    "Referer": "https://www.tiktok.com/"
}

def get_tt_room_id(tiktok_username):
    try:
        api = f"https://www.tiktok.com/@{tiktok_username}/live"

        response = requests.get(api, allow_redirects=False, headers=headers)
        if response.status_code == 404:
            raise ValueError()

        content = response.text
        if "room_id" not in content:
            raise ValueError()

        room_id = re.findall("room_id=(.*?)\"/>", content)[0]
        return room_id
    except Exception as e:
        # print(f"Error get room id tt: {e}")
        # LOGGER.warning(f"Error get room id tt: {e}")
        pass

def is_user_tt_live(room_id):
    try:   
        url = f"https://www.tiktok.com/api/live/detail/?aid=1988&roomID={room_id}"

        # content = requests.get(url, headers=headers).text
        # return '"status":4' not in content

        content = requests.get(url, headers=headers).json()
        status = content['LiveRoomInfo']['status']
        cover_url = content['LiveRoomInfo']['coverUrl']
        title = content['LiveRoomInfo']['title']
        nickname = content['LiveRoomInfo']['ownerInfo']['nickname']
        userCount = content['LiveRoomInfo']['liveRoomStats']['userCount']
        liveUrl = content['LiveRoomInfo']['liveUrl']

        if status == 4:
            is_online = False
        else:
            is_online = True

        if '?' in liveUrl:
            base_url = liveUrl.split('?')
            liveUrl = base_url[0]
        else:
            liveUrl = liveUrl

        userCount = format_angka(userCount)

        return is_online, cover_url, title, nickname, userCount, liveUrl
    except Exception as e:
        # print(f"Error is user tt live: {e}")
        # LOGGER.warning(f"Error is user tt live: {e}")
        pass

def get_tt_stream_url(room_id):
    try:
        api = f"https://webcast.tiktok.com/webcast/room/info/?aid=1988&room_id={room_id}"

        response = requests.get(api, headers=headers)

        json = response.json()
        url = json['data']['stream_url']['hls_pull_url']
        create_time = json['data']['create_time']
        finish_time = json['data']['finish_time']

        # Konversi timestamp menjadi objek datetime
        create_time = datetime.fromtimestamp(create_time, tz=pytz.utc).astimezone(jakarta_timezone).strftime("%A, %d %b %Y | %H:%M:%S WIB")
        finish_time = datetime.fromtimestamp(finish_time, tz=pytz.utc).astimezone(jakarta_timezone).strftime("%A, %d %b %Y | %H:%M:%S WIB")

        if '?' in url:
            base_url = url.split('?')
            stream_url = base_url[0]
        else:
            stream_url = url

        return stream_url, create_time, finish_time
    except Exception as e:
        # print(f"Error get tt stream url: {e}")
        # LOGGER.warning(f"Error get tt stream url: {e}")
        pass

def format_angka(angka):
    return '{:,.0f}'.format(angka).replace(',', '.')

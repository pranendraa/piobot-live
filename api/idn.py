import time
import requests
import re
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

def get_livestreams(channel_username):
    try:
        url = "https://api.idn.app/graphql"

        # Define the GraphQL query with variables
        graphql_query = """
        query GetLivestreams($page: Int, $category: String) {
        getLivestreams(page: $page, category: $category) {
            title
            slug
            image_url
            playback_url
            status
            live_at
            scheduled_at
            category {
            name
            slug
            }
            creator {
            name
            username
            uuid
            }
        }
        }
        """

        # Create a session object
        session = requests.Session()

        # Set the initial page number and category
        page = 1
        category = "all"

        # Create a list to store all livestream data
        all_livestreams = []

        while True:
            try:
                # Set variables for the GraphQL query
                variables = {
                    "page": page,
                    "category": category
                }

                # Set data with the GraphQL query and variables
                data = {
                    "query": graphql_query,
                    "variables": variables
                }

                # Send a POST request to the GraphQL API
                response = session.post(url, json=data, headers=headers)

                # Check the status code
                if response.status_code == 200:
                    # Handle JSON response from the API
                    data = response.json()

                    # Check if there is no more data
                    if not data.get("data", {}).get("getLivestreams"):
                        break

                    # Iterate through the livestreams and add them to the list
                    for livestream in data["data"]["getLivestreams"]:
                        all_livestreams.append(livestream)

                    # Increment the page number for the next iteration
                    page += 1
                else:
                    print(f"Error: {response.status_code}, {response.text}")
                    pass  # pass to the next iteration in case of an error
            except Exception as e:
                LOGGER.warning(f"Error get slug IDN, Exception: {e}")
                pass  # pass to the next iteration in case of an exception

        # Extract and print M3U8 streaming URLs for JKT48 members
        for livestream in all_livestreams:
            if "creator" in livestream and "username" in livestream["creator"]:
                username = livestream["creator"]["username"]
                if re.fullmatch(f"{channel_username}$", username):
                    slug = livestream["slug"]
                    # playback_url = livestream["playback_url"]

                    return slug
            
        return None
    except Exception as e:
        LOGGER.warning(f"Error get livestream idn: {e}")

def get_infodata(slug):
    try:
        req = requests.get(f"https://www.idn.app/mobile-api/v3/livestream/{slug}", headers=headers)

        content = req.json()
        status = content['data']['status']
        title = content['data']['title']
        image_url = content['data']['image_url']
        name = content['data']['creator']['name']
        view_count = content['data']['view_count']
        live_at = content['data']['live_at']
        end_at = content['data']['end_at']
        playback_url = content['data']['playback_url']

        if status == "live":
            is_status_online = True
        else:
            is_status_online = False

        # Convert live_at and end_at times to Jakarta timezone
        live_at_jakarta = datetime.fromtimestamp(live_at, tz=pytz.utc).astimezone(jakarta_timezone).strftime("%A, %d %b %Y | %H:%M:%S WIB")
        end_at_jakarta = datetime.fromtimestamp(end_at, tz=pytz.utc).astimezone(jakarta_timezone).strftime("%A, %d %b %Y | %H:%M:%S WIB")

        view_count = format_angka(view_count)

        durasi_live = calculate_duration_hhmmss2(live_at, end_at)

        return title, name, view_count, durasi_live, live_at_jakarta, end_at_jakarta, playback_url, is_status_online, image_url
    except Exception as e:
        LOGGER.warning(f"Error get infodata idn: {e}")

def get_id_history_idn(slug):
    try:
        api = "https://api.crstlnz.my.id/api/recent?sort=date&page=1&filter=all&order=-1&group=jkt48&type=idn"

        while True:
            response = requests.get(api, headers=headers)
            if response.status_code == 200:
                data = response.json()
                recents = data.get("recents", [])
                if recents:
                    for recent in recents:
                        api_slug = recent["idn"]["slug"]
                        if api_slug == slug:
                            data_id = recent.get("data_id")
                            return data_id
                # Jika data tidak ditemukan, tunggu sebentar sebelum mencoba lagi
                time.sleep(30)  # Anda bisa sesuaikan interval waktu menunggu
            else:
                return f"Failed to fetch data: {response.status_code}"
    except Exception as e:
        LOGGER.warning("Error Get ID History IDN:", e)

def get_history_live_idn(data_id):
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

        rupiah_gold = total_gifts * 2500

        # ubah tanggal
        waktu_mulai_without_z = waktu_mulai.replace("Z", "")
        waktu_selesai_without_z = waktu_selesai.replace("Z", "")
        waktu_mulai_jakarta = datetime.fromisoformat(waktu_mulai_without_z).astimezone(jakarta_timezone).strftime("%A, %d %b %Y | %H:%M:%S WIB")
        waktu_selesai_jakarta = datetime.fromisoformat(waktu_selesai_without_z).astimezone(jakarta_timezone).strftime("%A, %d %b %Y | %H:%M:%S WIB")

        # format angka ada titiknya
        viewers = format_angka(viewers)
        active_viewers = format_angka(active_viewers)
        total_gifts = format_angka(total_gifts)
        comments = format_angka(comments)
        users_comments = format_angka(users_comments)

        return waktu_mulai_jakarta, waktu_selesai_jakarta, durasi, viewers, active_viewers, total_gifts, comments, users_comments, rupiah_gold
    except Exception as e:
        LOGGER.warning("Error Get History Live IDN:", e)

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

def calculate_duration_hhmmss2(start_str, end_str):
    start_time = datetime.fromtimestamp(start_str)
    end_time = datetime.fromtimestamp(end_str)
    duration = end_time - start_time
    total_seconds = duration.total_seconds()
    hours, minutes, seconds = convert_seconds_to_hms(total_seconds)
    return "{:02d}:{:02d}:{:02d}".format(hours, minutes, seconds)

def format_angka(angka):
    return '{:,.0f}'.format(angka).replace(',', '.')

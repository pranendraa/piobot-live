import os
import subprocess
import requests
from io import StringIO
from logging import basicConfig, getLogger, INFO
from dotenv import load_dotenv

# Konfigurasi logger
basicConfig(
    filename="log.txt",
    format="{asctime} - [{levelname[0]}] {name} [{module}:{lineno}] - {message}",
    datefmt="%Y-%m-%d %H:%M:%S",
    style="{",
    level=INFO,
)

LOGGER = getLogger("update")

# Mendapatkan isi dari file .env di GitHub Gist
CONFIG_FILE_URL = os.getenv("CONFIG_FILE_URL", "")
response = requests.get(CONFIG_FILE_URL)
env_content = response.text

# Membuat buffer string dan menulis isi .env ke dalamnya
env_buffer = StringIO(env_content)

# Memuat variabel dari buffer menggunakan load_dotenv
load_dotenv(stream=env_buffer)

UPSTREAM_REPO = os.getenv("UPSTREAM_REPO")
UPSTREAM_BRANCH = os.getenv("UPSTREAM_BRANCH")

# Perbarui repositori GitHub
if UPSTREAM_REPO is not None:
    if os.path.exists(".git"):
        subprocess.run([
            "rm -rf .git"
        ], shell=True)

    process = subprocess.run([
            f"git init -q \
            && git config --global user.email evanfauzi0@gmail.com \
            && git config --global user.name pranendraa \
            && git add . \
            && git commit -sm update -q \
            && git remote add origin {UPSTREAM_REPO} \
            && git fetch origin -q \
            && git reset --hard origin/{UPSTREAM_BRANCH} -q"
        ], shell=True)

    if process.returncode == 0:
        LOGGER.info("Successfully updated with latest commit from UPSTREAM_REPO!")
    else:
        LOGGER.error(
            "Something wrong while updating! Check UPSTREAM_REPO if valid or not!")

else:
    LOGGER.warning("UPSTREAM_REPO is not found!")

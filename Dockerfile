FROM ubuntu:latest

WORKDIR /app

COPY . .

# Install dependensi yang dibutuhkan
RUN apt-get update && apt-get install -y python3 python3-pip locales git && \
    sed -i -e 's/# id_ID.UTF-8 UTF-8/id_ID.UTF-8 UTF-8/' /etc/locale.gen && \
    locale-gen && \
    pip3 install --no-cache-dir -r requirements.txt

CMD ["bash", "start.sh"]
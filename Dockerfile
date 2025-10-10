FROM dvivanov/wst-base:v0.2

LABEL version="0.2"
LABEL project="wst"

WORKDIR /project

COPY requirements.txt requirements.txt
RUN pip3 install --ignore-installed --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONPATH='/project/:/project/app/'
WORKDIR /project/app

RUN STATIC_HASH=$(find app/static -type f -exec md5sum {} \; | md5sum | cut -d' ' -f1) && \
    echo $STATIC_HASH >> /APP_STATIC_HASH 

ENV APP_STATIC_HASH_FILE=/APP_STATIC_HASH
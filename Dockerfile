FROM python:3.6
WORKDIR /app
COPY . .
RUN apt-get update
RUN apt-get install -y vim ffmpeg exiftool inkscape
RUN pip install -r requirements.txt
ENV PYTHONPATH='/app'
WORKDIR /app/app
CMD /bin/bash

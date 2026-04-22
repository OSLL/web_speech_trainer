FROM dvivanov/wst-base:v0.2

LABEL version="0.3"
LABEL project="wst"

WORKDIR /project

COPY requirements.txt ./
RUN python3 -m pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONPATH='/project/:/project/app/'
WORKDIR /project/app
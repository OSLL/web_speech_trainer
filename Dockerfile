FROM dvivanov/wst-base:v0.3

LABEL version="0.3"
LABEL project="wst"

ENV PYTHONPATH="/project/:/project/app/"

WORKDIR /project

COPY requirements.txt ./
RUN python -m pip install --no-cache-dir -r requirements.txt

COPY . .

WORKDIR /project/app
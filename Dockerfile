FROM dvivanov/wst-base:v0.2

LABEL version="0.2"
LABEL project="wst"

WORKDIR /project

COPY . .

ENV PYTHONPATH='/project/:/project/app/'
WORKDIR /project/app
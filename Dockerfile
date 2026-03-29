FROM dvivanov/wst-base:v0.2

LABEL version="0.2"
LABEL project="wst"

WORKDIR /project

COPY requirements.txt /project/requirements.txt
RUN python3 -m pip install --ignore-installed -r /project/requirements.txt

COPY . .

ENV PYTHONPATH='/project/:/project/app/'
WORKDIR /project/app
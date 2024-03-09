FROM dvivanov/wst-base:v0.2

LABEL version="0.2"
LABEL project="wst"

WORKDIR /project

COPY requirements.txt requirements.txt

RUN pip3 install --ignore-installed -r requirements.txt

COPY . .
RUN rm -rf /project/tests/selenium

ENV PYTHONPATH='/project/:/project/app/'
WORKDIR /project/app

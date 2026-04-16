FROM dvivanov/wst-base:v0.2

LABEL version="0.2"
LABEL project="wst"

WORKDIR /project

COPY requirements.txt requirements.txt
RUN pip3 install --ignore-installed --no-cache-dir -r requirements.txt

RUN mkdir -p /root/nltk_data
ENV NLTK_DATA=/root/nltk_data
RUN python3 -c "import nltk; nltk.download('punkt', download_dir='/root/nltk_data', quiet=True)"
RUN python3 -c "import nltk; nltk.download('stopwords', download_dir='/root/nltk_data', quiet=True)"

COPY . .

ENV PYTHONPATH='/project/:/project/app/'
WORKDIR /project/app
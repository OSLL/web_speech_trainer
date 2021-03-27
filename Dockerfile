FROM ubuntu:18.04
ENV LANG C.UTF-8

WORKDIR /app
COPY . .
RUN apt-get update
RUN apt-get install -y python3-pip vim ffmpeg exiftool inkscape mupdf mupdf-tools
RUN pip3 install --upgrade pip
RUN pip3 install --upgrade setuptools

# The installation of `fitz` library is really tricky.
# The library uses `frontend` internal package that can be obtained
# via installation if `PyMuPDF` package but `PyMuPDF` itself requires fitz.
# That's why fitz is installed separately.
RUN pip3 install fitz

RUN pip3 install -r requirements.txt
ENV PYTHONPATH='/app'
WORKDIR /app/app
CMD /bin/bash

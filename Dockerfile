FROM osll/wst_base:v0.1

RUN apt update

# The installation of `fitz` library is really tricky.
# The library uses `frontend` internal package that can be obtained
# via installation of `PyMuPDF` package but `PyMuPDF` itself requires `fitz`.
# That's why `fitz` is installed separately.
RUN pip3 install fitz==0.0.1.dev2

WORKDIR /app
COPY . .

RUN pip3 install -r requirements.txt
ENV PYTHONPATH='/app/:/app/app/'
WORKDIR /app/app
CMD /bin/bash

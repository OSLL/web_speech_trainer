FROM plyushchenko/ubuntu_python3:latest

WORKDIR /app
COPY . .

# The installation of `fitz` library is really tricky.
# The library uses `frontend` internal package that can be obtained
# via installation of `PyMuPDF` package but `PyMuPDF` itself requires `fitz`.
# That's why `fitz` is installed separately.
RUN pip3 install fitz

RUN pip3 install -r requirements.txt
ENV PYTHONPATH='/app'
WORKDIR /app/app
CMD /bin/bash

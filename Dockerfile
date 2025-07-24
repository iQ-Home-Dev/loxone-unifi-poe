FROM python:3.10.10-alpine

WORKDIR /usr/src/app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY data data/
COPY bin/loxone-unifi-poe.py bin/loxone-unifi-poe.py

CMD [ "python", "./bin/loxone-unifi-poe.py" ]

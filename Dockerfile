FROM python:3.10.10-alpine

WORKDIR /usr/src/app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY unifi_poe/unifi.py unifi_poe/unifi.py
COPY loxone-unifi-poe.py loxone-unifi-poe.py

CMD [ "python", "./loxone-unifi-poe.py" ]

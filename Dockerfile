FROM python:3-slim

RUN ln -sf /bin/bash /bin/sh
RUN useradd -ms /bin/bash alarmebot
USER alarmebot

WORKDIR /home/alarmebot/Documents

COPY requirements.txt ./
COPY .env ./
COPY alarmeBot.py ./

RUN pip install --no-cache-dir --disable-pip-version-check -r requirements.txt

CMD [ "python", "./alarmeBot.py" ]

FROM python:3.6
RUN useradd -m aviapayroll && mkdir /usr/src/app && chown aviapayroll /usr/src/app
USER aviapayroll
WORKDIR /usr/src/app/
COPY requirements.txt /usr/src/app/
RUN pip3 install -r requirements.txt --user --src=$HOME/.local/lib/python3.6/site-packages
COPY . /usr/src/app/
CMD $HOME/.local/bin/gunicorn --reload -k aiohttp.worker.GunicornWebWorker --bind 0.0.0.0:$PORT main:app
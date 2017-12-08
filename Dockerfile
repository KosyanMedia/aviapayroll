FROM python:3.6
RUN set -ex && useradd -m aviapayroll && mkdir /usr/src/app\
    && chown aviapayroll /usr/src/app\
    && pip3 install pipenv==9.0.0
WORKDIR /usr/src/app/

COPY Pipfile Pipfile
COPY Pipfile.lock Pipfile.lock
RUN set -ex && pipenv install --deploy --system

USER aviapayroll
COPY . /usr/src/app/
CMD gunicorn --reload -k aiohttp.worker.GunicornWebWorker --bind 0.0.0.0:$PORT main:app
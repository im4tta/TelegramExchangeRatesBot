FROM python:3.7.2-slim

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /code

COPY wait-for-it.sh ./

# coverage
RUN apt-get update \
    && apt-get -y install --no-install-recommends git \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

RUN pip install pipenv==2018.11.26 codecov==2.0.15 codacy-coverage==1.3.11
COPY Pipfile Pipfile.lock ./
RUN pipenv install --system --dev

COPY . .

CMD [ "python manage.py start" ]

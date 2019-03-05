FROM python:3.7.2-slim

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /code

RUN pip install pipenv
COPY Pipfile Pipfile.lock ./
RUN pipenv install --system --deploy --dev

COPY wait-for-it.sh ./

COPY . .

CMD [ "python manage.py start" ]

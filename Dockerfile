FROM python:3.7-alpine

RUN mkdir /code
RUN mkdir /keys
COPY . /code
WORKDIR /code

RUN pip3 install -r requirements.txt

ENTRYPOINT ["flask", "run", "--host=0.0.0.0"]
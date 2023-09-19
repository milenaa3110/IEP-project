FROM python:3

RUN mkdir -p /opt/src/migration
WORKDIR /opt/src/migration


COPY ./migrate.py ./migrate.py
COPY ./configuration.py ./configuration.py
COPY ./models.py ./models.py
COPY authentication/requirements.txt ./requirements.txt
RUN pip install -r ./requirements.txt

ENTRYPOINT ["python", "./migrate.py"]
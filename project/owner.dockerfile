FROM bde2020/spark-python-template:3.3.0-hadoop3.3


RUN apk --no-cache add python3 py3-pip


RUN if [ ! -e /usr/bin/python ]; then ln -sf python3 /usr/bin/python; fi
RUN if [[ ! -e /usr/bin/pip ]]; then ln -sf pip3 /usr/bin/pip; fi


RUN mkdir -p /opt/src/owner
WORKDIR /opt/src/owner


COPY owner/application.py ./application.py
COPY owner/configuration.py ./configuration.py
COPY owner/mysql-connector-j-8.0.33.jar ./mysql-connector-j-8.0.33.jar
COPY owner/requirements.txt ./requirements.txt
COPY owner/productStatistics.py ./productStatistics.py
COPY owner/categoryStatistics.py ./categoryStatistics.py
COPY authentication/roleCheckDecorator.py ./roleCheckDecorator.py
COPY ../models.py ./models.py

RUN pip3 install --upgrade pip && pip3 install -r ./requirements.txt

CMD [ "python3", "/opt/src/owner/application.py" ]

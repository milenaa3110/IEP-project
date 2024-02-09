FROM ethereum/solc:0.8.0-alpine as builder

RUN mkdir -p /opt/src/customer

WORKDIR /opt/src/customer

COPY solidity/OrderContract.sol ./OrderContract.sol

RUN solc --bin --abi -o output/ OrderContract.sol

FROM python:3

COPY --from=builder /opt/src/customer/output/ ./output/

COPY customer/application.py ./application.py
COPY customer/configuration.py ./configuration.py
COPY customer/requirements.txt ./requirements.txt
COPY authentication/roleCheckDecorator.py ./roleCheckDecorator.py
COPY ./models.py ./models.py

RUN pip install -r ./requirements.txt

ENTRYPOINT ["python", "-u", "./application.py"]
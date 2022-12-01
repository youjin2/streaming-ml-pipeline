FROM python:3.9

RUN pip install --upgrade pip setuptools wheel

# set workdir
WORKDIR /opt/src/

# install external packages
COPY requirements.txt .
RUN pip install -r requirements.txt

# install connectors on Debezium
# (run this script while creating a container in docker-compose)
COPY ./connector/debezium_connectors.py .

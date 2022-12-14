## Introduction
In this project, we will cover a brief introduction to ML serving pipeline processing real-time streaming data with `Apache Kafka`. 
More specifically, we will use `Debezium` to automatically capture changes of the database, and `BentoML` to serve the ML model and get the predictions for the target event. 
A detailed description to these frameworks will be covered in later sections. 

Dataset used in this project is `Ford car price prediction dataset` providede by `Kaggle`. 
The goal is to predict the price of used car given information such as the year, transmission type, and engine size etc, and we are going to train `XGBoostRegressor` to build ML model predicting the used car price.


## Dependencies
Dependencies required to reproduce this project are:
- Docker
- docker-compose
- Python >= 3.9
- bentoml==1.0.6


## Train & Deploy Bentoml Model
[BentoML] is an unified model serving framework that enables ML engineers to accelerate and standardize the process of taking ML models into production.
As mentioned in the `Introduction`, we will use `BentoML` as a framework to serve the ML model throughout this project.
If you are a beginner to `BentoML`, [Tutorial: Intro to BentoML] would be a nice introduction.  
Now, let's get start training our car price predicting model.

**i) Build python-dev environment used to train and deploy our ML model**
```bash
$ docker-compose -f docker-compose-dev.yml build

# check that the "streaming-ml-jupyter" image created
$ docker images

# output:
REPOSITORY                                        TAG                IMAGE ID       CREATED        SIZE
streaming-ml-jupyter                              0.1.0              5b4e80dc8277   2 weeks ago    2.13GB

# run docker container for training the model
$ docker-compose -f docker-compose-dev.yml up -d
$ docker exec -it jupyter /bin/bash
```

**ii) Train car prediction ML model and save it as a `BentoML model`**

A detailed code examples for EDA about `Ford used car dataset` and training process including data-preprocessing steps can be found at:
- [01\_eda\_ford\_used\_car\_dataset.ipynb]
- [02\_train\_car\_price\_prediction\_model.ipynb]

In case you want to skip the above examples, I have written a Python script that trains the ML model and save it as a `BentoML` model.  
In that case, just run commands below in the docker container:
```bash
# train and save the BentoML model
$ python -m src.train

# check out the saved models list
$ bentoml models list

# output: 
 Tag                                   Module           Size        Creation Time
 ford_used_car_price:mh5soxdweoxxmasc  bentoml.sklearn  390.06 KiB  2022-12-03 12:05:17
```

**iii) Test `Bento` serving API**

You can test the serving API by running commands below in docker container:
```bash
# launch api server inside "jupyter" docker container
$ bentoml serve service.py:svc --host 0.0.0.0 --port 3000 --reload

# get api response by running below on local machine
# (or you can also get the response in docker container by changing the port to 3000)
$ curl -X \
    POST -H "content-type: application/json" \
    --data '{"model": ["C-MAX", "EcoSport"], "year": [2014, 2019], "price": [8295, 18995], "transmission": ["Semi-Auto", "Automatic"], "mileage": [40000, 1400], "fuelType": ["Diesel", "Petrol"], "tax": [160, 150], "mpg": [50.4, 44.1], "engineSize": [2.0, 1.0]}' \
    http://0.0.0.0:12000/predict
```
Moreover, a Python example for API request also can be found at [03\_api\_requests\_example.ipynb].

**NOTE:** If you got an error message like below in your API server logs, check whether the `n_jobs` argument of `sklearn` `ColumnTransformer` is set to 1 correctly.
(`BentoML` save/restore the sklearn model instance with `joblib.dump/joblib.load` which preserves the `n_jobs` argrument and this raises a seg-fault error.)

```bash
joblib.externals.loky.process_executor.TerminatedWorkerError: A worker process managed by the executor was unexpectedly terminated.
This could be caused by a segmentation fault while calling the function or by an excessive memory usage causing the Operating System to kill the worker.
The exit codes of the workers are {SIGTERM(-15)}
```

**iv) Build the Bento**

Now, let's build the `Bento` to deploy it as a docker image:
```bash
# project root
$ cd /opt/project

# build the bento (note that the "bentofile.yaml" must be defined in advance)
# $ bentoml build --version 0.1.0
# $ bentoml delete price_prediction_service:0.1.0
$ bentoml build

# check the built bento
$ bentoml list

# output:
 Tag                                        Size        Creation Time        Path
 price_prediction_service:56n5jrtweondqasc  411.61 KiB  2022-12-03 12:05:23  /opt/project/bentoml/bentos/price_prediction_service/ym3pedttakagcasc

# test production api server
$ bentoml serve --host price_prediction_service --host 0.0.0.0 --port 3000 --production
```

**NOTE:** The entire pipeline codes (`src/pipeline/*.py`) must be included in `bentofile` because `BentoML` uses the `joblib.dump`, which stores the entire path of the module imported, to save the sklearn instance.


**v) Containerize the Bento**

Finally, containerize the `Bento` built in the previous step for use in the streaming ML pipeline:
```bash
# project root
$ cd streaming-ml-pipeline/

$ export BENTOML_HOME=`pwd`/bentoml/ && bentoml containerize price_prediction_service:latest -t price_prediction_service:0.1.0

# check that the "streaming-ml-jupyter" image created
$ docker images

# output:
REPOSITORY                                        TAG                IMAGE ID       CREATED        SIZE
price_prediction_service                          0.1.0              1a6fb70af53f   12 days ago    1.15GB
streaming-ml-jupyter                              0.1.0              5b4e80dc8277   2 weeks ago    2.13GB

# docker
$ docker run --rm -p 12000:3000 price_prediction_service:0.1.0 serve --production
```


## Setup streaming-ml pipeline
So far, we've trained a ML model predicting the used car price and deployed it as a containerized API service to be used for streaming-ml-pipeline. 
Now it's time to build the streaming-ml-pipeline.

Before we get into it, let's first define the problem.

> Suppose you are operating a trading platform where user can sell their car after registering some required information.
Users can set the selling price by themselves, but if they don't know the proper price, they may need some recommendation about it.  
To this end, we're going to build an API service which suggests (or predicts) the appropriate price whenever user create a new record.

For this, `Kafka` and `Debezium` are needed.

[Kafka] is an open-source distributed event streaming platform used to build a real-time data streaming pipeline.  
The main components of Kafka are:
- `Topic`: a category or a feed to which records are published
- `Event`: each record in the log that consumer and producer exchange data
- `Broker`: a server that runs Kafka and stores streams of records in topics
- `Consumer`: read data from brokers
- `Producer`: write data to brokers

There are many other concepts you need to know about Kafka, but for now just mention above componets and let's learn more about Debezium.

[Debezium] is an open-source distributed platform for change data capture (CDC). 
It is built on top of Apache Kafka and provides a set of connectors that enable user to capture changes in various data sources, such as databases, and stream the changes to Kafka.

Note that I have already mentioned before, there're two connectors in Kafka: source connector and sink connector.
We're going to create these connectors in Debezium, so that whenever user registers a car information, this change will be detected through the source connector.
And it will also be sent to the `BentoML API server` to predict the car price and finally save this updated information through the sink connector.

The Proposed architecture for these process is:

![title](./docs/figures/architecture.png)


**i) Build streaming-ml pipeline**

All the infrastructure above can be built with containers:
```bash
$ docker-compose -f docker-compose.yml build

# check that the "streaming-ml-jupyter" image created
$ docker images

# output:
REPOSITORY                                        TAG                IMAGE ID       CREATED        SIZE
streaming-ml-python-app                           0.1.0              858525c42981   11 days ago    953MB
price_prediction_service                          0.1.0              1a6fb70af53f   12 days ago    1.15GB
streaming-ml-debezium                             0.1.0              00bbf6094025   2 weeks ago    941MB
streaming-ml-jupyter                              0.1.0              5b4e80dc8277   2 weeks ago    2.13GB
streaming-ml-postgres                             0.1.0              40039281dc29   3 weeks ago    314MB

# run docker-stack containers
$ docker-compose up -d
```
**NOTE:** Since the service `bento_server` dependes on the already built bento, you need to train & build the bento in advance before trying to build this docker-stack images.


**ii) Setup Postgres**

As you can see in `docker-compose.yml`, we will use `Postgres` as our database throughout this project.  
I've already prepared init sql file creating the `DATABASE.PUBLIC.TBL_CAR_PRICE` table while building postgres container image.  
You can check out table lists in the database using Python with:
```python
import pandas as pd
import psycopg2


conn = psycopg2.connect(
    host="postgres",
    port="5432",
    user="postgres",
    password="postgres",
    database="database",
)

c = conn.cursor()
c.execute(
"""
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public'
"""
)
print(c.fetchall())

# output:
[('tbl_car_price',)]
```

**NOTE:** `wal_level=logical` to `Postgres` work correctly with `Debezium`.


**iii) Setup Debezium & Kafka**

As mentioned before, we need to create source/sink connector in `Debezium` and this can be done by sending a `POST` request to the endpoint of `Debezium` connectors. 
See [python-app/connector/debezium\_connectors.py] for more details, and once the `Debezium` container is running, check the endpoints below to see if the connector was created succesfully.
- Debezium API endpoint: http://0.0.0.0:8083/
- Plugins endpoint: http://0.0.0.0:8083/connector-plugins/
- Connectors endpoint: http://0.0.0.0:8083/connectors/

You can check the list of source/sink connectors on the Connectors endpoint:
```bash
[
    "sink_pg_car_connector",
    "source_pg_car_connector"
]
```

**NOTE:** We didn't created a database table for sink topic, since `Debezium` automatically create this table by inferring schema when the first message is sent to the sink topic.

**iv) Connecting Kafka and ML model**

Now, we have built the main parts of our streaming-ml pipeline:  
- Process streaming data with `Kafka/Debezium`  
- Serve ML model with `BentoML`

All that reamains is to connect each component to send a streaming data to the ML server to get the predicted car price and store them in a database, which can be done using a `Python script`. 
Specifically, we can put all these components together by using a `Kafka consumer/producer` instances which can be simply created using [confluent-kafka] libray.  

The codes below is a brief summary of the `Python script` and detailed definition about `KafkaBuilder & RequestHandler` can be found at [python-app/app/main.py].
```python
# create Kafka consumer/producer instance
builder = KafkaBuilder()

# ML API server
api_handler = RequestHandler()

while True:
    msg = builder.consumer.poll(1.0)
    if msg is None:
        continue
    if msg.value() is None:
        continue
    if msg.error():
        logging.error("Consumer error: {}".format(msg.error()))
        continue

    # retrieve the message and the key
    message = msg.value().decode("utf-8")
    key = msg.key().decode("utf-8")

    # get predicted car price
    message_dict = json.loads(message)
    input_dict = api_handler.parse_inputs(message_dict=message_dict)

    # update the suggested price field
    pred_price = api_handler.predict(input_dict=input_dict)
    message_dict["payload"]["suggested_price"] = pred_price

    # send the message to the sink topic with the suggested price
    builder.producer.produce(
        SINK_TOPIC,
        key=key,
        value=json.dumps(message_dict)
    )
    builder.producer.flush(1)
```



**v) Streaming-ML pipeline Example**

Up to now, we have seen how to build a streaming-ml pipeline using `Kafka/Debezium` and `BentoML`. 
To do this, we created a `Python App` which detects the changes of the `car database`, and sends them to a `Kafka topic`, and then predicts the `car price` by sending a `POST` request to the `ML API server`

Now, let's figure out how the entire pipeline works as expeceted with a simple example.

First, we are going to use `Adminer`, which is a database management tool written in `PHP`, to manage the stream data.
We have already run it as a docker container while running docker-compose, so just open `Adminer` web (http://0.0.0.0:8080/) and login to it as below.

![title](docs/figures/adminer_login.png)

And then, open a new terminal and run commands below in `Kafka` container to check the standard output of streaming data sent to the `Kafka source topic`.
```bash
# kafka conatiner
$ docker exec -it kafka /bin/bash

# monitor consumer logs
$ kafka-console-consumer.sh --bootstrap-server kafka:9092 --topic car_database.public.tbl_car_price
```

After running commands above, you can see the logs like below. (Don't worry about the error messages appeared, since it can happen when you run the commands before `Debezium` server finished running.)

![title](docs/figures/kafka_consumer_example1.png)


Now, let's make make some example records and see how it sent to the `Kafka source topic`.  
You can create an example record using `SQL command` (left) or by clicking `New item bottn` (right).

<img src="docs/figures/adminer_insert_example1.png" width="420"/> <img src="docs/figures/adminer_insert_example2.png" width="420" height=230/> 
<!--![alt-text-1](docs/figures/adminer_insert_example1.png "title-1") ![alt-text-2](docs/figures/kafka_consumer_example2.png "title-2")-->

**NOTE:** Below is an example `SQL query` for writing record to `tbl_car_price` table.
```sql
INSERT INTO
    tbl_car_price
(
    MODEL,
    YEAR,
    TRANSMISSION,
    MILEAGE,
    FUEL_TYPE,
    TAX,
    MPG,
    ENGINE_SIZE
)
VALUES
(
    'Fiesta',
    2017,
    'Automatic',
    13000,
    'Petrol',
    140,
    43.2,
    1.2
);
```


The data we have created just before can be found at `Adminer -> tbl_car_price -> select`.

![title](docs/figures/adminer_insert_example3.png)

Also, the messages created on `Kafka` can be checked in the termina log which we previously executed in `Kafka container`.
The message is written in [AVRO], the leading serialization format for record data, which can be understood as `JSON with a schema`.

![title](docs/figures/kafka_consumer_example3.png)


If the messages are created succesfully on `Kafka`, then the `Python App` predicts the car price by parsing and sending them to the `BentoML server`.  

We can the check the output logs with command below:
```bash
$ docker logs python-app
```
![title](./docs/figures/python_app_logs.png)

Finally, if there's no problem in the app log, check whether the message including `suggested_price` field is written in `car_data_predicted` table on `Adiminer`.

See `Adminer -> tbl_car_price -> select` for source table (left), and `Adminer -> car_data_predicted -> select` for sink table (right).

<img src="docs/figures/kafka_source_topic.png" width="440"/> <img src="docs/figures/kafka_sink_topic.png" width="440" height=312/> 

**NOTE:** You can make an API request to `Bento Server` which is used in `Python App` with:
```python
>>> import requests

>>> inputs = {'engineSize': [1.2], 'fuelType': ['Diesel'], 'mileage': [5060], 'model': ['C-MAX'], 'mpg': [45.2], 'tax': [165], 'transmission': ['Manual'], 'year': [2017]}
>>> response = requests.post("http://bento-server:3000/predict", json=inputs)
```

The domain name for `Bento Server` follows the container name defined in `docker-compose` and you can also use IP address by identifying the network address used in docker-compose.
(but, ip address may varies when you re-running the docker-compose)
```bash
$ docker inspect -f '{{.Name}} - {{range $net,$v := .NetworkSettings.Networks}}{{printf "%s" $net}}{{end}} - {{range .NetworkSettings.Networks}}{{.IPAddress}} - {{.NetworkID}}{{end}}' $(docker ps -aq)
```


## References
- [Machine Learning Streaming with Kafka, Debezium, and BentoML]
- [Introduction to Kafka]
- [Streaming data to a downstream database]
- [Tutorial: Intro to BentoML]
- [Brief introduction to BentoML on my repo]
- [Ford Car Prediction Dataset (Kaggle)]


[Machine Learning Streaming with Kafka, Debezium, and BentoML]: https://towardsdatascience.com/machine-learning-streaming-with-kafka-debezium-and-bentoml-c5f3996afe8f
[Introduction to Kafka]: https://docs.confluent.io/5.5.1/kafka/introduction.html
[Streaming data to a downstream database]: https://debezium.io/blog/2017/09/25/streaming-to-another-database/
[Tutorial: Intro to BentoML]: https://docs.bentoml.org/en/latest/tutorial.html
[Brief introduction to BentoML on my repo]: https://github.com/youjin2/mlops/tree/main/bentoml
[ml-streaming-kafka-cdc-github]: https://github.com/jaumpedro214/ml-streming-kafka-cdc
[Ford Car Prediction Dataset (Kaggle)]: https://www.kaggle.com/datasets/mysarahmadbhat/ford-used-car-listing
[BentoML]: https://docs.bentoml.org/en/latest/index.html
[Kafka]: https://kafka.apache.org/
[Debezium]: https://debezium.io/
[01\_eda\_ford\_used\_car\_dataset.ipynb]: https://github.com/youjin2/streaming-ml-pipeline/blob/main/notebooks/01_eda_ford_used_car_dataset.ipynb
[02\_train\_car\_price\_prediction\_model.ipynb]: https://github.com/youjin2/streaming-ml-pipeline/blob/main/notebooks/02_train_car_price_prediction_model.ipynb
[03\_api\_requests\_example.ipynb]: https://github.com/youjin2/streaming-ml-pipeline/blob/main/notebooks/03_api_requests_example.ipynb
[python-app/connector/debezium\_connectors.py]: https://github.com/youjin2/streaming-ml-pipeline/blob/main/docker/python-app/connector/debezium_connectors.py
[python-app/app/main.py]: https://github.com/youjin2/streaming-ml-pipeline/blob/main/docker/python-app/app/main.py
[confluent-kafka]: https://github.com/confluentinc/confluent-kafka-python
[AVRO]: https://avro.apache.org/

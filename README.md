## Introduction
In this project, we will cover a brief introduction to ML serving pipeline processing real-time streaming data with `Apache Kafka`. 
More specifically, we will use `Debezium` to automatically capture changes in the database, and `BentoML` to serve the ML model and get the predictions for the target event. 
A detailed description to these frameworks will be covered in later sections. 

Dataset used in this project is `Ford car price prediction dataset` providede by `Kaggle`. 
The goal is to predict the price of used car given information such as the year, transmission type, and engine size etc, and we are going to train `XGBoostRegressor` to build ML model predicting the used car price.


## Dependencies
- docker
- docker-compose


## Train & Save Bentoml Model
Setup dev environment.
```bash
# build jupyter & bnetoml serve docker stack
$ docker-compose -f docker-compose-dev.yml build

# run docker container for training the model
$ docker-compose -f docker-compose-dev.yml up -d
```

Train the car price predicting model.
```bash
$ python -m src.train

$ bentoml models list

# output: 
 Tag                                   Module           Size        Creation Time
 ford_used_car_price:mh5soxdweoxxmasc  bentoml.sklearn  390.06 KiB  2022-12-03 12:05:17

# launch api server
$ bentoml serve service.py:svc --host 0.0.0.0 --port 3000 --reload

# response
$ curl -X \
    POST -H "content-type: application/json" \
    --data '{"model": ["C-MAX", "EcoSport"], "year": [2014, 2019], "price": [8295, 18995], "transmission": ["Semi-Auto", "Automatic"], "mileage": [40000, 1400], "fuelType": ["Diesel", "Petrol"], "tax": [160, 150], "mpg": [50.4, 44.1], "engineSize": [2.0, 1.0]}' \
    http://0.0.0.0:12000/predict
```

ColumnTransformer `n_jobs` argument
```bash
joblib.externals.loky.process_executor.TerminatedWorkerError: A worker process managed by the executor was unexpectedly terminated.
This could be caused by a segmentation fault while calling the function or by an excessive memory usage causing the Operating System to kill the worker.
The exit codes of the workers are {SIGTERM(-15)}
```

build bentos (on container)
```bash
# project root
$ cd /opt/project

# build the bento
$ bentoml build

$ bentoml list

# output:
 Tag                                        Size        Creation Time        Path
 price_prediction_service:56n5jrtweondqasc  411.61 KiB  2022-12-03 12:05:23  /opt/project/bentoml/bentos/price_prediction_service/ym3pedttakagcasc

# test api server
$ bentoml serve --host price_prediction_service --host 0.0.0.0 --port 3000 --production
```


contanerize
write bentofile  
NOTE: must include pipeline codes (`src/pipeline/*.p`y) since bentoml sklearn uses joblib which stores the entire path of the scripts

```bash
# project root
$ cd streaming-ml-pipeline/

$ export BENTOML_HOME=`pwd`/bentoml/ && bentoml containerize price_prediction_service:latest

# docker
$ docker run --rm -p 12000:3000 price_prediction_service:56n5jrtweondqasc serve --production
```




## Setup streaming-ml pipeline
postgres
The `wal_level=logical` is a configuration needed to Postgres work correctly with Debezium.

debezium base endpoint
- http://0.0.0.0:8083/
- http://0.0.0.0:8083/connector-plugins/
- http://0.0.0.0:8083/connectors/

adminer
- http://0.0.0.0:8080/


run below in kafka or debezium container
```bash
# kafka conatiner
$ docker exec -it kafka /bin/bash

# monitor consumer logs
$ kafka-console-consumer.sh --bootstrap-server kafka:9092 --topic car_database.public.tbl_car_price
```
wait until python-app creating debeizum connections
![title](docs/figures/kafka_consumer_example1.png)


Update `tbl_car_price` table via `SQL command` (left) or directly insert by clicking `New item button` (right)

<img src="docs/figures/adminer_insert_example1.png" width="420"/> <img src="docs/figures/adminer_insert_example2.png" width="420" height=230/> 
<!--![alt-text-1](docs/figures/adminer_insert_example1.png "title-1") ![alt-text-2](docs/figures/kafka_consumer_example2.png "title-2")-->


You can 
![title](docs/figures/adminer_insert_example3.png)

message created on Kafaka which is written in `AVRO`
![title](docs/figures/kafka_consumer_example3.png)


bentoml requests between docker-compose network
how to know (or fix) internal network ip address?
```python
>>> import requests

>>> inputs = {'engineSize': [1.2], 'fuelType': ['Diesel'], 'mileage': [5060], 'model': ['C-MAX'], 'mpg': [45.2], 'tax': [165], 'transmission': ['Manual'], 'year': [2017]}
>>> requests.post("http://172.26.0.3:3000/predict", json=inputs)
>>> requests.post("http://streaming-ml-pipeline_bento_server_1:3000/predict", json=inputs)
```

```bash
$ docker inspect -f '{{.Name}} - {{range $net,$v := .NetworkSettings.Networks}}{{printf "%s" $net}}{{end}} - {{range .NetworkSettings.Networks}}{{.IPAddress}} - {{.NetworkID}}{{end}}' $(docker
ps -aq)
```


```bash
$ docker logs python-app
```

![title](./docs/figures/kafka_source_topic.png)
![title](docs/figures/kafka_sink_topic.png)



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

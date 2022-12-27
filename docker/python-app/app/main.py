import json
import logging

import confluent_kafka as ck
import requests


logging.basicConfig(
    level=logging.DEBUG,
    format="[%(levelname)s] %(message)s (%(filename)s:%(lineno)d)",
)


# kafka settings
SOURCE_TOPICS = ["car_database.public.tbl_car_price"]
SINK_TOPIC = "car_data_predicted"
BOOTSTRAP_SERVER = "kafka:9092"


# fields required to predict the car price
FIELDS = {
    "model": "model",
    "year": "year",
    "transmission": "transmission",
    "mileage": "mileage",
    "fuel_type": "fuelType",
    "tax": "tax",
    "mpg": "mpg",
    "engine_size": "engineSize",
}

# bentoml api enpoint to request the prediction
# API endpoint will be automatically created like below unless you specify the container_name in docker-compose.yml
# - streaming-ml-pipeline: project root directory
# - bento_server: servece name in docker-compose
# BENTO_ENDPOINT = "http://streaming-ml-pipeline_bento_server_1:3000/predict"
BENTO_ENDPOINT = "http://bento-server:3000/predict"


class KafkaBuilder:

    def __init__(self):
        # build consumer and producer instances
        self.__consumer = ck.Consumer(
            {
                "bootstrap.servers": BOOTSTRAP_SERVER,
                "group.id": "teste",
                "auto.offset.reset": "earliest",
            }
        )
        self.__consumer.subscribe(SOURCE_TOPICS)

        self.__producer = ck.Producer(
            {
                "bootstrap.servers": BOOTSTRAP_SERVER,
            }
        )

    @property
    def consumer(self):
        """consumer.
        returns consumer instance
        """
        return self.__consumer

    @property
    def producer(self):
        """producer.
        returns producer instance
        """
        return self.__producer


class RequestHandler:

    def __init__(self):
        pass

    def parse_inputs(self, message_dict: dict):
        input_dict = {
            api_col: [message_dict["payload"][db_col]]
            for db_col, api_col in FIELDS.items()
        }

        return input_dict

    def predict(self, input_dict: dict):
        response = requests.post(BENTO_ENDPOINT, json=input_dict)
        if response.status_code != 200:
            pred_price = None
            logging.error(f"BENTOML API request failed (code: {response.status_code}, message: {response.text})")
        else:
            pred_price = float(json.loads(response.text)[0])

        return pred_price


if __name__ == "__main__":

    builder = KafkaBuilder()
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

        # send the message to the topic with the suggested price
        builder.producer.produce(
            SINK_TOPIC,
            key=key,
            value=json.dumps(message_dict)
        )
        builder.producer.flush(1)

        # log the result
        logging.info(message_dict)

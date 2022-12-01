import time
import requests

CONNECTORS = [
    {
        "name": "source_pg_car_connector",
        "config": {
            "connector.class": "io.debezium.connector.postgresql.PostgresConnector",
            "plugin.name": "pgoutput",

            "database.hostname": "postgres",
            "database.port": "5432",
            "database.user": "postgres",
            "database.password": "postgres",
            "database.dbname": "database",

            "database.server.name": "car_database",
            "table.include.list": "public.tbl_car_price",

            # SMTs
            "transforms": "unwrap",
            # extract the new record state from the record
            "transforms.unwrap.type": "io.debezium.transforms.ExtractNewRecordState",
        }
    },

    {
        "name": "sink_pg_car_connector",
        "config": {
            "topics": "car_data_predicted",

            "connector.class": "io.confluent.connect.jdbc.JdbcSinkConnector",
            "tasks.max": "1",

            "connection.url": "jdbc:postgresql://postgres:5432/database",
            "connection.user": "postgres",
            "connection.password": "postgres",

            "auto.create": "true",
            "insert.mode": "upsert",
            "pk.fields": "id",
            "pk.mode": "record_value",
        }
    }
]

# wait until the debezium server to be ready
time.sleep(50)


# write connectors to the debezium server
for connector in CONNECTORS:
    response = requests.post(
        "http://connect:8083/connectors",
        headers={
            "Content-Type": "application/json"
        },
        json=connector,
    )
    print(f"status: {response.status_code}")
    print(f"text: {response.json()}")
    print("\n")

import pandas as pd
import bentoml
from bentoml.io import JSON


price_prediction_model = bentoml.sklearn.get("ford_used_car_price:latest")
price_prediction_runner = price_prediction_model.to_runner()
svc = bentoml.Service(
    name="price_prediction_service",
    runners=[price_prediction_runner]
)


@svc.api(input=JSON(), output=JSON())
def predict(inputs: JSON):
    inputs = pd.DataFrame(inputs)
    outputs = price_prediction_runner.run(inputs)
    return outputs

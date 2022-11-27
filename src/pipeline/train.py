import numpy as np
import bentoml
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.metrics import mean_squared_error, mean_absolute_error
from xgboost import XGBRegressor

from .data import read_ford_data, split_train_test
from .transform import (
    log_standardize_transformer,
    transmission_transformer,
    fuel_type_transformer,
    model_name_transformer,
    standardize_transformer,
)


def build_model(fuel_types: list, model_name_replace_rules: dict):
    """build_model.

    Parameters
    ----------
    fuel_types : list
        - replace fuelType not belongs to this as "Others"
        - e.g. ["Petrol", "Diesel"]
    model_name_replace_rules : dict
        - replace model for corresponding numeric value
        - models not matched will be converted as 0.0
        - e.g. {"C-MAX": 0.3, "EcoSport": 0.2}
    """
    transformers = ColumnTransformer(
        [
            ("LogStandardize", log_standardize_transformer(), ["mileage", "tax"]),
            ("OneHot", transmission_transformer(), ["transmission"]),
            ("ReplaceOneHot", fuel_type_transformer(fuel_types), ["fuelType"]),
            ("StringToNumeric", model_name_transformer(model_name_replace_rules), ["model"]),
            ("Standardize", standardize_transformer(), ["year", "mpg", "engineSize"]),
        ],
        remainder="drop",
        n_jobs=1,
    )
    regressor = XGBRegressor(
            max_depth=None,
            n_estimators=100,
            random_state=214
    )
    model = Pipeline([
        ("FeatureEngineerring", transformers),
        ("Regressorm", regressor)
    ])

    return model


def mean_absolute_percentile_error(y_true: np.ndarray, y_pred: np.ndarray):
    y_true = np.squeeze(np.array(y_true))
    y_pred = np.squeeze(np.array(y_pred))
    return np.nanmean(np.abs((y_true - y_pred) / y_true))


def main():
    # read train/test data
    data = read_ford_data()
    train_data, test_data = split_train_test(data, test_size=0.2, seed=1234)

    # build model
    fuel_types = ["Petrol", "Diesel"]
    model_name_replace_rules = (train_data.model.value_counts() / len(train_data)).to_dict()
    model = build_model(
        fuel_types=fuel_types,
        model_name_replace_rules=model_name_replace_rules
    )

    # fit car price prediction model
    X_train = train_data.drop("price", axis=1)
    y_train = train_data.price
    X_test = test_data.drop("price", axis=1)
    y_test = test_data.price
    model.fit(X=X_train, y=y_train)

    # result metrics
    pred_train = np.clip(model.predict(X_train), a_min=0.0, a_max=np.infty)
    pred_test = np.clip(model.predict(X_test), a_min=0.0, a_max=np.infty)

    print(f"Train RMSE (Euro): {mean_squared_error(y_train, pred_train)**(1/2.):0.2f}")
    print(f"Train MAE (Euro): {mean_absolute_error(y_train, pred_train):0.2f}")
    print(f"Train MAPE (%): {mean_absolute_percentile_error(y_train, pred_train)*100:0.2f}")

    print(f"Test RMSE (Euro): {mean_squared_error(y_test, pred_test)**(1/2.):0.2f}")
    print(f"Test MAE (Euro): {mean_absolute_error(y_test, pred_test):0.2f}")
    print(f"Test MAPE (%): {mean_absolute_percentile_error(y_test, pred_test)*100:0.2f}")

    # save bentoml model
    # NOTE: you must set n_jobs=1 in ColumnTransformer
    # or manually update model.steps[0][1].n_jobs = 1 before pass the trained model to save_model
    # otherwise, bento.Service may raise SIGTERM error because of segmentation fault / excessive memory usage
    bentoml.sklearn.save_model(name="ford_used_car_price", model=model)


if __name__ == "__main__":
    main()

import numpy as np
import pandas as pd

from sklearn.preprocessing import (
    FunctionTransformer,
    StandardScaler,
    OneHotEncoder,
)
from sklearn.pipeline import Pipeline


def log_standardize_transformer():
    """log_standardize_transformer.

    Input: mileage, tax
    Transform: log(1+x) => StandardScaler
    """
    return Pipeline([
        ("Log1P", FunctionTransformer(np.log1p)),
        ("Scaler", StandardScaler())
    ])


def transmission_transformer():
    """transmission_transformer.

    Input: transmission
    Transform: OneHotEncoder
    - handle_unknown = 'ignore' (encode data never has been observed to zeros)
    """
    return OneHotEncoder(handle_unknown="ignore", sparse=False)


def _replace_minor_fuel_type(x: np.ndarray or pd.DataFrame, **kwargs):
    """_replace_minor_fuel_type.
    Replace classes not belongs to the major_types with "Others"
    - kwargs must contain "major_types" list

    Parameters
    ----------
    x : np.ndarray or pd.DataFrame
        - shape: (N, 1)
    """
    major_types = kwargs["major_types"]
    x = pd.DataFrame(x, columns=["fuelType"]).copy()
    x[~x.fuelType.isin(major_types)] = "Others"
    return x.values


def fuel_type_transformer(major_types: list = ["Petrol", "Diesel"]):
    """fuel_type_transformer.

    Input: fuelType
    Transform: ReplaceMinorClass => OneHotEncoder
    - ReplaceMinorClass: replace minor classes with "Others"
    """

    return Pipeline([
        (
            "Replacer",
            FunctionTransformer(
                _replace_minor_fuel_type,
                kw_args={"major_types": ["Petrol", "Diesel"]},
            )
        ),
        ("OneHotEncoder", OneHotEncoder(handle_unknown="ignore", sparse=False))
    ])


def _convert_model_to_numeric(x: np.ndarray or pd.DataFrame, **kwargs):
    """_convert_model_to_numeric.
    Convert string model values to it's corresponding frequencies
    - kwargs must contain "model_replace_rules" dictionary-typed rules

    Parameters
    ----------
    x : np.ndarray or pd.DataFrame
        - shape: (N, 1)
    """
    model_replace_rules = kwargs["model_replace_rules"]
    x = pd.DataFrame(x, columns=["model"]).copy()
    x[~x.model.isin(model_replace_rules.keys())] = 0.0
    for k, v in model_replace_rules.items():
        x[x == k] = v
    return x.values.astype("float")


def model_name_transformer(model_replace_rules: dict):
    """model_name_transformer.

    Input: model
    Transform: NumericConverter
    - NumericConverter: convert model to its corresponding frequencies in train data
    """
    return FunctionTransformer(
        _convert_model_to_numeric,
        kw_args={"model_replace_rules": model_replace_rules},
    )


def standardize_transformer():
    """standardize_transformer.

    Input: year, mpg, engineSize
    Transform: StandardScaler()
    """
    return StandardScaler()

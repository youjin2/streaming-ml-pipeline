import os

import pandas as pd
from sklearn.model_selection import train_test_split


def read_ford_data():
    """read_ford_data.
    read ford used car price dataset
    """
    cur_dir = __file__
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(cur_dir)))
    data_path = os.path.join(
        base_dir,
        "data",
        "ford.csv",
    )
    data = pd.read_csv(data_path)
    # there are cases model column containing whitespace
    data["model"] = data.model.str.strip(" ")

    return data


def split_train_test(data: pd.DataFrame,
                     test_size: float = 0.2,
                     seed: int = 1234):
    """split_train_test.
    split data into train/test
    """
    train_data, test_data = train_test_split(data, test_size=test_size, random_state=seed)
    train_data = train_data.reset_index(drop=True)
    test_data = test_data.reset_index(drop=True)

    return train_data, test_data


if __name__ == "__main__":
    data = read_ford_data()
    train_data, test_data = split_train_test(data)

    print(data.head())
    print(train_data.shape)
    print(test_data.shape)

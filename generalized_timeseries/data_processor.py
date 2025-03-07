#!/usr/bin/env python3
# data_processor.py

# handle relative directory imports for chronicler
import logging as l

# handle data transformation and preparation tasks
import pandas as pd
import numpy as np
from statsmodels.tsa.stattools import adfuller
from tabulate import tabulate  # pretty print dfs
from typing import Callable, Dict, Tuple


class MissingDataHandler:
    """Handles missing data through various strategies such as dropping or forward filling."""

    def __init__(self) -> None:
        """
        Initializes the MissingDataHandler class.
        Logs an ASCII banner for initialization.
        """
        ascii_banner = """
        \n
        \t> MissingDataHandler <\n"""
        l.info(ascii_banner)

    def drop_na(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Drops rows with missing values from the given DataFrame.

        Args:
            data (pd.DataFrame): The DataFrame from which to drop rows with missing values.

        Returns:
            pd.DataFrame: A DataFrame with rows containing missing values removed.
        """
        l.info("Dropping rows with missing values")
        l.info("df filled:")
        l.info("\n" + tabulate(data.head(5), headers="keys", tablefmt="fancy_grid"))
        return data.dropna()

    def forward_fill(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Fills missing values in the DataFrame using the forward fill method.

        Args:
            data (pd.DataFrame): The DataFrame containing missing values to be filled.

        Returns:
            pd.DataFrame: The DataFrame with missing values filled using forward fill.
        """
        l.info("Filling missing values with forward fill")
        l.info("df filled:")
        l.info("\n" + tabulate(data.head(5), headers="keys", tablefmt="fancy_grid"))
        return data.fillna(method="ffill")


class MissingDataHandlerFactory:
    """Factory for creating missing data handlers based on a specified strategy."""

    @staticmethod
    def create_handler(strategy: str) -> Callable[[pd.DataFrame], pd.DataFrame]:
        """
        Creates a handler function based on the specified strategy.

        Args:
            strategy (str): The strategy to handle missing data. Options are "drop" or "forward_fill".

        Returns:
            Callable[[pd.DataFrame], pd.DataFrame]: A function that handles missing data accordingly.

        Raises:
            ValueError: If an unknown strategy is provided.
        """
        handler = MissingDataHandler()
        l.info(f"Creating handler for strategy: {strategy}")
        if strategy.lower() == "drop":
            return handler.drop_na
        elif strategy.lower() == "forward_fill":
            return handler.forward_fill
        else:
            raise ValueError(f"Unknown missing data strategy: {strategy}")


def fill_data(df: pd.DataFrame, config) -> pd.DataFrame:
    """
    Fills missing data in the given DataFrame according to the specified configuration.

    Args:
        df (pd.DataFrame): The DataFrame containing the data to be processed.
        config: Configuration object containing the strategy for handling missing values.

    Returns:
        pd.DataFrame: The DataFrame with missing values handled according to the specified strategy.
    """
    if not config.data_processor.handle_missing_values.enabled:
        l.info("Skipping missing data handling as it is disabled in config.")
        return df  # Return original data without modification

    l.info("\n# Processing: handling missing values")
    handler_missing = MissingDataHandlerFactory.create_handler(
        strategy=config.data_processor.handle_missing_values.strategy
    )
    df_filled = handler_missing(df)
    return df_filled


from tabulate import tabulate
from typing import Callable


class DataScaler:
    """
    Provides methods to scale numeric data in a pandas DataFrame.

    Methods:
        scale_data_standardize(data: pd.DataFrame) -> pd.DataFrame:
            Standardizes all numeric columns except the index by subtracting the mean and dividing by the standard deviation.

        scale_data_minmax(data: pd.DataFrame) -> pd.DataFrame:
            Scales all numeric columns using MinMaxScaler by dividing each value by the range (max - min) of the column.
    """

    def scale_data_standardize(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Standardizes all numeric columns in the given DataFrame except the index.

        Args:
            data (pd.DataFrame): The input DataFrame containing numeric columns to be standardized.

        Returns:
            pd.DataFrame: The DataFrame with standardized numeric columns.

        Notes:
            - The standardization is performed by subtracting the mean and dividing by the standard deviation for each numeric column.
            - The index of the DataFrame is not modified.
            - Logs the process of scaling and displays the first 5 rows of the scaled DataFrame.
        """
        numeric_columns = data.select_dtypes(include=[np.number]).columns
        for column in numeric_columns:
            data[column] = (data[column] - data[column].mean()) / data[column].std()
        l.info("Scaling data using standardization")
        l.info("df scaled:")
        l.info("\n" + tabulate(data.head(5), headers="keys", tablefmt="fancy_grid"))
        return data

    def scale_data_minmax(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Scales the numeric columns of the given DataFrame using Min-Max scaling.

        Args:
            data (pd.DataFrame): The input DataFrame containing the data to be scaled.

        Returns:
            pd.DataFrame: The DataFrame with scaled numeric columns.

        Notes:
            - This function scales each numeric column to a range between 0 and 1.
            - Non-numeric columns are not affected by this scaling.
            - The function logs the scaling process and the first 5 rows of the scaled DataFrame.
        """
        numeric_columns = data.select_dtypes(include=[np.number]).columns
        for column in numeric_columns:
            data[column] = (data[column] - data[column].min()) / (
                data[column].max() - data[column].min()
            )
        l.info("Scaling data using minmax")
        l.info("df scaled:")
        l.info("\n" + tabulate(data.head(5), headers="keys", tablefmt="fancy_grid"))
        return data


class DataScalerFactory:
    """
    Factory class for creating data scaling handlers based on the specified strategy.

    Methods:
        create_handler(strategy: str) -> Callable[[pd.DataFrame], pd.DataFrame]:
            Returns the appropriate scaling function based on the provided strategy.
    """

    @staticmethod
    def create_handler(strategy: str) -> Callable[[pd.DataFrame], pd.DataFrame]:
        """
        Returns the appropriate scaling function based on the provided strategy.

        Args:
            strategy (str): The scaling strategy to use. Supported values are "standardize" and "minmax".

        Returns:
            Callable[[pd.DataFrame], pd.DataFrame]: The scaling function corresponding to the specified strategy.

        Raises:
            ValueError: If the provided strategy is not recognized.
        """
        scaler = DataScaler()
        l.info(f"Creating scaler for strategy: {strategy}")
        if strategy.lower() == "standardize":
            return scaler.scale_data_standardize
        elif (
            strategy.lower() == "minmax"
        ):  # TODO: fixme. This turns everything into a constant
            return scaler.scale_data_minmax
        else:
            raise ValueError(f"Unknown data scaling strategy: {strategy}")


def scale_data(df: pd.DataFrame, config) -> pd.DataFrame:
    """
    Scales the input DataFrame according to the specified configuration.

    Args:
        df (pd.DataFrame): The input data to be scaled.
        config: Configuration object containing scaling method details.

    Returns:
        pd.DataFrame: The scaled DataFrame.
    """
    l.info("\n# Processing: scaling data")
    handler_scaler = DataScalerFactory.create_handler(
        strategy=config.data_processor.scaling.method
    )
    df_scaled = handler_scaler(df)
    return df_scaled


class StationaryReturnsProcessor:
    """
    A class to process and test the stationarity of time series data.

    Methods:
        make_stationary(data: pd.DataFrame, method: str) -> pd.DataFrame:
            Apply the chosen method to make the data stationary.

        test_stationarity(data: pd.DataFrame, test: str) -> Dict[str, Dict[str, float]]:
            Perform the Augmented Dickey-Fuller test to check for stationarity.

        log_adf_results(data: Dict[str, Dict[str, float]], p_value_threshold: float) -> None:
            Log the interpreted results of the ADF test.
    """

    def make_stationary(self, data: pd.DataFrame, method: str, config) -> pd.DataFrame:
        """
        Apply the chosen method to make the data stationary.

        Args:
            data (pd.DataFrame): The input data to be made stationary.
            method (str): The method to use for making the data stationary. Currently supported method is "difference".
            config (Any): Configuration object containing parameters for making the data stationary.

        Returns:
            pd.DataFrame: The transformed data with the applied stationarity method.

        Raises:
            ValueError: If an unknown method is provided.
        """
        if not config.data_processor.make_stationary.enabled:
            l.info("Skipping stationarity transformation as it is disabled in config.")
            return data

        l.info(f"Applying stationarity method: {method}")
        numeric_columns = data.select_dtypes(include=[np.number]).columns

        if method.lower() == "difference":
            for column in numeric_columns:
                data[f"{column}_diff"] = data[column].diff()
            data = data.dropna()
        else:
            raise ValueError(f"Unknown make_stationary method: {method}")

        l.info("\n" + tabulate(data.head(5), headers="keys", tablefmt="fancy_grid"))
        return data

    def test_stationarity(
        self, data: pd.DataFrame, test: str
    ) -> Dict[str, Dict[str, float]]:
        """
        Perform the Augmented Dickey-Fuller (ADF) test for stationarity on the given data.

        The null hypothesis (H0) is that the series is non-stationary (has a unit root).
        The alternative hypothesis (H1) is that the series is stationary.

        Args:
            data (pd.DataFrame): The input data containing time series to be tested.
            test (str): The type of stationarity test to perform. Currently, only "adf" is supported.

        Returns:
            Dict[str, Dict[str, float]]: A dictionary where keys are column names and values are dictionaries containing
                the ADF Statistic and p-value for each numeric column in the input data.

        Raises:
            ValueError: If an unsupported stationarity test is specified.
        """
        if test.lower() != "adf":
            raise ValueError(f"Unsupported stationarity test: {test}")
        else:
            l.info(f"Test_stationarity: {test} test for stationarity")
            results = {}
            numeric_columns = data.select_dtypes(include=[np.number]).columns
            for column in numeric_columns:
                if data[column].isnull().any() or not np.isfinite(data[column]).all():
                    l.warning(
                        f"Column {column} contains NaN or Inf values. Skipping ADF test."
                    )
                    continue
                result = adfuller(data[column])
                results[column] = {"ADF Statistic": result[0], "p-value": result[1]}
            l.info(f"Results: {results}")
        return results

    def log_adf_results(
        self, data: Dict[str, Dict[str, float]], p_value_threshold: float
    ) -> None:
        """
        Logs interpreted Augmented Dickey-Fuller (ADF) test results.

        Args:
            data (Dict[str, Dict[str, float]]): A dictionary where keys are series names and values are dictionaries containing ADF test results.
                Each value dictionary should have the keys "ADF Statistic" and "p-value".
            p_value_threshold (float): The threshold for the p-value to determine if the series is stationary.

        Returns:
            None
        """
        for series_name, result in data.items():
            adf_stat = result["ADF Statistic"]
            p_value = result["p-value"]
            if p_value < p_value_threshold:
                interpretation = f"p_value {p_value:.2e} < p_value_threshold {p_value_threshold}. Data is stationary (reject null hypothesis)."
            else:
                interpretation = f"p_value {p_value:.2e} >= p_value_threshold {p_value_threshold}. Data is non-stationary (fail to reject null hypothesis)."

            l.info(
                f"series_name: {series_name}\n"
                f"   adf_stat: {adf_stat:.2f}\n"
                f"   p_value: {p_value:.2e}\n"
                f"   interpretation: {interpretation}\n"
            )


class StationaryReturnsProcessorFactory:
    """
    Factory class for creating handlers for stationary returns processing strategies.

    Methods:
        create_handler(strategy: str) -> Callable:
            Returns the appropriate processing function based on the provided strategy.
    """

    @staticmethod
    def create_handler(strategy: str) -> Callable:
        """
        Returns the appropriate processing function based on the provided strategy.

        Args:
            strategy (str): The name of the strategy for which the processing function is to be created.
                Supported strategies are:
                - "transform_to_stationary_returns"
                - "test_stationarity"
                - "log_stationarity"

        Returns:
            Callable: The appropriate processing function.

        Raises:
            ValueError: If an unknown strategy is provided.
        """
        stationary_returns_processor = StationaryReturnsProcessor()
        l.info(f"Creating processor for strategy: {strategy}")
        if strategy.lower() == "transform_to_stationary_returns":
            return stationary_returns_processor
        elif strategy.lower() == "test_stationarity":
            return stationary_returns_processor
        elif strategy.lower() == "log_stationarity":
            return stationary_returns_processor
        else:
            raise ValueError(
                f"Unknown stationary returns processing strategy: {strategy}"
            )


def stationarize_data(df: pd.DataFrame, config) -> pd.DataFrame:
    """
    Processes the given DataFrame to make the data stationary.

    Args:
        df (pd.DataFrame): The input data to be made stationary.
        config: Configuration object containing the method to be used for making the data stationary.

    Returns:
        pd.DataFrame: The stationary version of the input data.
    """
    l.info("\n# Processing: making data stationary")
    stationary_returns_processor = StationaryReturnsProcessor()
    df_stationary = stationary_returns_processor.make_stationary(
        data=df, method=config.data_processor.make_stationary.method, config=config
    )
    return df_stationary


def test_stationarity(df: pd.DataFrame, config) -> Dict[str, Dict[str, float]]:
    """
    Tests the stationarity of a given DataFrame using the specified configuration.

    Args:
        df (pd.DataFrame): The DataFrame containing the data to be tested for stationarity.
        config: Configuration object containing the method to be used for testing stationarity.

    Returns:
        Dict[str, Dict[str, float]]: Results of the stationarity test.
    """
    l.info("\n# Testing: stationarity")
    stationary_returns_processor = StationaryReturnsProcessorFactory.create_handler(
        "test_stationarity"
    )
    adf_results = stationary_returns_processor.test_stationarity(
        data=df, test=config.data_processor.test_stationarity.method
    )
    return adf_results


def log_stationarity(df: pd.DataFrame, config) -> None:
    """
    Logs the stationarity of the given DataFrame using the Augmented Dickey-Fuller (ADF) test.

    Args:
        df (pd.DataFrame): The DataFrame containing the data to be tested for stationarity.
        config: Configuration object containing the parameters for the stationarity test.
            - config.data_processor.test_stationarity.p_value_threshold (float): The p-value threshold for the ADF test.

    Returns:
        None
    """
    l.info("\n# Logging: stationarity")
    stationary_returns_processor = StationaryReturnsProcessorFactory.create_handler(
        "log_stationarity"
    )
    stationary_returns_processor.log_adf_results(
        data=df,
        p_value_threshold=config.data_processor.test_stationarity.p_value_threshold,
    )

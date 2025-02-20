#!/usr/bin/env python3

# run_pipeline.py

# handle relative directory imports for chronicler
import logging as l
from chronicler_loader import init_chronicler
chronicler = init_chronicler()

from config_loader import load_config
from data_generator import PriceSeriesGenerator
from data_processor import MissingDataHandlerFactory
from data_processor import DataScalerFactory
from data_processor import StationaryReturnsProcessor

l.info("Loading configuration")
config = load_config("config.dev.yml")

l.info("Configuring: data_generator")
config_data_generator = config["data_generator"]
data_generator_start_date = config_data_generator.get("start_date", "2023-01-01")
data_generator_end_date = config_data_generator.get("end_date", "2023-12-31")
data_generator_ticker_initial_prices = config_data_generator.get("ticker_initial_prices", {"AAPL": 100.0})

l.info("Configuring: data_processor")
config_data_processor = config["data_processor"]
data_processor_missing_data_strategy = config_data_processor.get("missing_data_handler", {}).get("strategy", "drop")
data_processor_scaling_strategy = config_data_processor.get("scaler", {}).get("method", "standardize")
data_processor_stationarity_method = config_data_processor.get("make_stationarity", {}).get("method", "difference")
data_processor_p_value_threshold = config_data_processor.get("stationarity_test", {}).get("p_value_threshold", 0.05)

generator = PriceSeriesGenerator(start_date=data_generator_start_date, end_date=data_generator_end_date)
price_dict, price_df = generator.generate_prices(
    ticker_initial_prices=data_generator_ticker_initial_prices
)

handler_missing = MissingDataHandlerFactory.create_handler(data_processor_missing_data_strategy)
filled_df = handler_missing(price_df)

handler_scaler = DataScalerFactory.create_handler("standardize")
scaled_df = handler_scaler(filled_df)
stationary_returns_processor = StationaryReturnsProcessor()
diffed_df = stationary_returns_processor.make_stationary(scaled_df)
adf_results = stationary_returns_processor.check_stationarity(diffed_df)
stationary_returns_processor.log_adf_results(adf_results, data_processor_p_value_threshold)

# GARCH models, like ARMA models, predict volatility rather than values. 
# Volatility = changes in variance over time, making it a function of time. 
# GARCH handles uneven variance (heteroskedasticity).
# GARCH models assume stationarity, similar to ARMA models, and include both AR and MA components.
# Since volatility often clusters, GARCH is designed to capture and leverage this behavior.

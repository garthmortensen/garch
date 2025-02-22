#!/usr/bin/env python3

# run_pipeline.py

# handle relative directory imports for chronicler
import logging as l
from chronicler_loader import init_chronicler
chronicler = init_chronicler()

from configurator import load_configuration
from data_generator import PriceSeriesGenerator
from data_processor import MissingDataHandlerFactory
from data_processor import DataScalerFactory
from data_processor import StationaryReturnsProcessor
from stats_model import ModelFactory

try:
    config_file = "config.yml"
    config = load_configuration(config_file)

    l.info("\n# Generating: price series data")
    generator = PriceSeriesGenerator(
        start_date=config.data_generator.start_date,
        end_date=config.data_generator.end_date
        )
    price_dict, price_df = generator.generate_prices(
        ticker_initial_prices=config.data_generator.ticker_initial_prices
    )

    l.info("\n# Processing: handling missing data")
    handler_missing = MissingDataHandlerFactory.create_handler(
        strategy=config.data_processor.missing_data_handler.strategy
    )
    filled_df = handler_missing(price_df)

    l.info("\n# Processing: scaling data")
    handler_scaler = DataScalerFactory.create_handler(
        strategy=config.data_processor.scaler.method
        )
    scaled_df = handler_scaler(filled_df)

    stationary_returns_processor = StationaryReturnsProcessor()
    l.info("\n# Processing: making data stationary")
    diffed_df = stationary_returns_processor.make_stationary(
        data=scaled_df,
        method=config.data_processor.make_stationarity.method
        )

    l.info("\n# Testing: stationarity")
    adf_results = stationary_returns_processor.check_stationarity(
        data=diffed_df,
        test=config.data_processor.test_stationarity.method
        )
    stationary_returns_processor.log_adf_results(
        data=adf_results,
        p_value_threshold=config.data_processor.test_stationarity.p_value_threshold
        )

    l.info("\n# Modeling")

    if config.stats_model.ARIMA.run:
        l.info("\n## Running ARIMA")
        model_arima = ModelFactory.create_model(
            model_type="ARIMA", 
            data=diffed_df, 
            order=(
                config.stats_model.ARIMA.parameters_fit.get("p",),
                config.stats_model.ARIMA.parameters_fit.get("d"),
                config.stats_model.ARIMA.parameters_fit.get("q")
                ),
            steps=config.stats_model.ARIMA.parameters_predict_steps
            )
        arima_fit = model_arima.fit()
        l.info("\n## ARIMA summary")
        l.info(model_arima.summary())
        l.info("\n## ARIMA forecast")
        arima_forecast = model_arima.forecast()  # dont include steps arg here bc its already in object initialization
        l.info(f"arima_forecast: {arima_forecast}")

    if config.stats_model.GARCH.run:
        l.info("\n## Running GARCH")
        model_garch = ModelFactory.create_model(
            model_type="GARCH", 
            data=diffed_df,
            order=(
                config.stats_model.GARCH.parameters_fit.p,
                config.stats_model.GARCH.parameters_fit.q,
                config.stats_model.GARCH.parameters_fit.dist
                )
            )


    # GARCH models, like ARMA models, predict volatility rather than values. 
    # Volatility = changes in variance over time, making it a function of time. 
    # GARCH handles uneven variance (heteroskedasticity).
    # GARCH models assume stationarity, similar to ARMA models, and include both AR and MA components.
    # Since volatility often clusters, GARCH is designed to capture and leverage this behavior.

except Exception as e:
    l.exception(f"\nError in pipeline:\n{e}")
    raise

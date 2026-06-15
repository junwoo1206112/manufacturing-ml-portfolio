import logging
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.logging_config import get_logger, setup_logging


class TestLoggingConfig:
    def test_setup_logging_configures_root_logger(self):
        setup_logging(level=logging.DEBUG)
        root = logging.getLogger()
        assert root.level == logging.DEBUG
        assert any(isinstance(h, logging.StreamHandler) for h in root.handlers)

    def test_setup_logging_with_file_handler(self, tmp_path):
        log_path = tmp_path / "test.log"
        setup_logging(level=logging.INFO, log_file=str(log_path))

        logger = get_logger(__name__)
        logger.info("test log message")

        for handler in logging.getLogger().handlers:
            handler.flush()

        assert log_path.exists()
        content = log_path.read_text(encoding="utf-8")
        assert "test log message" in content

        logging.shutdown()

    def test_get_logger_returns_named_logger(self):
        logger = get_logger("src.quality_predictor")
        assert logger.name == "src.quality_predictor"

    def test_module_loggers_use_root_handlers(self, caplog):
        setup_logging(level=logging.INFO)
        root = logging.getLogger()
        root.addHandler(caplog.handler)

        logger = get_logger("test_caplog")
        with caplog.at_level(logging.INFO, logger="test_caplog"):
            logger.info("captured message")
        assert "captured message" in caplog.text

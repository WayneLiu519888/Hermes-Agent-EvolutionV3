"""Tests for logging_config.py — unified logging setup."""
import logging
import unittest
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from evolution.logging_config import (
    setup_logging, get_logger, shutdown_logging,
    log_tool_call, log_cycle_step, log_db_query,
    LOGGER_HIERARCHY, LOG_FORMAT, LOG_DATE_FORMAT,
)


class TestGetLogger(unittest.TestCase):

    def test_src_evolution_transforms(self):
        log = get_logger("src.evolution.tools.registry")
        self.assertEqual(log.name, "hermes_evo.tools.registry")

    def test_src_services_transforms(self):
        log = get_logger("src.services.core.events")
        self.assertEqual(log.name, "hermes_evo.services.core.events")

    def test_src_utils_transforms(self):
        log = get_logger("src.utils.feishu_notifier")
        self.assertEqual(log.name, "hermes_evo.utils")

    def test_hermes_plugin_transforms(self):
        log = get_logger("hermes_plugin")
        self.assertEqual(log.name, "hermes_evo.plugin")

    def test_unknown_prefix_adds_hermes_evo(self):
        log = get_logger("my_custom_module")
        self.assertEqual(log.name, "hermes_evo.my_custom_module")

    def test_already_hermes_evo_unchanged(self):
        log = get_logger("hermes_evo.tools")
        self.assertEqual(log.name, "hermes_evo.tools")


class TestSetupLogging(unittest.TestCase):

    def setUp(self):
        # Reset global state
        import evolution.logging_config as lc
        lc._logging_initialized = False
        root = logging.getLogger("hermes_evo")
        root.handlers.clear()
        root.setLevel(logging.NOTSET)

    def tearDown(self):
        shutdown_logging()

    def test_setup_console_only(self):
        setup_logging(level="DEBUG", console=True)
        root = logging.getLogger("hermes_evo")
        self.assertGreater(len(root.handlers), 0, "Should have at least one handler")

    def test_setup_with_file(self):
        import tempfile, os
        with tempfile.NamedTemporaryFile(suffix=".log", delete=False) as f:
            log_path = f.name
        try:
            setup_logging(level="INFO", log_file=log_path, console=False)
            self.assertTrue(os.path.exists(log_path))
            self.assertGreater(os.path.getsize(log_path), 0)
        finally:
            os.unlink(log_path)

    def test_idempotent_setup(self):
        setup_logging(level="INFO")
        initial_handlers = len(logging.getLogger("hermes_evo").handlers)
        setup_logging(level="DEBUG")  # second call
        # handler count should not increase
        self.assertEqual(len(logging.getLogger("hermes_evo").handlers), initial_handlers)

    def test_hierarchy_levels_set(self):
        setup_logging(level="INFO")
        for name, expected_level in LOGGER_HIERARCHY.items():
            log = logging.getLogger(name)
            self.assertEqual(log.level, expected_level,
                             f"Logger '{name}' should be level {expected_level}")

    def test_shutdown_clears_handlers(self):
        setup_logging(level="INFO")
        self.assertGreater(len(logging.getLogger("hermes_evo").handlers), 0)
        shutdown_logging()
        self.assertEqual(len(logging.getLogger("hermes_evo").handlers), 0)


class TestConvenienceFunctions(unittest.TestCase):

    def setUp(self):
        import evolution.logging_config as lc
        lc._logging_initialized = False
        logging.getLogger("hermes_evo").handlers.clear()

    def test_log_tool_call(self):
        log = get_logger("hermes_evo.tools")
        log.setLevel(logging.INFO)
        stream = StringIO()
        handler = logging.StreamHandler(stream)
        log.addHandler(handler)
        log_tool_call(log, "test_tool", {"x": 1}, "ok")
        output = stream.getvalue()
        self.assertIn("test_tool", output)

    def test_log_cycle_step(self):
        log = get_logger("hermes_evo.closed_loop")
        log.setLevel(logging.INFO)
        stream = StringIO()
        handler = logging.StreamHandler(stream)
        log.addHandler(handler)
        log_cycle_step(log, 1, "monitor", "collecting metrics")
        output = stream.getvalue()
        self.assertIn("1", output)
        self.assertIn("monitor", output)

    def test_log_db_query(self):
        log = get_logger("hermes_evo.memory")
        log.setLevel(logging.DEBUG)
        stream = StringIO()
        handler = logging.StreamHandler(stream)
        log.addHandler(handler)
        log_db_query(log, "test.db", "SELECT * FROM x", 12.5)
        output = stream.getvalue()
        self.assertIn("test.db", output)
        self.assertIn("12.5", output)


class TestLogFormat(unittest.TestCase):

    def test_format_contains_expected_fields(self):
        self.assertIn("asctime", LOG_FORMAT)
        self.assertIn("levelname", LOG_FORMAT)
        self.assertIn("name", LOG_FORMAT)
        self.assertIn("message", LOG_FORMAT)


if __name__ == "__main__":
    unittest.main()

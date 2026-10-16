"""With SGLANG_REDACT_REQUEST_DATA set, /configure_logging refuses changes that
would log or dump request data and passes other changes through. Pure CPU."""

import asyncio
import unittest
from http import HTTPStatus
from types import SimpleNamespace
from unittest import mock

from sglang.srt.entrypoints import http_server
from sglang.srt.environ import envs
from sglang.srt.managers.io_struct import ConfigureLoggingReq
from sglang.test.ci.ci_register import register_cpu_ci
from sglang.test.test_utils import CustomTestCase

register_cpu_ci(est_time=5, suite="base-a-test-cpu")


def _call(obj):
    tokenizer_manager = mock.MagicMock()
    with mock.patch.object(
        http_server,
        "_global_state",
        SimpleNamespace(tokenizer_manager=tokenizer_manager),
    ):
        response = asyncio.run(http_server.configure_logging(obj, request=None))
    return response, tokenizer_manager


class TestConfigureLoggingRedaction(CustomTestCase):
    def test_request_data_changes_are_refused(self):
        for obj, field in (
            (ConfigureLoggingReq(log_requests=True), "log_requests"),
            (
                ConfigureLoggingReq(dump_requests_folder="/tmp/d"),
                "dump_requests_folder",
            ),
            (ConfigureLoggingReq(crash_dump_folder="/tmp/c"), "crash_dump_folder"),
            (ConfigureLoggingReq(log_level="DEBUG"), "log_level=debug"),
        ):
            with self.subTest(field=field):
                with envs.SGLANG_REDACT_REQUEST_DATA.override(True):
                    response, tokenizer_manager = _call(obj)
                self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)
                self.assertIn(field, response.body.decode())
                tokenizer_manager.configure_logging.assert_not_called()

    def test_other_changes_pass_through(self):
        obj = ConfigureLoggingReq(
            log_requests=False, log_requests_level=3, dump_requests_folder=""
        )
        with envs.SGLANG_REDACT_REQUEST_DATA.override(True):
            response, tokenizer_manager = _call(obj)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        tokenizer_manager.configure_logging.assert_called_once_with(obj)

    def test_request_data_changes_pass_through_without_the_flag(self):
        obj = ConfigureLoggingReq(log_requests=True)
        response, tokenizer_manager = _call(obj)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        tokenizer_manager.configure_logging.assert_called_once_with(obj)


if __name__ == "__main__":
    unittest.main()

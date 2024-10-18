import enum
import json
import logging
import logging.handlers
import pathlib
import sys
import tempfile
import unittest.mock

import json_log_formatter  # type: ignore
import pytest

from pantos.common.blockchains.enums import Blockchain
from pantos.common.logging import _HUMAN_READABLE_LOG_FORMAT
from pantos.common.logging import LogFile
from pantos.common.logging import LogFormat
from pantos.common.logging import _DataDogJSONFormatter
from pantos.common.logging import _HumanReadableFormatter
from pantos.common.logging import initialize_logger

_LOG_MESSAGE = 'test message'
_LOG_EXTRA_KEY_1 = 'first test key'
_LOG_EXTRA_VALUE_1 = 'extra test message'
_LOG_EXTRA_KEY_2 = 'second test key'
_LOG_EXTRA_VALUE_2 = [1, 2, 3]
_LOG_EXTRA_KEY_3 = 'blockchain'
_LOG_EXTRA_VALUE_3 = Blockchain.AVALANCHE
_LOG_ERROR_MESSAGE = 'error message'
_LOG_FILE_NAME = 'test.log'


class _LogFileTest(enum.Enum):
    NO_LOG_FILE = 1
    LOG_FILE_EXISTING = 2
    LOG_DIRECTORY_EXISTING = 3
    LOG_DIRECTORY_NOT_EXISTING = 4


@pytest.fixture
def human_readable_formatter():
    return _HumanReadableFormatter()


@pytest.fixture
def datadog_custom_formatter():
    return _DataDogJSONFormatter()


@pytest.fixture
def root_logger():
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    return root_logger


def test_human_readable_formatter_format_correct(root_logger,
                                                 human_readable_formatter):
    log_record = root_logger.makeRecord(
        '', logging.ERROR, '', 0, _LOG_MESSAGE, (), None, extra={
            _LOG_EXTRA_KEY_1: _LOG_EXTRA_VALUE_1,
            _LOG_EXTRA_KEY_2: _LOG_EXTRA_VALUE_2
        })
    formatted_log = human_readable_formatter.format(log_record)
    assert _LOG_MESSAGE in formatted_log
    assert _LOG_EXTRA_KEY_1 in formatted_log
    assert _LOG_EXTRA_VALUE_1 in formatted_log
    assert _LOG_EXTRA_KEY_2 in formatted_log
    assert str(_LOG_EXTRA_VALUE_2) in formatted_log


def test_datadog_custom_formatter_format_correct(root_logger,
                                                 datadog_custom_formatter):
    log_record = root_logger.makeRecord(
        '', logging.ERROR, '', 0, _LOG_MESSAGE, (), None, extra={
            _LOG_EXTRA_KEY_1: _LOG_EXTRA_VALUE_1,
            _LOG_EXTRA_KEY_2: _LOG_EXTRA_VALUE_2,
            _LOG_EXTRA_KEY_3: _LOG_EXTRA_VALUE_3,
        })
    formatted_log = datadog_custom_formatter.format(log_record)
    json_formatted_log = json.loads(formatted_log)
    assert isinstance(json_formatted_log, dict)
    assert json_formatted_log[_LOG_EXTRA_KEY_1] == _LOG_EXTRA_VALUE_1
    assert json_formatted_log[_LOG_EXTRA_KEY_2] == _LOG_EXTRA_VALUE_2
    assert json_formatted_log[
        _LOG_EXTRA_KEY_3] == _LOG_EXTRA_VALUE_3.name.capitalize()


def test_datadog_custom_formatter_format_error_correct(
        root_logger, datadog_custom_formatter):
    try:
        raise ValueError(_LOG_ERROR_MESSAGE)
    except Exception:
        exc_info = sys.exc_info()
    log_record = root_logger.makeRecord(
        '', logging.ERROR, '', 0, _LOG_MESSAGE, (), exc_info, extra={
            _LOG_EXTRA_KEY_1: _LOG_EXTRA_VALUE_1,
            _LOG_EXTRA_KEY_2: _LOG_EXTRA_VALUE_2,
            _LOG_EXTRA_KEY_3: _LOG_EXTRA_VALUE_3
        })
    formatted_log = datadog_custom_formatter.format(log_record)
    json_formatted_log = json.loads(formatted_log)
    assert isinstance(json_formatted_log, dict)
    assert json_formatted_log[_LOG_EXTRA_KEY_1] == _LOG_EXTRA_VALUE_1
    assert json_formatted_log[_LOG_EXTRA_KEY_2] == _LOG_EXTRA_VALUE_2
    assert json_formatted_log[
        _LOG_EXTRA_KEY_3] == _LOG_EXTRA_VALUE_3.name.capitalize()
    assert json_formatted_log['message'] == _LOG_MESSAGE


@pytest.mark.parametrize('logger', [
    logging.getLogger(),
    logging.getLogger('test1'),
    logging.getLogger('test2').getChild('test3')
])
@pytest.mark.parametrize('log_format',
                         [log_format for log_format in LogFormat])
@pytest.mark.parametrize('standard_output', [True, False])
@pytest.mark.parametrize('log_file_test',
                         [log_file_test for log_file_test in _LogFileTest])
@pytest.mark.parametrize('max_bytes', [0, 1024 * 1024, 10 * 1024 * 1024])
@pytest.mark.parametrize('backup_count', [0, 1, 10])
@pytest.mark.parametrize('debug', [True, False])
@pytest.mark.parametrize('initial_handler', [True, False])
def test_initialize_logger_correct(logger, log_format, standard_output,
                                   log_file_test, max_bytes, backup_count,
                                   debug, initial_handler):
    log_file = _create_log_file(log_file_test, max_bytes, backup_count)
    number_handlers = sum([standard_output, log_file is not None])
    if initial_handler:
        logger.addHandler(logging.StreamHandler())
    initialize_logger(logger, log_format, standard_output, log_file, debug)
    assert len(logger.handlers) == number_handlers
    standard_output_handler = False
    rotating_file_handler = False
    for handler in logger.handlers:
        _check_log_format(log_format, handler)
        assert isinstance(handler, logging.StreamHandler)
        if isinstance(handler, logging.handlers.RotatingFileHandler):
            assert not rotating_file_handler
            assert log_file is not None
            assert log_file.file_path.exists()
            assert pathlib.Path(handler.baseFilename) == log_file.file_path
            assert handler.maxBytes == max_bytes
            assert handler.backupCount == backup_count
            rotating_file_handler = True
        else:
            assert not standard_output_handler
            assert standard_output
            assert handler.stream == sys.stdout
            standard_output_handler = True
    assert logger.level == (logging.DEBUG if debug else logging.INFO)
    _delete_log_file(log_file)


@pytest.mark.parametrize('log_format',
                         [log_format for log_format in LogFormat])
def test_initialize_logger_log_correct(root_logger, log_format):
    file_path = pathlib.Path(tempfile.mkstemp()[1])
    log_file = LogFile(file_path, 0, 0)
    initialize_logger(root_logger, log_format, False, log_file, False)
    root_logger.log(
        logging.INFO, _LOG_MESSAGE, extra={
            _LOG_EXTRA_KEY_1: _LOG_EXTRA_VALUE_1,
            _LOG_EXTRA_KEY_2: _LOG_EXTRA_VALUE_2
        })
    with file_path.open() as log_file:
        log_entry = log_file.readline()
    assert _LOG_MESSAGE in log_entry
    assert _LOG_EXTRA_KEY_1 in log_entry
    assert _LOG_EXTRA_VALUE_1 in log_entry
    assert _LOG_EXTRA_KEY_2 in log_entry
    assert str(_LOG_EXTRA_VALUE_2) in log_entry
    file_path.unlink()


@unittest.mock.patch('pantos.common.logging.pathlib.Path.mkdir')
def test_initialize_logger_permission_error(mocked_mkdir, root_logger):
    mocked_mkdir.side_effect = PermissionError
    directory_path = pathlib.Path(tempfile.mkdtemp())
    file_path = directory_path / 'test' / _LOG_FILE_NAME
    log_file = LogFile(file_path, 0, 0)
    with pytest.raises(OSError):
        initialize_logger(root_logger, LogFormat.JSON, False, log_file, False)
    directory_path.rmdir()


@pytest.mark.parametrize('log_format',
                         [log_format for log_format in LogFormat])
def test_log_format_from_name_correct(log_format):
    assert LogFormat.from_name(log_format.name.lower()) is log_format
    assert LogFormat.from_name(log_format.name.upper()) is log_format


def test_log_format_from_name_error():
    with pytest.raises(NameError):
        LogFormat.from_name('unknown_log_format')


def _check_log_format(log_format, handler):
    if log_format is LogFormat.HUMAN_READABLE:
        assert isinstance(handler.formatter, _HumanReadableFormatter)
        assert handler.formatter._fmt == _HUMAN_READABLE_LOG_FORMAT
    elif log_format is LogFormat.JSON:
        assert isinstance(handler.formatter,
                          json_log_formatter.VerboseJSONFormatter)
    else:
        raise NotImplementedError


def _create_log_file(log_file_test, max_bytes, backup_count):
    if log_file_test is _LogFileTest.NO_LOG_FILE:
        return None
    elif log_file_test is _LogFileTest.LOG_FILE_EXISTING:
        file_path = pathlib.Path(tempfile.mkstemp()[1])
    elif log_file_test is _LogFileTest.LOG_DIRECTORY_EXISTING:
        file_path = pathlib.Path(tempfile.mkdtemp()) / _LOG_FILE_NAME
    elif log_file_test is _LogFileTest.LOG_DIRECTORY_NOT_EXISTING:
        file_path = pathlib.Path(tempfile.mkdtemp()) / 'test' / _LOG_FILE_NAME
    else:
        raise NotImplementedError
    return LogFile(file_path, max_bytes, backup_count)


def _delete_log_file(log_file):
    if log_file is None:
        return
    temp_dir_path = pathlib.Path(tempfile.gettempdir())
    path = log_file.file_path
    while True:
        if path == temp_dir_path:
            return
        elif path.is_dir():
            path.rmdir()
        else:
            path.unlink()
        path = path.parent

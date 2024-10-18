"""Module for initializing console and file logging.

"""
import dataclasses
import datetime
import enum
import logging
import logging.handlers
import pathlib
import sys
import typing

import json_log_formatter  # type: ignore

from pantos.common.blockchains.enums import Blockchain

_HUMAN_READABLE_LOG_FORMAT: typing.Final[str] = (
    '%(asctime)s - %(name)s - %(thread)d - %(levelname)s - '
    '%(message)s%(extra)s')


@dataclasses.dataclass
class LogFile:
    """Properties of a log file.

    Attributes
    ----------
    file_path : pathlib.Path
        The path to the log file.
    max_bytes : int
        Maximum number of bytes the log file can reach before it is
        rolled over.
    backup_count : int
        Number of old log files kept (by appending the file extensions
        .1, .2, etc.).

    """
    file_path: pathlib.Path
    max_bytes: int
    backup_count: int


class LogFormat(enum.Enum):
    """Enumeration of available log formats.

    """
    HUMAN_READABLE = 1
    JSON = 2

    @staticmethod
    def from_name(name: str) -> 'LogFormat':
        """Find an enumeration member by its name.

        Parameters
        ----------
        name : str
            The name to search for.

        Raises
        ------
        NameError
            If no enumeration member can be found for the given name.

        """
        name_upper = name.upper()
        for log_format in LogFormat:
            if name_upper == log_format.name:
                return log_format
        raise NameError(name)


class _DataDogJSONFormatter(json_log_formatter.VerboseJSONFormatter):
    """Custom JSON formatter tailored for proper DataDog logs.

    """
    def mutate_json_record(self, json_record: typing.Dict[str | int,
                                                          typing.Any]):
        """Convert fields of `json_record` to needed types.

        Parameters
        ----------
        json_record : dict of str or int, typing.Any
            The json dictionary object of the log.

        Returns
        -------
        dict of str or int, typing.Any
            The mutated dictionary object of the log.

        """
        for attribute_name in json_record:
            attribute = json_record[attribute_name]
            if isinstance(attribute, datetime.datetime):
                json_record[attribute_name] = attribute.isoformat()
            if isinstance(attribute, Blockchain):
                json_record[attribute_name] = attribute.name_in_pascal_case
        return json_record

    def json_record(self, message: str, extra: typing.Dict[str | int,
                                                           typing.Any],
                    record: typing.Any) -> typing.Dict[str | int, typing.Any]:
        """Prepares a JSON payload which will be logged.

        Parameters
        ----------
        message : str
            Log message.
        extra : dict of str or int, typing.Any
            Dictionary that was passed as `extra` parameter.
        record : typing.Any
            Log record returned by JSONFormatter.format()

        Returns
        ------
        dict of str or int, typing.Any
            The dictionary of the record.

        """
        extra['levelname'] = record.levelname
        if 'time' not in extra:
            extra['time'] = datetime.datetime.utcnow()
        extra['message'] = message
        if record.exc_info:
            extra['exc_info'] = self.formatException(record.exc_info)
        return extra


class _HumanReadableFormatter(logging.Formatter):
    """Formatter for human-readable log messages.

    """
    def __init__(self):
        log_record = logging.LogRecord(None, None, None, None, None, None,
                                       None)
        self.__log_record_attributes = set(log_record.__dict__.keys())
        self.__log_record_attributes.add('asctime')
        self.__log_record_attributes.add('message')
        super().__init__(_HUMAN_READABLE_LOG_FORMAT)

    def format(self, log_record: logging.LogRecord) -> str:
        # Docstring inherited
        extra = ''
        for key, value in log_record.__dict__.items():
            if key not in self.__log_record_attributes and key != 'extra':
                extra += f' - {key}: {value}'
        log_record.__dict__['extra'] = extra
        return super().format(log_record)


def initialize_logger(logger: logging.Logger = logging.getLogger(),
                      log_format: LogFormat = LogFormat.HUMAN_READABLE,
                      standard_output: bool = True,
                      log_file: typing.Optional[LogFile] = None,
                      debug: bool = False) -> None:
    """Initialize a logger by setting its log format, output streams,
    and the level of logged messages.

    Parameters
    ----------
    logger : logging.Logger
        The logger to be initialized (default: root logger).
    log_format : LogFormat
        The format of the log output (default: human-readable format).
    standard_output : bool
        If True, the messages are logged to the standard output, which
        is shown on the console if it is not redirected (default: True).
    log_file : LogFile, optional
        If given, messages are logged to the specified log file
        (default: None).
    debug : bool
        If True, debug messages are logged (default: False).

    Raises
    ------
    OSError
        If the logs cannot be written to the specified log file.

    """
    logger.handlers.clear()
    formatter = _create_formatter(log_format)
    if standard_output:
        logger.addHandler(_create_standard_output_handler(formatter))
    if log_file is not None:
        logger.addHandler(_create_rotating_file_handler(log_file, formatter))
    logger.setLevel(logging.DEBUG if debug else logging.INFO)


def _create_formatter(log_format: LogFormat) -> logging.Formatter:
    if log_format is LogFormat.HUMAN_READABLE:
        return _HumanReadableFormatter()
    if log_format is LogFormat.JSON:
        return _DataDogJSONFormatter()
    raise NotImplementedError


def _create_rotating_file_handler(
        log_file: LogFile, formatter: logging.Formatter) -> logging.Handler:
    if not log_file.file_path.parent.exists():
        log_file.file_path.parent.mkdir(parents=True)
    handler = logging.handlers.RotatingFileHandler(
        log_file.file_path, maxBytes=log_file.max_bytes,
        backupCount=log_file.backup_count)
    handler.setFormatter(formatter)
    return handler


def _create_standard_output_handler(
        formatter: logging.Formatter) -> logging.Handler:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    return handler

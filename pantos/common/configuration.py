"""Module for loading and parsing a configuration file.

"""
import errno
import importlib.resources
import logging
import os
import pathlib
import typing

import cerberus  # type: ignore
import dotenv
import pyaml_env  # type: ignore
import yaml

from pantos.common.exceptions import BaseError

_logger = logging.getLogger(__name__)

# Ordered by priority
_CONFIGURATION_PATHS = [
    pathlib.Path.home(),
    pathlib.Path.home() / '.config',
    pathlib.Path('/etc/pantos'),
    pathlib.Path('/etc')
]

if pathlib.Path.cwd() != pathlib.Path('/'):
    _CONFIGURATION_PATHS.insert(0, pathlib.Path.cwd())

if os.environ.get('PANTOS_CONFIG'):
    _logger.info('loading configuration from environment variable '
                 'PANTOS_CONFIG')
    _CONFIGURATION_PATHS.insert(0, pathlib.Path(os.environ['PANTOS_CONFIG']))


class _CustomValidator(cerberus.Validator):
    def _validate_one_not_present(self, other: str, field: str, value: str):
        if (bool(value)) == (bool(self.document.get(other))):
            self._error(field, "only one field can be present: " + other)

    def _normalize_coerce_load_if_file(self, value: str):
        path = pathlib.Path(value)
        try:
            # This method may trigger an exception if the path is not valid
            if path.is_file():
                with open(path, 'r') as file:
                    return file.read()
        except OSError as error:
            if error.errno != errno.ENAMETOOLONG:
                raise error
        return value


class ConfigError(BaseError):
    """Exception class for all configuration errors.

    """
    pass


class Config:
    """Class that loads and parses a configuration file and provides
    dictionary-like access to the configuration values.

    Attributes
    ----------
    default_file_name : str
        The default configuration file name to be used when no explicit
        file path is provided for loading the configuration.

    """
    def __init__(self, default_file_name: str):
        """Initialize a configuration instance.

        Parameters
        ----------
        default_file_name : str
            The default configuration file name to be used when no
            explicit file path is provided for loading the
            configuration.

        """
        self.default_file_name = default_file_name
        self.__config_dict: dict[str, typing.Any] | None = None

    def __getitem__(self, key: str) -> typing.Any:
        """Get the configuration value for a given key.

        Parameters
        ----------
        key : str
            The key to get the configuration value for.

        Returns
        -------
        Any
            The configuration value.

        Raises
        ------
        ConfigError
            If the configuration has not been loaded.

        """
        if self.__config_dict is None:
            raise ConfigError('configuration not yet loaded')
        return self.__config_dict[key]

    def __str__(self) -> str:
        return str(self.__config_dict)

    def is_loaded(self) -> bool:
        """Determine if the configuration has been loaded.

        Returns
        -------
        bool
            True if the configuration has been loaded.

        """
        return self.__config_dict is not None

    def load(self, validation_schema: dict[str, typing.Any],
             file_path: str | None = None) -> None:
        """Load the configuration from a file.

        Parameters
        ----------
        validation_schema : dict
            The Cerberus validation schema used for validating the
            loaded configuration.
        file_path : str, optional
            The path to the configuration file to load. If no file path
            is provided, the configuration is loaded from a default
            configuration file path.

        Raises
        ------
        ConfigError
            If the validation schema is invalid, the configuration file
            cannot be found, or the configuration file is invalid.

        """
        path = self.__find_file(file_path)
        _logger.info(f'loading configuration from file {path}')
        config_dict = self.__parse_file(path)
        # Validate the configuration and add default configuration values
        self.__config_dict = self.__validate(config_dict, validation_schema)

    def __find_file(self, file_path: str | None) -> pathlib.Path:
        if file_path is not None:
            # Use the specified configuration file
            path = pathlib.Path(file_path)
            if not path.is_file():
                raise ConfigError(
                    f'no configuration file found at {file_path}')
            return path
        # Find the configuration file at common locations
        for path in _CONFIGURATION_PATHS:
            config_path = path
            try:
                if config_path.is_dir():
                    config_path = config_path / self.default_file_name
                if config_path.is_file():
                    return config_path
            except OSError:
                # Perhaps the path is not readable
                _logger.warning(f'error while reading: {config_path}',
                                exc_info=True)
        # Package resource
        if importlib.resources.is_resource('pantos', self.default_file_name):
            with importlib.resources.path('pantos',
                                          self.default_file_name) as path:
                return path
        # No configuration file found at common locations
        raise ConfigError('no configuration file found')

    def __parse_file(self, path: pathlib.Path) -> dict[str, typing.Any]:
        # List of potential .env file paths
        env_files = [
            pathlib.Path(path.as_posix() + '.env'),
            pathlib.Path(path.with_suffix('.env').as_posix())
        ]
        if os.environ.get('PANTOS_ENV_FILE'):
            _logger.info('loading env variables from environment defined file '
                         'PANTOS_ENV_FILE')
            env_files.insert(0, pathlib.Path(os.environ['PANTOS_ENV_FILE']))

        # Extend env_files with .env paths from _CONFIGURATION_PATHS
        env_files.extend(
            pathlib.Path(str(p)).with_name(
                str(p.name) + self.default_file_name + '.env')
            for p in _CONFIGURATION_PATHS)
        # Iterate over the potential .env file paths
        for env_file in env_files:
            try:
                if env_file.is_file():
                    dotenv.load_dotenv(env_file)
                    _logger.info(f'loaded .env from file {env_file}')
                    break
            except OSError:
                # Perhaps the path is not readable
                _logger.warning(f'error while reading: {env_file}',
                                exc_info=True)
            except Exception:
                _logger.error(f'unable to load .env file {env_file}',
                              exc_info=True)
        # Parse the YAML code in the configuration file
        try:
            return pyaml_env.parse_config(path.as_posix(), default_value='')
        except yaml.YAMLError as error:
            if hasattr(error, 'problem_mark'):
                line = error.problem_mark.line + 1
                column = error.problem_mark.column + 1
                raise ConfigError('YAML code in configuration file invalid at '
                                  f'line {line} and column {column}')
            else:
                raise ConfigError('YAML code in configuration file invalid')

    def __validate(
            self, config_dict: dict[str, typing.Any],
            validation_schema: dict[str, typing.Any]) -> dict[str, typing.Any]:
        # Create the validator and validate the validation schema
        try:
            validator = _CustomValidator(validation_schema)
        except cerberus.schema.SchemaError as error:
            raise ConfigError(f'validation schema invalid: {error}')
        # Validate the configuration
        if not validator.validate(config_dict):
            raise ConfigError(
                f'configuration file invalid: {validator.errors}')
        # Add default configuration values
        return validator.normalized(config_dict)

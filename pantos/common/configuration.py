"""Module for loading and parsing a configuration file.

"""
import errno
import importlib.resources
import logging
import os
import pathlib

import cerberus  # type: ignore
import dotenv
import pyaml_env  # type: ignore
import yaml

from pantos.common.exceptions import BaseError

_logger = logging.getLogger(__name__)

# Ordered by priority
_CONFIGURATION_PATHS = [
    pathlib.Path.cwd(),
    pathlib.Path.home(),
    pathlib.Path.home() / '.config',
    pathlib.Path('/etc/pantos'),
    pathlib.Path('/etc')
]

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
    """TODO

    """
    def __init__(self, default_file_name):
        """TODO

        """
        assert isinstance(default_file_name, str)
        self.default_file_name = default_file_name
        self.__config_dict = None

    def __getitem__(self, key):
        """TODO

        """
        assert isinstance(key, str)
        if self.__config_dict is None:
            raise ConfigError('configuration not yet loaded')
        return self.__config_dict[key]

    def __str__(self):
        """TODO

        """
        return str(self.__config_dict)

    def is_loaded(self):
        """TODO

        """
        return self.__config_dict is not None

    def load(self, validation_schema, file_path=None):
        """TODO

        """
        assert isinstance(validation_schema, dict)
        assert file_path is None or isinstance(file_path, str)
        # Find the configuration file
        path = self.__find_file(file_path)
        _logger.info('loading configuration from file {}'.format(path))
        # Parse the configuration file
        config_dict = self.__parse_file(path)
        # Validate the configuration and add default configuration values
        self.__config_dict = self.__validate(config_dict, validation_schema)

    def __find_file(self, file_path=None):
        """TODO

        """
        assert file_path is None or isinstance(file_path, str)
        if file_path is not None:
            # Use the specified configuration file
            path = pathlib.Path(file_path)
            if not path.is_file():
                raise ConfigError('no configuration file found at '
                                  '{}'.format(file_path))
            return path
        # Find the configuration file at common locations
        for path in _CONFIGURATION_PATHS:
            config_path = path
            if config_path.is_dir():
                config_path = config_path / self.default_file_name
            if config_path.is_file():
                return config_path
        # Package resource
        if importlib.resources.is_resource('pantos', self.default_file_name):
            with importlib.resources.path('pantos',
                                          self.default_file_name) as path:
                return path
        # No configuration file found at common locations
        raise ConfigError('no configuration file found')

    def __parse_file(self, path):
        """TODO

        """
        assert isinstance(path, pathlib.Path)
        # List of potential .env file paths
        env_files = [
            pathlib.Path(path.as_posix() + '.env'),
            pathlib.Path(path.with_suffix('.env').as_posix())
        ]

        # Iterate over the potential .env file paths
        for env_file in env_files:
            if env_file.is_file():
                try:
                    dotenv.load_dotenv(env_file)
                    _logger.info(f'loaded .env from file {env_file}')
                    break
                except Exception:
                    raise ConfigError(f'unable to load .env file {env_file}')
        # Parse the YAML code in the configuration file
        try:
            return pyaml_env.parse_config(path.as_posix(), default_value='')
        except yaml.YAMLError as error:
            if hasattr(error, 'problem_mark'):
                line = error.problem_mark.line + 1
                column = error.problem_mark.column + 1
                raise ConfigError('YAML code in configuration file '
                                  'invalid at line {} and '
                                  'column {}'.format(line, column))
            else:
                raise ConfigError('YAML code in configuration file '
                                  'invalid')

    def __validate(self, config_dict, validation_schema):
        """TODO

        """
        assert isinstance(config_dict, dict)
        assert isinstance(validation_schema, dict)
        # Create the validator and validate the validation schema
        try:
            validator = _CustomValidator(validation_schema)
        except cerberus.schema.SchemaError as error:
            raise ConfigError('validation schema invalid: {}'.format(error))
        # Validate the configuration
        if not validator.validate(config_dict):
            raise ConfigError('configuration file invalid: '
                              '{}'.format(validator.errors))
        # Add default configuration values
        return validator.normalized(config_dict)

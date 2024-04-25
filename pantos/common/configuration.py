"""Module for loading and parsing a configuration file.

"""
import importlib.resources
import logging
import pathlib

import cerberus  # type: ignore
import yaml

from pantos.common.exceptions import BaseError

_logger = logging.getLogger(__name__)


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
        # Current working directory
        path = pathlib.Path.cwd() / self.default_file_name
        if path.is_file():
            return path
        # Home directory
        path = pathlib.Path.home() / self.default_file_name
        if path.is_file():
            return path
        # Hidden file in home directory
        path = pathlib.Path.home() / '.{}'.format(self.default_file_name)
        if path.is_file():
            return path
        # Subdirectory .config in home directory
        path = pathlib.Path.home() / '.config' / self.default_file_name
        if path.is_file():
            return path
        # Configuration directory /etc
        path = pathlib.Path('/etc') / self.default_file_name
        if path.is_file():
            return path
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
        with path.open() as config_file:
            # Parse the YAML code in the configuration file
            try:
                return yaml.safe_load(config_file)
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
            validator = cerberus.Validator(validation_schema)
        except cerberus.schema.SchemaError as error:
            raise ConfigError('validation schema invalid: {}'.format(error))
        # Validate the configuration
        if not validator.validate(config_dict):
            raise ConfigError('configuration file invalid: '
                              '{}'.format(validator.errors))
        # Add default configuration values
        return validator.normalized(config_dict)

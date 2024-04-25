import pathlib
from unittest.mock import mock_open
from unittest.mock import patch

import pytest

from pantos.common.configuration import Config
from pantos.common.configuration import ConfigError


def test_validate_one_not_present():
    # Test with valid data
    validation_schema = {
        'private_key_path': {
            'type': 'string',
            'required': True,
            'one_not_present': 'private_key_value'
        },
        'private_key_value': {
            'type': 'string',
            'required': True,
            'one_not_present': 'private_key_path'
        }
    }
    config_dict = {'private_key_path': 'path', 'private_key_value': ''}
    config = Config('')
    result = config._Config__validate(config_dict, validation_schema)
    assert result is not None

    # Test with invalid data
    config_dict = {'private_key_path': '', 'private_key_value': ''}
    with pytest.raises(ConfigError):
        config._Config__validate(config_dict, validation_schema)


@patch('pathlib.Path.is_file')
@patch('builtins.open', new_callable=mock_open, read_data="loaded")
def test_validate_load_if_file(mock_open, mock_is_file):
    # Test with valid data
    validation_schema = {
        'private_key_path': {
            'type': 'string',
            'coerce': 'load_if_file'
        },
    }
    config_dict = {'private_key_path': 'not a path'}
    config = Config('')

    mock_is_file.return_value = True
    result = config._Config__validate(config_dict, validation_schema)
    assert result == {'private_key_path': 'loaded'}

    # Test with invalid data
    mock_is_file.return_value = False
    result = config._Config__validate(config_dict, validation_schema)
    assert result == {'private_key_path': 'not a path'}


def test_validate_load_if_long_string_not_file():
    validation_schema = {
        'private_key_path': {
            'type': 'string',
            'coerce': 'load_if_file'
        },
    }
    config_dict = {'private_key_path': '{ a }' * 100000}
    config = Config('')

    result = config._Config__validate(config_dict, validation_schema)
    assert result == {'private_key_path': '{ a }' * 100000}


@patch('pathlib.Path.is_file')
def test_validate_load_os_error_escalates(mock_is_file):
    validation_schema = {
        'private_key_path': {
            'type': 'string',
            'coerce': 'load_if_file'
        },
    }
    config_dict = {'private_key_path': '/tmp/invalid'}  # nosec
    config = Config('')
    mock_is_file.return_value = True

    with pytest.raises(ConfigError):
        config._Config__validate(config_dict, validation_schema)


@patch('pathlib.Path.is_file')
@patch('dotenv.load_dotenv')
@patch('pyaml_env.parse_config')
@patch('builtins.open', new_callable=mock_open, read_data="data")
def test_parse_file(mock_open, mock_parse_config, mock_load_dotenv,
                    mock_is_file):
    mock_is_file.return_value = True
    mock_load_dotenv.return_value = True
    mock_parse_config.return_value = {'key': 'value'}

    config = Config('config.yaml')
    result = config._Config__parse_file(
        pathlib.Path('config.yaml'))  # Accessing private function

    assert result == {'key': 'value'}

    mock_load_dotenv.assert_called_once()
    mock_parse_config.assert_called_once()


@patch('pathlib.Path.is_file')
@patch('dotenv.load_dotenv')
@patch('pyaml_env.parse_config')
@patch('builtins.open', new_callable=mock_open, read_data="data")
def test_parse_file_error(mock_open, mock_parse_config, mock_load_dotenv,
                          mock_is_file):
    mock_is_file.return_value = True
    mock_load_dotenv.side_effect = Exception()
    mock_parse_config.return_value = {'key': 'value'}

    config = Config('config.yaml')
    with pytest.raises(ConfigError):
        config._Config__parse_file(
            pathlib.Path('config.yaml'))  # Accessing private function

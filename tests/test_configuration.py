import os
import pathlib
import unittest.mock
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
@patch.object(Config, '_Config__parse_config', return_value={'key': 'value'})
@patch('builtins.open', new_callable=mock_open, read_data="data")
def test_parse_file(mock_open, mock_parse_config, mock_load_dotenv,
                    mock_is_file):
    mock_is_file.return_value = True
    mock_load_dotenv.return_value = True

    config = Config('config.yaml')
    result = config._Config__parse_file(
        pathlib.Path('config.yaml'))  # Accessing private function

    assert result == {'key': 'value'}

    mock_load_dotenv.assert_called_once()
    mock_parse_config.assert_called_once()


@patch('pathlib.Path.is_file')
@patch('dotenv.load_dotenv')
@patch.object(Config, '_Config__parse_config', return_value={'key': 'value'})
@patch('builtins.open', new_callable=mock_open, read_data="data")
def test_parse_file_error(mock_open, mock_parse_config, mock_load_dotenv,
                          mock_is_file):
    mock_is_file.return_value = True
    mock_load_dotenv.side_effect = Exception()

    config = Config('config.yaml')
    result = config._Config__parse_file(
        pathlib.Path('config.yaml'))  # Accessing private function

    assert result == {'key': 'value'}


@patch(
    'builtins.open',
    unittest.mock.mock_open(read_data="""
        database:
            name: test_db
            username: !ENV ${DB_USER:paws}
            password: !ENV ${DB_PASS:meaw2}
            url: !ENV 'http://${DB_BASE_URL:prod_url}:${DB_PORT:80}'
        """))
def test_parse_config_default_values():
    config = Config('config.yaml')

    result = config._Config__parse_config('ok', '')

    assert result == {
        'database': {
            'name': 'test_db',
            'username': 'paws',
            'password': 'meaw2',
            'url': 'http://prod_url:80'
        }
    }


@patch(
    'builtins.open',
    unittest.mock.mock_open(read_data="""
        database:
            name: test_db
            username: !ENV ${DB_USER:paws}
            password: !ENV ${DB_PASS:meaw2}
            url: !ENV 'http://${DB_BASE_URL:prod_url}:${DB_PORT:80}'
        """))
def test_parse_config_env_variables_values():
    config = Config('config.yaml')
    os.environ['DB_USER'] = 'some_other_user'
    os.environ['DB_PASS'] = 'some_other_pass'
    os.environ['DB_BASE_URL'] = 'some_other_url'
    os.environ['DB_PORT'] = '443'

    result = config._Config__parse_config('ok', '')

    assert result == {
        'database': {
            'name': 'test_db',
            'username': 'some_other_user',
            'password': 'some_other_pass',
            'url': 'http://some_other_url:443'
        }
    }
    del os.environ['DB_USER']
    del os.environ['DB_PASS']
    del os.environ['DB_BASE_URL']
    del os.environ['DB_PORT']


@patch(
    'builtins.open',
    unittest.mock.mock_open(read_data="""
        database:
            urls: !ENV ${URLS}
        """))
def test_parse_config_env_variables_list_value():
    config = Config('config.yaml')
    os.environ['URLS'] = 'first_url|second_url|third_url'

    result = config._Config__parse_config('ok', '')

    assert result == {
        'database': {
            'urls': ['first_url', 'second_url', 'third_url']
        }
    }
    del os.environ['URLS']


@patch(
    'builtins.open',
    unittest.mock.mock_open(read_data="""
        database:
            urls: !ENV ${URLS}
            username: !ENV ${DB_USER:paws}
            password: !ENV ${DB_PASS:meaw2}
        """))
def test_parse_config_env_variables_mix_values():
    config = Config('config.yaml')
    os.environ['URLS'] = 'first_url|second_url|third_url'
    os.environ['DB_PASS'] = 'some_other_pass'

    result = config._Config__parse_config('ok', '')

    assert result == {
        'database': {
            'urls': ['first_url', 'second_url', 'third_url'],
            'username': 'paws',
            'password': 'some_other_pass'
        }
    }
    del os.environ['URLS']
    del os.environ['DB_PASS']

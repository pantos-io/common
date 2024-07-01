import json
import unittest.mock

import pytest
import werkzeug.exceptions

from pantos.common.blockchains.base import GENERAL_RPC_ERROR_MESSAGE
from pantos.common.blockchains.base import UnhealthyNode
from pantos.common.blockchains.enums import Blockchain
from pantos.common.exceptions import NotInitializedError
from pantos.common.health import NodesHealth
from pantos.common.restapi import NodesHealthResource
from pantos.common.restapi import bad_request
from pantos.common.restapi import conflict
from pantos.common.restapi import forbidden
from pantos.common.restapi import internal_server_error
from pantos.common.restapi import no_content_response
from pantos.common.restapi import not_acceptable
from pantos.common.restapi import ok_response
from pantos.common.restapi import resource_not_found


@pytest.fixture
def error_message():
    return 'error message'


@pytest.fixture
def error_message_list():
    return [
        'first error message', 'second error message', 'third error message'
    ]


@pytest.fixture
def error_message_dict():
    return {
        'first_property': 'first error message',
        'second_property': 'second error message',
        'third_property': 'third error message'
    }


@unittest.mock.patch('pantos.common.restapi.check_blockchain_nodes_health')
def test_nodes_health_resource_correct(mocked_check_blockchain_nodes_health):
    mocked_check_blockchain_nodes_health.return_value = {
        Blockchain.ETHEREUM: NodesHealth(1, 0, []),
        Blockchain.BNB_CHAIN: NodesHealth(0, 2, [
            UnhealthyNode('node1_domain', GENERAL_RPC_ERROR_MESSAGE),
            UnhealthyNode('node2_domain', GENERAL_RPC_ERROR_MESSAGE)
        ])
    }
    nodes_health_resource = NodesHealthResource()

    response = nodes_health_resource.get()

    assert response.status_code == 200
    assert json.loads(response.data) == {
        'Ethereum': {
            'healthy_total': 1,
            'unhealthy_total': 0,
            'unhealthy_nodes': []
        },
        'Bnb_chain': {
            'healthy_total': 0,
            'unhealthy_total': 2,
            'unhealthy_nodes': [{
                'node_domain': 'node1_domain',
                "status": GENERAL_RPC_ERROR_MESSAGE
            }, {
                'node_domain': "node2_domain",
                'status': GENERAL_RPC_ERROR_MESSAGE
            }]
        }
    }


@unittest.mock.patch('pantos.common.restapi.check_blockchain_nodes_health')
def test_nodes_health_resource_uninitialized_nodes(
        mocked_check_blockchain_nodes_health):
    mocked_check_blockchain_nodes_health.side_effect = NotInitializedError('')
    nodes_health_resource = NodesHealthResource()

    with pytest.raises(werkzeug.exceptions.HTTPException) as exception_info:
        nodes_health_resource.get()

    assert isinstance(exception_info.value,
                      werkzeug.exceptions.InternalServerError)
    assert exception_info.value.data[
        'message'] == 'no blockchain nodes have been initialized yet'


@unittest.mock.patch('pantos.common.restapi.check_blockchain_nodes_health')
def test_nodes_health_resource_exception(mocked_check_blockchain_nodes_health):
    mocked_check_blockchain_nodes_health.side_effect = Exception
    nodes_health_resource = NodesHealthResource()

    with pytest.raises(werkzeug.exceptions.HTTPException) as exception_info:
        nodes_health_resource.get()

    assert isinstance(exception_info.value,
                      werkzeug.exceptions.InternalServerError)
    assert exception_info.value.data['message'] is None


def test_ok_response():
    data = {
        'first_property': 1,
        'second_propery': 'a',
        'third_property': True,
        'fourth_property': 1.01
    }

    response = ok_response(data)

    assert response.status_code == 200
    assert response.mimetype == 'application/json'
    assert json.loads(response.data) == data


def test_no_content_response():
    response = no_content_response()

    assert response.status_code == 204
    assert len(response.data) == 0


def test_bad_request_str(error_message):
    with pytest.raises(werkzeug.exceptions.HTTPException) as exception_info:
        bad_request(error_message)

    assert isinstance(exception_info.value, werkzeug.exceptions.BadRequest)
    assert exception_info.value.data['message'] == error_message


def test_bad_request_list(error_message_list):
    with pytest.raises(werkzeug.exceptions.HTTPException) as exception_info:
        bad_request(error_message_list)

    assert isinstance(exception_info.value, werkzeug.exceptions.BadRequest)
    assert exception_info.value.data['message'] == error_message_list


def test_bad_request_dict(error_message_dict):
    with pytest.raises(werkzeug.exceptions.HTTPException) as exception_info:
        bad_request(error_message_dict)

    assert isinstance(exception_info.value, werkzeug.exceptions.BadRequest)
    assert exception_info.value.data['message'] == error_message_dict


def test_forbidden(error_message):
    with pytest.raises(werkzeug.exceptions.HTTPException) as exception_info:
        forbidden(error_message)

    assert isinstance(exception_info.value, werkzeug.exceptions.Forbidden)
    assert exception_info.value.data['message'] == error_message


def test_resource_not_found(error_message):
    with pytest.raises(werkzeug.exceptions.HTTPException) as exception_info:
        resource_not_found(error_message)

    assert isinstance(exception_info.value, werkzeug.exceptions.NotFound)
    assert exception_info.value.data['message'] == error_message


def test_not_acceptable_str(error_message):
    with pytest.raises(werkzeug.exceptions.HTTPException) as exception_info:
        not_acceptable(error_message)

    assert isinstance(exception_info.value, werkzeug.exceptions.NotAcceptable)
    assert exception_info.value.data['message'] == error_message


def test_not_acceptable_list(error_message_list):
    with pytest.raises(werkzeug.exceptions.HTTPException) as exception_info:
        not_acceptable(error_message_list)

    assert isinstance(exception_info.value, werkzeug.exceptions.NotAcceptable)
    assert exception_info.value.data['message'] == error_message_list


def test_not_acceptable_dict(error_message_dict):
    with pytest.raises(werkzeug.exceptions.HTTPException) as exception_info:
        not_acceptable(error_message_dict)

    assert isinstance(exception_info.value, werkzeug.exceptions.NotAcceptable)
    assert exception_info.value.data['message'] == error_message_dict


def test_conflict(error_message):
    with pytest.raises(werkzeug.exceptions.HTTPException) as exception_info:
        conflict(error_message)

    assert isinstance(exception_info.value, werkzeug.exceptions.Conflict)
    assert exception_info.value.data['message'] == error_message


@pytest.mark.parametrize('with_error_message', [True, False])
def test_internal_server_error(with_error_message, error_message):
    with pytest.raises(werkzeug.exceptions.HTTPException) as exception_info:
        internal_server_error(error_message if with_error_message else None)

    assert isinstance(exception_info.value,
                      werkzeug.exceptions.InternalServerError)
    assert exception_info.value.data['message'] == (
        error_message if with_error_message else None)

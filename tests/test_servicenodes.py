import unittest.mock
import uuid

import pytest
import requests

from pantos.common.blockchains.enums import Blockchain
from pantos.common.entities import ServiceNodeBid
from pantos.common.servicenodes import ServiceNodeClient
from pantos.common.servicenodes import ServiceNodeClientError
from pantos.common.types import BlockchainAddress

mock_transfer_request = ServiceNodeClient.SubmitTransferRequest(
    'url', Blockchain(0), Blockchain(1), BlockchainAddress('sender_addr'),
    BlockchainAddress('recipient_addr'), BlockchainAddress('source_token'),
    BlockchainAddress('destination_token'), 77,
    ServiceNodeBid(Blockchain(0), Blockchain(1), 77, 1337, 77, 'signature'), 2,
    22, 'signature')

mock_service_node_request = json = {
    'source_blockchain_id': 0,
    'destination_blockchain_id': 1,
    'sender_address': 'sender_addr',
    'recipient_address': 'recipient_addr',
    'source_token_address': 'source_token',
    'destination_token_address': 'destination_token',
    'amount': 77,
    'bid': {
        'fee': 77,
        'execution_time': 1337,
        'valid_until': 77,
        'signature': 'signature'
    },
    'nonce': 2,
    'valid_until': 22,
    'signature': 'signature'
}

mock_bid_response = {
    'fee': 100,
    'execution_time': 200,
    'valid_until': 300,
    'signature': 'mock_signature'
}

mock_response_header = requests.utils.CaseInsensitiveDict(
    {'Content-Type': 'application/json'})
mock_response_header_html = requests.utils.CaseInsensitiveDict(
    {'Content-Type': 'text/html; charset=UTF-8'})


@unittest.mock.patch.object(ServiceNodeClient,
                            '_ServiceNodeClient__build_transfer_url')
@unittest.mock.patch('pantos.common.servicenodes.requests.post')
def test_submit_transfer_correct(mocked_post, mocked_build_transfer_url):
    uuid_string = '123e4567-e89b-12d3-a456-426655440000'
    mocked_post().json.return_value = {'task_id': uuid_string}

    result = ServiceNodeClient().submit_transfer(mock_transfer_request)

    assert type(result) == uuid.UUID
    assert str(result) == uuid_string
    mocked_build_transfer_url.assert_called_once_with(
        mock_transfer_request.service_node_url)
    mocked_post.assert_called_with(mocked_build_transfer_url(),
                                   json=mock_service_node_request,
                                   timeout=None)
    mocked_post().raise_for_status.assert_called_once()
    mocked_post().json.assert_called_with()


@unittest.mock.patch.object(ServiceNodeClient,
                            '_ServiceNodeClient__build_transfer_url')
@unittest.mock.patch('pantos.common.servicenodes.locals',
                     return_value=['response'])
@unittest.mock.patch('pantos.common.servicenodes.requests.post')
def test_submit_transfer_exception(mocked_post, mocked_locals,
                                   mocked_build_transfer_url):
    mocked_post(
    ).raise_for_status.side_effect = requests.exceptions.RequestException
    mocked_post().json.return_value = {'message': 'specific error message'}
    mocked_post().headers = mock_response_header

    with pytest.raises(ServiceNodeClientError, match='specific error message'):
        ServiceNodeClient().submit_transfer(mock_transfer_request)


@unittest.mock.patch.object(ServiceNodeClient,
                            '_ServiceNodeClient__build_transfer_url')
@unittest.mock.patch('pantos.common.servicenodes.locals',
                     return_value=['response'])
@unittest.mock.patch('pantos.common.servicenodes.requests.post')
def test_submit_transfer_no_response_message_exception(
        mocked_post, mocked_locals, mocked_build_transfer_url):
    mocked_post(
    ).raise_for_status.side_effect = requests.exceptions.RequestException
    mocked_post().headers = mock_response_header
    mocked_post().json.return_value = {}

    with pytest.raises(ServiceNodeClientError):
        ServiceNodeClient().submit_transfer(mock_transfer_request)


@unittest.mock.patch.object(ServiceNodeClient,
                            '_ServiceNodeClient__build_transfer_url')
@unittest.mock.patch('pantos.common.servicenodes.locals',
                     return_value=['response'])
@unittest.mock.patch('pantos.common.servicenodes.requests.post')
def test_submit_transfer_html_response_exception(mocked_post, mocked_locals,
                                                 mocked_build_transfer_url):
    mocked_post(
    ).raise_for_status.side_effect = requests.exceptions.RequestException
    mocked_post().headers = mock_response_header_html

    with pytest.raises(ServiceNodeClientError):
        ServiceNodeClient().submit_transfer(mock_transfer_request)

    assert not mocked_post.json.called


def test_build_transfer_url_no_slash_correct():
    url = 'some_url'
    result = ServiceNodeClient()._ServiceNodeClient__build_transfer_url(url)
    assert result == 'some_url/transfer'


def test_build_transfer_url_with_slash_correct():
    url = 'some_url/'
    result = ServiceNodeClient()._ServiceNodeClient__build_transfer_url(url)
    assert result == 'some_url/transfer'


@unittest.mock.patch('pantos.common.servicenodes.requests.get')
def test_bids_correct(mocked_get):
    url = 'mock_url'
    source_blockchain = Blockchain.ETHEREUM
    destination_blockchain = Blockchain.BNB_CHAIN
    mocked_get().json.return_value = [mock_bid_response]

    bids = ServiceNodeClient().bids(url, source_blockchain,
                                    destination_blockchain)

    assert bids[0] == ServiceNodeBid(source_blockchain, destination_blockchain,
                                     mock_bid_response['fee'],
                                     mock_bid_response['execution_time'],
                                     mock_bid_response['valid_until'],
                                     mock_bid_response['signature'])


@unittest.mock.patch('pantos.common.servicenodes.requests.get')
def test_bids_url_has_slash_correc(mocked_get):
    url = 'mock_url/'
    source_blockchain = Blockchain.ETHEREUM
    destination_blockchain = Blockchain.BNB_CHAIN
    mocked_get().json.return_value = [mock_bid_response]

    bids = ServiceNodeClient().bids(url, source_blockchain,
                                    destination_blockchain)

    assert bids[0] == ServiceNodeBid(source_blockchain, destination_blockchain,
                                     mock_bid_response['fee'],
                                     mock_bid_response['execution_time'],
                                     mock_bid_response['valid_until'],
                                     mock_bid_response['signature'])


@unittest.mock.patch('pantos.common.servicenodes.requests.get')
def test_bids_service_node_client_error(mocked_get):
    url = 'mock_url'
    source_blockchain = Blockchain.ETHEREUM
    destination_blockchain = Blockchain.BNB_CHAIN
    mocked_get(
    ).raise_for_status.side_effect = requests.exceptions.RequestException
    mocked_get().json.return_value = {'message': 'specific error message'}
    mocked_get().headers = mock_response_header

    with pytest.raises(ServiceNodeClientError, match='specific error message'):
        ServiceNodeClient().bids(url, source_blockchain,
                                 destination_blockchain)


@unittest.mock.patch('pantos.common.servicenodes.requests.get')
def test_bids_service_node_no_response_message_client_error(mocked_get):
    url = 'mock_url'
    source_blockchain = Blockchain.ETHEREUM
    destination_blockchain = Blockchain.BNB_CHAIN
    mocked_get(
    ).raise_for_status.side_effect = requests.exceptions.RequestException
    mocked_get().headers = mock_response_header
    mocked_get().json.return_value = {}

    with pytest.raises(ServiceNodeClientError):
        ServiceNodeClient().bids(url, source_blockchain,
                                 destination_blockchain)


@unittest.mock.patch('pantos.common.servicenodes.requests.get')
def test_bids_service_node_html_response_client_error(mocked_get):
    url = 'mock_url'
    source_blockchain = Blockchain.ETHEREUM
    destination_blockchain = Blockchain.BNB_CHAIN
    mocked_get(
    ).raise_for_status.side_effect = requests.exceptions.RequestException
    mocked_get().headers = mock_response_header_html

    with pytest.raises(ServiceNodeClientError):
        ServiceNodeClient().bids(url, source_blockchain,
                                 destination_blockchain)
    assert not mocked_get.json.called


def test_build_bids_url_no_slash_correct():
    url = 'some_url'
    result = ServiceNodeClient()._ServiceNodeClient__build_bids_url(url, 1, 4)
    expected = 'some_url/bids?source_blockchain=1&destination_blockchain=4'
    assert result == expected


def test_build_bids_url_with_slash_correct():
    url = 'some_url/'
    result = ServiceNodeClient()._ServiceNodeClient__build_bids_url(url, 1, 4)
    expected = 'some_url/bids?source_blockchain=1&destination_blockchain=4'
    assert result == expected


@unittest.mock.patch('pantos.common.servicenodes.ServiceNodeTransferStatus')
@unittest.mock.patch('pantos.common.servicenodes.BlockchainAddress')
@unittest.mock.patch('pantos.common.servicenodes.Blockchain')
@unittest.mock.patch('pantos.common.servicenodes.uuid')
@unittest.mock.patch('pantos.common.servicenodes.requests.get')
def test_status_correct(mocked_get, mocked_uuid, mocked_blockchain,
                        mocked_blockchain_address, mocked_status):
    task_id = uuid.UUID('cf9ff19f-b691-46c6-8645-08d05309ea84')

    result = ServiceNodeClient().status('', task_id)

    mocked_get.assert_called_once_with(
        '/transfer/cf9ff19f-b691-46c6-8645-08d05309ea84/status', timeout=None)
    mocked_get().json.assert_called_once_with()
    mocked_json_result = mocked_get(
        '/transfer/cf9ff19f-b691-46c6-8645-08d05309ea84/status').json()
    assert result.task_id == mocked_uuid.UUID(mocked_json_result['task_id'])
    assert result.source_blockchain == mocked_blockchain(
        mocked_json_result['source_blockchain_id'])
    assert result.destination_blockchain == mocked_blockchain(
        mocked_json_result['destination_blockchain_id'])
    assert result.sender_address == mocked_blockchain_address(
        mocked_json_result['sender_address'])
    assert result.recipient_address == mocked_blockchain_address(
        mocked_json_result['recipient_address'])
    assert result.source_token_address == mocked_blockchain_address(
        mocked_json_result['source_token_address'])
    assert result.destination_token_address == mocked_blockchain_address(
        mocked_json_result['destination_token_address'])
    assert result.token_amount == mocked_json_result['amount']
    assert result.status == mocked_status.from_name(
        mocked_json_result['status'])
    assert result.transfer_id == mocked_json_result['transfer_id']
    assert result.transaction_id == mocked_json_result['transaction_id']


@unittest.mock.patch('pantos.common.servicenodes.locals',
                     return_value=['response'])
@unittest.mock.patch('pantos.common.servicenodes.requests.get')
def test_status_exception(mocked_get, mocked_locals):
    task_id = uuid.UUID('cf9ff19f-b691-46c6-8645-08d05309ea84')
    mocked_get(
    ).raise_for_status.side_effect = requests.exceptions.RequestException
    mocked_get().json.return_value = {'message': 'specific error message'}
    mocked_get().headers = mock_response_header

    with pytest.raises(ServiceNodeClientError, match='specific error message'):
        ServiceNodeClient().status('', task_id)


@unittest.mock.patch('pantos.common.servicenodes.locals',
                     return_value=['response'])
@unittest.mock.patch('pantos.common.servicenodes.requests.get')
def test_status_no_response_message_exception(mocked_get, mocked_locals):
    task_id = uuid.UUID('cf9ff19f-b691-46c6-8645-08d05309ea84')
    mocked_get(
    ).raise_for_status.side_effect = requests.exceptions.RequestException
    mocked_get().headers = mock_response_header
    mocked_get().json.return_value = {}
    with pytest.raises(ServiceNodeClientError):
        ServiceNodeClient().status('', task_id)


@unittest.mock.patch('pantos.common.servicenodes.locals',
                     return_value=['response'])
@unittest.mock.patch('pantos.common.servicenodes.requests.get')
def test_status_html_response_message_exception(mocked_get, mocked_locals):
    task_id = uuid.UUID('cf9ff19f-b691-46c6-8645-08d05309ea84')
    mocked_get(
    ).raise_for_status.side_effect = requests.exceptions.RequestException
    mocked_get().headers = mock_response_header_html
    with pytest.raises(ServiceNodeClientError):
        ServiceNodeClient().status('', task_id)
    assert not mocked_get.json.called


def test_build_status_url_no_slash_correct():
    url = 'some_url'
    task_id = 'some_task_id'
    result = ServiceNodeClient()._ServiceNodeClient__build_status_url(
        url, task_id)
    assert result == 'some_url/transfer/some_task_id/status'


def test_build_status_url_with_slash_correct():
    url = 'some_url/'
    task_id = 'some_task_id'
    result = ServiceNodeClient()._ServiceNodeClient__build_status_url(
        url, task_id)
    assert result == 'some_url/transfer/some_task_id/status'

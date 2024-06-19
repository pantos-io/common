import dataclasses
import importlib
import json
import pathlib
import unittest.mock
import uuid

import pytest

from pantos.common.blockchains.base import _BASE_CONTRACT_ABI_PACKAGE
from pantos.common.blockchains.base import BlockchainUtilities
from pantos.common.blockchains.base import BlockchainUtilitiesError
from pantos.common.blockchains.base import MaxTotalFeePerGasExceededError
from pantos.common.blockchains.base import NodeConnectionError
from pantos.common.blockchains.base import NodeConnections
from pantos.common.blockchains.base import ResultsNotMatchingError
from pantos.common.blockchains.base import SingleNodeConnectionError
from pantos.common.blockchains.base import TransactionUnderpricedError
from pantos.common.blockchains.base import VersionedContractAbi
from pantos.common.blockchains.enums import ContractAbi
from pantos.common.entities import TransactionStatus

_CONTRACT_ABI = '''
    [
        {
            "inputs": [],
            "name": "getAddress",
            "outputs": [
                {
                    "internalType": "address",
                    "name": "",
                    "type": "address"
                }
            ],
            "stateMutability": "view",
            "type": "function"
        },
        {
            "inputs": [
                {
                    "internalType": "address",
                    "name": "address_",
                    "type": "address"
                }
            ],
            "name": "setAddress",
            "outputs": [],
            "stateMutability": "nonpayable",
            "type": "function"
        }
    ]
'''


@pytest.fixture
@unittest.mock.patch.object(BlockchainUtilities, '__abstractmethods__', set())
def blockchain_utilities(blockchain_node_urls, fallback_blockchain_node_urls,
                         average_block_time,
                         required_transaction_confirmations,
                         transaction_network_id, account):
    return BlockchainUtilities(
        blockchain_node_urls, fallback_blockchain_node_urls,
        average_block_time, required_transaction_confirmations,
        transaction_network_id,
        default_private_key=(account.keystore, account.keystore_password),
        celery_tasks_enabled=True)


@pytest.mark.parametrize('celery_tasks_enabled', [True, False])
@unittest.mock.patch.object(BlockchainUtilities, 'decrypt_private_key')
@unittest.mock.patch.object(BlockchainUtilities, 'get_address')
@unittest.mock.patch.object(BlockchainUtilities, '__abstractmethods__', set())
def test_init_correct(mock_get_address, mock_decrypt_private_key,
                      celery_tasks_enabled, blockchain_node_urls,
                      fallback_blockchain_node_urls, average_block_time,
                      required_transaction_confirmations,
                      transaction_network_id, account):
    mock_get_address.return_value = account.address
    mock_decrypt_private_key.return_value = account.private_key
    blockchain_utilities = BlockchainUtilities(
        blockchain_node_urls, fallback_blockchain_node_urls,
        average_block_time, required_transaction_confirmations,
        transaction_network_id,
        default_private_key=(account.keystore, account.keystore_password),
        celery_tasks_enabled=celery_tasks_enabled)
    assert blockchain_utilities.average_block_time == average_block_time
    assert (blockchain_utilities.required_transaction_confirmations ==
            required_transaction_confirmations)
    assert (
        blockchain_utilities.transaction_network_id == transaction_network_id)
    assert blockchain_utilities._blockchain_node_urls == blockchain_node_urls
    assert blockchain_utilities._default_private_key == account.private_key
    assert blockchain_utilities._default_address == account.address
    assert blockchain_utilities._celery_tasks_enabled == celery_tasks_enabled


@pytest.mark.parametrize('replaced_arg', [2, 3, 4])
@unittest.mock.patch.object(BlockchainUtilities, 'get_error_class',
                            return_value=BlockchainUtilitiesError)
@unittest.mock.patch.object(BlockchainUtilities, '__abstractmethods__', set())
def test_init_error(mock_get_error_class, replaced_arg, blockchain_node_urls,
                    fallback_blockchain_node_urls, average_block_time,
                    required_transaction_confirmations,
                    transaction_network_id):
    args = [
        blockchain_node_urls, fallback_blockchain_node_urls,
        average_block_time, required_transaction_confirmations,
        transaction_network_id
    ]
    args[replaced_arg] = -1
    with pytest.raises(BlockchainUtilitiesError):
        BlockchainUtilities(*args)


@unittest.mock.patch.object(BlockchainUtilities, 'get_error_class',
                            return_value=BlockchainUtilitiesError)
@unittest.mock.patch.object(BlockchainUtilities, '__abstractmethods__', set())
def test_init_no_blockchain_node_uri_error(mock_get_error_class,
                                           average_block_time,
                                           required_transaction_confirmations,
                                           transaction_network_id):
    args = [[], [], average_block_time, required_transaction_confirmations,
            transaction_network_id]
    with pytest.raises(BlockchainUtilitiesError):
        BlockchainUtilities(*args)


@unittest.mock.patch.object(BlockchainUtilities,
                            '_get_transaction_method_names', return_value=[''])
@unittest.mock.patch.object(BlockchainUtilities,
                            '_create_single_node_connection')
def test_create_node_connection_correct(mocked_create_single_node_connection,
                                        mocked_get_transaction_method_names,
                                        blockchain_utilities):
    mocked_create_single_node_connection.return_value = 'test_connection'

    node_connections = blockchain_utilities.create_node_connections()

    assert node_connections._NodeConnections__node_connections == [
        'test_connection'
    ]


@unittest.mock.patch.object(BlockchainUtilities,
                            '_get_transaction_method_names', return_value=[''])
@unittest.mock.patch.object(BlockchainUtilities,
                            '_create_single_node_connection')
def test_create_node_connection_fallback_not_used_twice_correct(
        mocked_create_single_node_connection,
        mocked_get_transaction_method_names, blockchain_utilities):
    blockchain_utilities._blockchain_node_urls = ['node1', 'node2']
    blockchain_utilities._fallback_blockchain_node_urls = [
        'fallback_node1', 'fallback_node2'
    ]
    mocked_create_single_node_connection.side_effect = \
        lambda node_url, _: node_url if node_url.startswith('fallback') \
        else exec('raise SingleNodeConnectionError()')

    node_connections = blockchain_utilities.create_node_connections()

    assert node_connections._NodeConnections__node_connections == [
        'fallback_node1', 'fallback_node2'
    ]
    assert blockchain_utilities._fallback_blockchain_node_urls == [
        'fallback_node1', 'fallback_node2'
    ]  # testing for unintented side effect


@unittest.mock.patch.object(BlockchainUtilities, 'get_error_class',
                            return_value=BlockchainUtilitiesError)
@unittest.mock.patch.object(BlockchainUtilities,
                            '_get_transaction_method_names', return_value=[''])
@unittest.mock.patch.object(BlockchainUtilities,
                            '_create_single_node_connection')
def test_create_node_connection_no_node_connection_valid(
        mocked_create_single_node_connection,
        mocked_get_transaction_method_names, mock_get_error_class,
        blockchain_utilities):
    blockchain_utilities._blockchain_node_urls = ['node1', 'node2']
    blockchain_utilities._fallback_blockchain_node_urls = [
        'fallback_node1', 'fallback_node2'
    ]
    mocked_create_single_node_connection.side_effect = \
        SingleNodeConnectionError()

    with pytest.raises(BlockchainUtilitiesError):
        blockchain_utilities.create_node_connections()


@unittest.mock.patch.object(ContractAbi, 'get_file_name')
def test_load_contract_abi_correct(mock_get_file_name, blockchain_utilities,
                                   contracts_abi_version):
    abi_file_name = f'{uuid.uuid4()}.abi'
    mock_get_file_name.return_value = abi_file_name
    module_to_import = (
        f'{_BASE_CONTRACT_ABI_PACKAGE}.v{contracts_abi_version.major}_'
        f'{contracts_abi_version.minor}_{contracts_abi_version.patch}')
    module = importlib.import_module(module_to_import)
    abi_file_path = pathlib.Path(module.__file__).parent / abi_file_name
    contract_abi = list(ContractAbi)[0]
    versioned_contract_abi = VersionedContractAbi(contract_abi,
                                                  contracts_abi_version)
    contract_abi_list = json.loads(_CONTRACT_ABI)
    try:
        with abi_file_path.open('w') as abi_file:
            abi_file.write(_CONTRACT_ABI)
        loaded_contract_abi_list = blockchain_utilities.load_contract_abi(
            versioned_contract_abi)
    finally:
        abi_file_path.unlink()
    assert loaded_contract_abi_list == contract_abi_list
    # Make sure that a cached version is returned when the function is
    # invoked again (loading the ABI again from the file would fail
    # since the file has already been deleted)
    loaded_contract_abi_list = blockchain_utilities.load_contract_abi(
        versioned_contract_abi)
    assert loaded_contract_abi_list == contract_abi_list


@unittest.mock.patch.object(ContractAbi, 'get_file_name',
                            return_value=f'{uuid.uuid4()}.abi')
@unittest.mock.patch.object(BlockchainUtilities, 'get_error_class',
                            return_value=BlockchainUtilitiesError)
def test_load_contract_abi_error(mock_get_error_class, mock_get_file_name,
                                 blockchain_utilities, contracts_abi_version):
    versioned_contract_abi = VersionedContractAbi(
        list(ContractAbi)[0], contracts_abi_version)
    with pytest.raises(BlockchainUtilitiesError):
        blockchain_utilities.load_contract_abi(versioned_contract_abi)


@pytest.mark.parametrize('underpriced_submissions', [0, 1, 10])
@pytest.mark.parametrize('min_adaptable_fee_per_gas', [0, int(1e6), int(1e9)])
@unittest.mock.patch.object(BlockchainUtilities, 'submit_transaction')
def test_resubmit_transaction_correct(mock_submit_transaction,
                                      min_adaptable_fee_per_gas,
                                      underpriced_submissions,
                                      blockchain_utilities,
                                      transaction_resubmission_request,
                                      transaction_submission_response):
    mock_submit_transaction.side_effect = (
        [TransactionUnderpricedError] * underpriced_submissions +
        [transaction_submission_response])
    transaction_resubmission_request.min_adaptable_fee_per_gas = \
        min_adaptable_fee_per_gas
    response = blockchain_utilities.resubmit_transaction(
        transaction_resubmission_request)
    assert dataclasses.asdict(response) == dataclasses.asdict(
        transaction_submission_response)
    assert mock_submit_transaction.call_count == underpriced_submissions + 1


@unittest.mock.patch.object(BlockchainUtilities, 'get_error_class',
                            return_value=BlockchainUtilitiesError)
def test_resubmit_transaction_min_adaptable_fee_per_gas_error(
        mock_get_error_class, blockchain_utilities,
        transaction_resubmission_request):
    transaction_resubmission_request.min_adaptable_fee_per_gas = -1
    with pytest.raises(BlockchainUtilitiesError):
        blockchain_utilities.resubmit_transaction(
            transaction_resubmission_request)


@unittest.mock.patch.object(BlockchainUtilities, 'get_error_class',
                            return_value=BlockchainUtilitiesError)
def test_resubmit_transaction_adaptable_fee_increase_factor_error(
        mock_get_error_class, blockchain_utilities,
        transaction_resubmission_request):
    transaction_resubmission_request.adaptable_fee_increase_factor = 1.001
    with pytest.raises(BlockchainUtilitiesError):
        blockchain_utilities.resubmit_transaction(
            transaction_resubmission_request)


@unittest.mock.patch.object(BlockchainUtilities, 'get_error_class',
                            return_value=BlockchainUtilitiesError)
def test_resubmit_transaction_max_total_fee_per_gas_exceeded_error(
        mock_get_error_class, blockchain_utilities,
        transaction_resubmission_request):
    transaction_resubmission_request.max_total_fee_per_gas = \
        transaction_resubmission_request.min_adaptable_fee_per_gas
    with pytest.raises(MaxTotalFeePerGasExceededError):
        blockchain_utilities.resubmit_transaction(
            transaction_resubmission_request)


@pytest.mark.parametrize('initial_submission_underpriced', [False, True])
@unittest.mock.patch(
    'pantos.common.blockchains.tasks.create_transaction_resubmission_task',
    return_value=uuid.uuid4())
@unittest.mock.patch.object(BlockchainUtilities, 'resubmit_transaction')
@unittest.mock.patch.object(BlockchainUtilities, 'submit_transaction')
def test_start_transaction_submission_correct(
        mock_submit_transaction, mock_resubmit_transaction,
        mock_create_transaction_resubmission_task,
        initial_submission_underpriced, blockchain_utilities,
        transaction_submission_start_request, transaction_submission_response,
        transaction_resubmission_response):
    mock_submit_transaction.side_effect = [
        TransactionUnderpricedError
        if initial_submission_underpriced else transaction_submission_response
    ]
    mock_resubmit_transaction.return_value = transaction_resubmission_response
    internal_transaction_id = \
        blockchain_utilities.start_transaction_submission(
            transaction_submission_start_request)
    assert (internal_transaction_id ==
            mock_create_transaction_resubmission_task.return_value)
    assert mock_submit_transaction.call_count == 1
    assert mock_resubmit_transaction.call_count == (
        1 if initial_submission_underpriced else 0)
    assert mock_create_transaction_resubmission_task.call_count == 1


@unittest.mock.patch.object(BlockchainUtilities, 'get_error_class',
                            return_value=BlockchainUtilitiesError)
def test_start_transaction_submission_celery_tasks_disabled_error(
        mock_get_error_class, blockchain_utilities,
        transaction_submission_start_request):
    blockchain_utilities._celery_tasks_enabled = False
    with pytest.raises(BlockchainUtilitiesError):
        blockchain_utilities.start_transaction_submission(
            transaction_submission_start_request)


@unittest.mock.patch.object(BlockchainUtilities, 'get_error_class',
                            return_value=BlockchainUtilitiesError)
def test_start_transaction_submission_blocks_until_resubmission_error(
        mock_get_error_class, blockchain_utilities,
        transaction_submission_start_request):
    transaction_submission_start_request.blocks_until_resubmission = 0
    with pytest.raises(BlockchainUtilitiesError):
        blockchain_utilities.start_transaction_submission(
            transaction_submission_start_request)


@unittest.mock.patch.object(BlockchainUtilities, 'get_error_class',
                            return_value=BlockchainUtilitiesError)
def test_start_transaction_submission_adaptable_fee_increase_factor_error(
        mock_get_error_class, blockchain_utilities,
        transaction_submission_start_request):
    transaction_submission_start_request.adaptable_fee_increase_factor = 1.001
    with pytest.raises(BlockchainUtilitiesError):
        blockchain_utilities.start_transaction_submission(
            transaction_submission_start_request)


@unittest.mock.patch(
    'pantos.common.blockchains.tasks.create_transaction_resubmission_task',
    side_effect=Exception)
@unittest.mock.patch.object(BlockchainUtilities, 'submit_transaction')
@unittest.mock.patch.object(BlockchainUtilities, 'get_error_class',
                            return_value=BlockchainUtilitiesError)
def test_start_transaction_submission_transaction_resubmission_task_error(
        mock_get_error_class, mock_submit_transaction,
        mock_create_transaction_resubmission_task, blockchain_utilities,
        transaction_submission_start_request, transaction_submission_response):
    mock_submit_transaction.return_value = transaction_submission_response
    with pytest.raises(BlockchainUtilitiesError):
        blockchain_utilities.start_transaction_submission(
            transaction_submission_start_request)


@pytest.mark.parametrize('task_result', [
    None,
    (TransactionStatus.CONFIRMED,
     '0xdf6fca0130714b5496fe9f0dbf6991ca996f2a387e6698707f825f98f8725e1c')
])
@unittest.mock.patch(
    'pantos.common.blockchains.tasks.get_transaction_resubmission_task_result')
def test_get_transaction_submission_status_correct(
        mock_get_transaction_resubmission_task_result, task_result,
        blockchain_utilities, internal_transaction_id):
    mock_get_transaction_resubmission_task_result.return_value = task_result
    response = blockchain_utilities.get_transaction_submission_status(
        internal_transaction_id)
    if task_result is None:
        assert not response.transaction_submission_completed
    else:
        assert response.transaction_submission_completed
        assert response.transaction_status is task_result[0]
        assert response.transaction_id == task_result[1]
    assert mock_get_transaction_resubmission_task_result.call_count == 1


@unittest.mock.patch.object(BlockchainUtilities, 'get_error_class',
                            return_value=BlockchainUtilitiesError)
def test_get_transaction_submission_status_celery_tasks_disabled_error(
        mock_get_error_class, blockchain_utilities, internal_transaction_id):
    blockchain_utilities._celery_tasks_enabled = False
    with pytest.raises(BlockchainUtilitiesError):
        blockchain_utilities.get_transaction_submission_status(
            internal_transaction_id)


@unittest.mock.patch(
    'pantos.common.blockchains.tasks.get_transaction_resubmission_task_result',
    side_effect=Exception)
@unittest.mock.patch.object(BlockchainUtilities, 'get_error_class',
                            return_value=BlockchainUtilitiesError)
def test_get_transaction_submission_status_transaction_resubmission_task_error(
        mock_get_error_class, mock_get_transaction_resubmission_task_result,
        blockchain_utilities, internal_transaction_id):
    with pytest.raises(BlockchainUtilitiesError):
        blockchain_utilities.get_transaction_submission_status(
            internal_transaction_id)


def test_add_node_connections_correct():
    mock_connection = unittest.mock.Mock()
    node_connections = NodeConnections()

    node_connections.add_node_connection(mock_connection)
    node_connections.add_node_connection(mock_connection)

    assert node_connections._NodeConnections__node_connections == [
        mock_connection, mock_connection
    ]


def test_getattr_with_no_connections_error():
    node_connections = NodeConnections()

    with pytest.raises(NodeConnectionError):
        node_connections.attribute


def test_getattr_with_valid_connection_correct():
    mock_connection = unittest.mock.Mock()
    node_connections = NodeConnections()
    node_connections.add_node_connection(mock_connection)

    assert isinstance(node_connections.attribute, NodeConnections.Wrapper)


def test_call_non_transaction_function_correct():
    mock_connection = unittest.mock.Mock()
    node_connections = NodeConnections()
    node_connections.add_node_connection(mock_connection)
    wrapper = node_connections.eth.get_balance

    assert not wrapper._Wrapper__is_transaction_function


def test_call_transaction_function():
    mock_connection = unittest.mock.Mock()
    node_connections = NodeConnections(['send_transaction'])
    node_connections.add_node_connection(mock_connection)
    wrapper = node_connections.eth.send_transaction
    result = wrapper()

    assert wrapper._Wrapper__is_transaction_function
    assert result == wrapper._Wrapper__objects[0]()


def test_get_wrapper_attribute_result_correct():
    mock_connection = unittest.mock.Mock()
    mock_connection.eth.get_gas = 100
    node_connections = NodeConnections()
    node_connections.add_node_connection(mock_connection)
    result = node_connections.eth.get_gas.get()

    assert result == 100


def test_get_item_correct():
    mock_connection = unittest.mock.Mock()
    mock_connection.accounts = ['account']
    node_connections = NodeConnections()
    node_connections.add_node_connection(mock_connection)

    account_wrapped = node_connections.accounts[0]

    assert account_wrapped._Wrapper__objects[0] == 'account'


def test_compare_results_matching_correct():
    mock_connection = unittest.mock.Mock()
    mock_connection.get_balance.return_value = 10
    node_connections = NodeConnections()
    node_connections.add_node_connection(mock_connection)
    node_connections.add_node_connection(mock_connection)

    balance = node_connections.get_balance().get()

    assert balance == 10


def test_compare_results_not_matching_error():
    mock_connection = unittest.mock.Mock()
    mock_connection_2 = unittest.mock.Mock()
    mock_connection.get_balance.return_value = 10
    mock_connection_2.get_balance.return_value = 15
    node_connections = NodeConnections()
    node_connections.add_node_connection(mock_connection)
    node_connections.add_node_connection(mock_connection_2)

    with pytest.raises(ResultsNotMatchingError):
        node_connections.get_balance().get()


def test_get_minimum_result_correct():
    mock_connection = unittest.mock.Mock()
    mock_connection_2 = unittest.mock.Mock()
    mock_connection.get_block_number.return_value = 10
    mock_connection_2.get_block_number.return_value = 11
    node_connections = NodeConnections()
    node_connections.add_node_connection(mock_connection)
    node_connections.add_node_connection(mock_connection_2)

    assert node_connections.get_block_number().get_minimum_result() == 10

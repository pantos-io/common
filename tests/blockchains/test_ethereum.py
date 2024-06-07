import importlib.resources
import unittest.mock

import hexbytes
import pytest
import web3
import web3.exceptions

from pantos.common.blockchains.base import NodeConnections
from pantos.common.blockchains.base import ResultsNotMatchingError
from pantos.common.blockchains.base import TransactionNonceTooLowError
from pantos.common.blockchains.base import TransactionUnderpricedError
from pantos.common.blockchains.enums import Blockchain
from pantos.common.blockchains.ethereum import _NO_ARCHIVE_NODE_LOG_MESSAGE
from pantos.common.blockchains.ethereum import \
    _NO_ARCHIVE_NODE_RPC_ERROR_MESSAGE
from pantos.common.blockchains.ethereum import _TRANSACTION_METHOD_NAMES
from pantos.common.blockchains.ethereum import EthereumUtilities
from pantos.common.blockchains.ethereum import EthereumUtilitiesError
from pantos.common.entities import TransactionStatus

_CONTRACT_ABI_PACKAGE = 'tests.blockchains.contracts'
"""Package that contains the contract ABI files."""

_ERC20_CONTRACT_ABI = 'ethereum_erc20.abi'
"""File name of the ERC20 token contract ABI."""

_ERC20_CONTRACT_BYTECODE = 'ethereum_erc20.bytecode'
"""File name of the ERC20 token contract bytecode."""


@pytest.fixture(scope='module')
def w3():
    return web3.Web3(web3.EthereumTesterProvider())


@pytest.fixture(scope='module')
def node_connections(w3):
    node_connections = NodeConnections[web3.Web3](_TRANSACTION_METHOD_NAMES)
    node_connections.add_node_connection(w3)
    return node_connections


@pytest.fixture(scope='module')
@unittest.mock.patch.object(EthereumUtilities, 'create_node_connections')
def ethereum_utilities(mock_create_node_connections, blockchain_node_urls,
                       fallback_blockchain_node_urls, average_block_time,
                       required_transaction_confirmations,
                       transaction_network_id, account, node_connections):
    ethereum_utilities = EthereumUtilities(
        blockchain_node_urls, fallback_blockchain_node_urls,
        average_block_time, required_transaction_confirmations,
        transaction_network_id,
        default_private_key=(account.keystore, account.keystore_password),
        celery_tasks_enabled=True)
    mock_create_node_connections.return_value = node_connections
    ethereum_utilities.create_node_connections = mock_create_node_connections
    return ethereum_utilities


@pytest.fixture
def deployed_erc20(w3, node_connections):
    default_account = w3.eth.accounts[0]
    with importlib.resources.open_text(
            _CONTRACT_ABI_PACKAGE, _ERC20_CONTRACT_BYTECODE) as bytecode_file:
        bytecode = bytecode_file.read()
    with importlib.resources.open_text(_CONTRACT_ABI_PACKAGE,
                                       _ERC20_CONTRACT_ABI) as abi_file:
        erc20_abi = abi_file.read()
    erc20_contract = node_connections.eth.contract(abi=erc20_abi,
                                                   bytecode=bytecode)
    tx_hash = erc20_contract.constructor(1000, 'TOK', 2, 'TOK').transact(
        {'from': default_account})
    tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash, 180)
    return erc20_contract(tx_receipt.contractAddress)


def test_get_address(ethereum_utilities, account):
    address = ethereum_utilities.get_address(account.private_key)
    assert address == account.address


def test_get_coin_balance_returns_0_correct(ethereum_utilities, account):
    assert ethereum_utilities.get_balance(account.address) == 0


def test_get_coin_balance_returns_1000000_correct(ethereum_utilities, w3):
    balance = ethereum_utilities.get_balance(w3.eth.accounts[0])
    assert balance == w3.to_wei(1000000, 'ether')


def test_get_coin_balance_returns_1_correct(ethereum_utilities, account, w3):
    default_account = w3.eth.accounts[0]
    w3.eth.send_transaction({
        'to': account.address,
        'from': default_account,
        'value': w3.to_wei(1, 'ether')
    })
    balance = ethereum_utilities.get_balance(account.address)
    assert balance == w3.to_wei(1, 'ether')


def test_get_token_balance_correct(ethereum_utilities, deployed_erc20, w3):
    default_account = w3.eth.accounts[0]
    balance = ethereum_utilities.get_balance(default_account,
                                             deployed_erc20.address.get())
    assert balance == 1000


def test_get_token_balance_wrong_address_raises_error(ethereum_utilities, w3):
    default_account = w3.eth.accounts[0]
    with pytest.raises(EthereumUtilitiesError):
        ethereum_utilities.get_balance(default_account, '0x0')


def test_get_coin_balance_wrong_address_raises_error(ethereum_utilities):
    with pytest.raises(EthereumUtilitiesError):
        ethereum_utilities.get_balance('0x0')


def test_get_coin_balance_error(ethereum_utilities, w3):
    default_account = w3.eth.accounts[0]
    mocked_node_connections = unittest.mock.Mock()
    mocked_node_connections.eth.get_balance.side_effect = \
        Exception

    with pytest.raises(EthereumUtilitiesError):
        ethereum_utilities.get_balance(
            default_account, node_connections=mocked_node_connections)


def test_get_coin_balance_results_not_matching_error(ethereum_utilities, w3):
    default_account = w3.eth.accounts[0]
    mocked_node_connections = unittest.mock.Mock()
    mocked_node_connections.eth.get_balance.side_effect = \
        ResultsNotMatchingError

    with pytest.raises(ResultsNotMatchingError):
        ethereum_utilities.get_balance(
            default_account, node_connections=mocked_node_connections)


@unittest.mock.patch.object(EthereumUtilities, 'create_contract')
def test_get_token_balance_error(mocked_create_contract, ethereum_utilities,
                                 node_connections, deployed_erc20):
    mocked_contract = unittest.mock.Mock()
    mocked_contract.functions.balanceOf.side_effect = Exception
    default_account = node_connections.eth.accounts[0]
    mocked_create_contract.return_value = mocked_contract

    with pytest.raises(EthereumUtilitiesError):
        ethereum_utilities.get_balance(default_account,
                                       deployed_erc20.address.get(),
                                       node_connections)


@unittest.mock.patch.object(EthereumUtilities, 'create_contract')
def test_get_token_results_not_matching_error(mocked_create_contract,
                                              ethereum_utilities, w3,
                                              deployed_erc20):
    mocked_contract = unittest.mock.Mock()
    mocked_contract.functions.balanceOf.side_effect = ResultsNotMatchingError
    default_account = w3.eth.accounts[0]
    mocked_create_contract.return_value = mocked_contract

    with pytest.raises(ResultsNotMatchingError):
        ethereum_utilities.get_balance(default_account,
                                       deployed_erc20.address.get())


def test_get_logs_correct(ethereum_utilities, deployed_erc20):
    transfer_event = deployed_erc20.events.Transfer()
    assert ethereum_utilities.get_logs(transfer_event, 0, 0) == ()


def test_get_logs_error(ethereum_utilities, deployed_erc20):
    transfer_event = deployed_erc20.events.Transfer()
    with pytest.raises(Exception):
        ethereum_utilities.get_logs(transfer_event, 0, 1000)


def test_is_valid_address(ethereum_utilities):
    # Valid Ethereum checksum addresses
    assert ethereum_utilities.is_valid_address(
        '0x2F64230f0AFFCA54563958caF89c9710f132cFe3')
    assert ethereum_utilities.is_valid_address(
        '0x5bD723CdfDa91B63aF3ff6BeC26443D5805a478B')
    assert ethereum_utilities.is_valid_address(
        '0x8C6C886E27477Fcb722c9b25225a99239309eF40')
    # Invalid Ethereum checksum addresses
    assert not ethereum_utilities.is_valid_address(
        '0x2f64230f0affca54563958caf89c9710f132cfe3')
    assert not ethereum_utilities.is_valid_address(
        '0x5bd723cdfda91b63af3ff6bec26443d5805a478b')
    assert not ethereum_utilities.is_valid_address(
        '0x8c6c886e27477fcb722c9b25225a99239309ef40')
    assert not ethereum_utilities.is_valid_address(None)
    assert not ethereum_utilities.is_valid_address(0)
    assert not ethereum_utilities.is_valid_address(1)
    assert not ethereum_utilities.is_valid_address('')
    assert not ethereum_utilities.is_valid_address(' ')


def test_get_transaction_method_names_correct(ethereum_utilities):
    web3_transaction_method_name = \
        ethereum_utilities._get_transaction_method_names()

    assert web3_transaction_method_name == [
        'send_transaction', 'replace_transaction', 'modify_transaction',
        'send_raw_transaction', 'transact'
    ]


def test_is_equal_address(ethereum_utilities):
    address = '0x2F64230f0AFFCA54563958caF89c9710f132cFe3'
    assert ethereum_utilities.is_equal_address(address, address) is True
    assert ethereum_utilities.is_equal_address(address.lower(), address) \
        is True
    assert ethereum_utilities.is_equal_address(address, address.lower()) \
        is True
    assert ethereum_utilities.is_equal_address(address.lower(),
                                               address.lower()) is True


def test_decrypt_private_encrypted_key(ethereum_utilities, account):
    with open(account.keystore_path, 'r') as file:
        private_key = ethereum_utilities.decrypt_private_key(
            file.read(), account.keystore_password)
        assert private_key == account.private_key


def test_get_blockchain_correct(ethereum_utilities):
    assert ethereum_utilities.get_blockchain() is Blockchain.ETHEREUM
    assert EthereumUtilities.get_blockchain() is Blockchain.ETHEREUM


def test_get_error_class_correct(ethereum_utilities):
    assert ethereum_utilities.get_error_class() is EthereumUtilitiesError
    assert EthereumUtilities.get_error_class() is EthereumUtilitiesError


@unittest.mock.patch.object(EthereumUtilities,
                            '_EthereumUtilities__retrieve_revert_message',
                            return_value='revert message')
@pytest.mark.parametrize('transaction_parameters',
                         [(980, 1, TransactionStatus.CONFIRMED),
                          (990, 1, TransactionStatus.UNCONFIRMED),
                          (None, 1, TransactionStatus.UNINCLUDED),
                          (980, 0, TransactionStatus.REVERTED),
                          (990, 0, TransactionStatus.UNCONFIRMED),
                          (None, 0, TransactionStatus.UNINCLUDED)])
def test_read_transaction_status_correct(mocked_retrieve_revert_message,
                                         transaction_parameters,
                                         ethereum_utilities, node_connections,
                                         w3, transaction_id):
    mock_transaction_receipt = {
        'transactionHash': hexbytes.HexBytes(transaction_id),
        'blockNumber': transaction_parameters[0],
        'status': transaction_parameters[1]
    }
    with unittest.mock.patch.object(w3.eth, 'get_transaction_receipt',
                                    return_value=mock_transaction_receipt):
        with unittest.mock.patch.object(w3.eth, 'get_block_number',
                                        return_value=1000):
            transaction_status = ethereum_utilities.read_transaction_status(
                transaction_id, node_connections)
    assert transaction_status is transaction_parameters[2]


def test_read_transaction_status_transaction_not_found_correct(
        ethereum_utilities, node_connections, transaction_id):
    with unittest.mock.patch.object(
            node_connections.eth, 'get_transaction_receipt',
            side_effect=web3.exceptions.TransactionNotFound):
        transaction_status = ethereum_utilities.read_transaction_status(
            transaction_id)
    assert transaction_status is TransactionStatus.UNINCLUDED


def test_read_transaction_status_error(ethereum_utilities, w3, transaction_id):
    with unittest.mock.patch.object(w3.eth, 'get_transaction_receipt',
                                    side_effect=Exception):
        with pytest.raises(EthereumUtilitiesError) as exception_info:
            ethereum_utilities.read_transaction_status(transaction_id)
    assert exception_info.value.details['transaction_id'] == transaction_id


def test_read_transaction_status_results_not_matching_error(
        ethereum_utilities, w3, transaction_id):
    with unittest.mock.patch.object(w3.eth, 'get_transaction_receipt',
                                    side_effect=ResultsNotMatchingError):
        with pytest.raises(ResultsNotMatchingError):
            ethereum_utilities.read_transaction_status(transaction_id)


@pytest.mark.parametrize('type_2_transaction', [True, False])
@unittest.mock.patch.object(EthereumUtilities,
                            '_type_2_transactions_supported')
@unittest.mock.patch.object(EthereumUtilities, 'create_contract')
def test_submit_transaction_correct(mock_create_contract,
                                    mock_type_2_transactions_supported,
                                    type_2_transaction, ethereum_utilities, w3,
                                    transaction_submission_request,
                                    transaction_id):
    mock_type_2_transactions_supported.return_value = type_2_transaction
    with unittest.mock.patch(
            'pantos.common.blockchains.ethereum.web3.Account.sign_transaction'
    ):
        with unittest.mock.patch.object(
                w3.eth, 'get_block', return_value={'baseFeePerGas': int(1e8)}):
            with unittest.mock.patch.object(
                    w3.eth,
                    'send_raw_transaction') as mock_send_raw_transaction:
                mock_send_raw_transaction().hex.return_value = \
                    transaction_id
                response = ethereum_utilities.submit_transaction(
                    transaction_submission_request)
    assert response.transaction_id == transaction_id


def test_submit_transaction_default_private_key_error(
        ethereum_utilities, transaction_submission_request):
    with unittest.mock.patch.object(ethereum_utilities, '_default_private_key',
                                    None):
        with pytest.raises(EthereumUtilitiesError):
            ethereum_utilities.submit_transaction(
                transaction_submission_request)


def test_submit_transaction_gas_error(ethereum_utilities,
                                      transaction_submission_request):
    transaction_submission_request.gas = 1000
    with pytest.raises(EthereumUtilitiesError):
        ethereum_utilities.submit_transaction(transaction_submission_request)


def test_submit_transaction_min_adaptable_fee_per_gas_error(
        ethereum_utilities, transaction_submission_request):
    transaction_submission_request.min_adaptable_fee_per_gas = -1
    with pytest.raises(EthereumUtilitiesError):
        ethereum_utilities.submit_transaction(transaction_submission_request)


def test_submit_transaction_max_total_fee_per_gas_error(
        ethereum_utilities, transaction_submission_request):
    transaction_submission_request.max_total_fee_per_gas = \
        transaction_submission_request.min_adaptable_fee_per_gas - 1
    with pytest.raises(EthereumUtilitiesError):
        ethereum_utilities.submit_transaction(transaction_submission_request)


def test_submit_transaction_amount_error(ethereum_utilities,
                                         transaction_submission_request):
    transaction_submission_request.amount = -1
    with pytest.raises(EthereumUtilitiesError):
        ethereum_utilities.submit_transaction(transaction_submission_request)


def test_submit_transaction_nonce_error(ethereum_utilities,
                                        transaction_submission_request):
    transaction_submission_request.nonce = -1
    with pytest.raises(EthereumUtilitiesError):
        ethereum_utilities.submit_transaction(transaction_submission_request)


@unittest.mock.patch.object(EthereumUtilities, 'create_contract')
def test_submit_transaction_max_fee_per_gas_error(
        mock_create_contract, ethereum_utilities, w3,
        transaction_submission_request, transaction_id):
    base_fee_per_gas = int(1e8)
    transaction_submission_request.max_total_fee_per_gas = (
        base_fee_per_gas +
        transaction_submission_request.min_adaptable_fee_per_gas)
    with unittest.mock.patch(
            'pantos.common.blockchains.ethereum.web3.Account.sign_transaction'
    ):
        with unittest.mock.patch.object(
                w3.eth, 'get_block',
                return_value={'baseFeePerGas': base_fee_per_gas}):
            with pytest.raises(EthereumUtilitiesError):
                ethereum_utilities.submit_transaction(
                    transaction_submission_request)


@unittest.mock.patch.object(EthereumUtilities,
                            '_type_2_transactions_supported',
                            return_value=False)
@unittest.mock.patch.object(EthereumUtilities, 'create_contract')
def test_submit_transaction_gas_price__error(
        mock_create_contract, mock_type_2_transactions_supported,
        ethereum_utilities, w3, transaction_submission_request,
        transaction_id):
    transaction_submission_request.min_adaptable_fee_per_gas = 1
    transaction_submission_request.max_total_fee_per_gas = 1
    with unittest.mock.patch(
            'pantos.common.blockchains.ethereum.web3.Account.sign_transaction'
    ):
        with pytest.raises(EthereumUtilitiesError):
            ethereum_utilities.submit_transaction(
                transaction_submission_request)


@unittest.mock.patch.object(EthereumUtilities, 'create_contract')
def test_submit_transaction_nonce_too_low_error(
        mock_create_contract, ethereum_utilities, w3,
        transaction_submission_request):
    with unittest.mock.patch(
            'pantos.common.blockchains.ethereum.web3.Account.sign_transaction'
    ):
        with unittest.mock.patch.object(
                w3.eth, 'send_raw_transaction', side_effect=ValueError({
                    'code': '-32000',
                    'message': 'nonce too low'
                })):
            with pytest.raises(TransactionNonceTooLowError):
                ethereum_utilities.submit_transaction(
                    transaction_submission_request)


@unittest.mock.patch.object(EthereumUtilities, 'create_contract')
def test_submit_transaction_underpriced_error(mock_create_contract,
                                              ethereum_utilities, w3,
                                              transaction_submission_request):
    with unittest.mock.patch(
            'pantos.common.blockchains.ethereum.web3.Account.sign_transaction'
    ):
        with unittest.mock.patch.object(
                w3.eth, 'send_raw_transaction', side_effect=ValueError({
                    'code': '-32000',
                    'message': 'transaction underpriced'
                })):
            with pytest.raises(TransactionUnderpricedError):
                ethereum_utilities.submit_transaction(
                    transaction_submission_request)


@unittest.mock.patch.object(EthereumUtilities, 'create_contract')
def test_submit_transaction_other_send_error(mock_create_contract,
                                             ethereum_utilities, w3,
                                             transaction_submission_request):
    with unittest.mock.patch(
            'pantos.common.blockchains.ethereum.web3.Account.sign_transaction'
    ):
        with unittest.mock.patch.object(w3.eth, 'send_raw_transaction',
                                        side_effect=ValueError('some error')):
            with pytest.raises(EthereumUtilitiesError):
                ethereum_utilities.submit_transaction(
                    transaction_submission_request)


@unittest.mock.patch.object(EthereumUtilities, 'create_contract')
def test_submit_transaction_results_not_matching_error(
        mock_create_contract, ethereum_utilities, w3,
        transaction_submission_request):
    with unittest.mock.patch(
            'pantos.common.blockchains.ethereum.web3.Account.sign_transaction'
    ):
        with unittest.mock.patch.object(w3.eth, 'send_raw_transaction',
                                        side_effect=ResultsNotMatchingError):
            with pytest.raises(ResultsNotMatchingError):
                ethereum_utilities.submit_transaction(
                    transaction_submission_request)


@unittest.mock.patch('pantos.common.blockchains.ethereum.web3')
def test_create_single_node_connection_correct(mocked_web3, ethereum_utilities,
                                               blockchain_node_urls):
    blockchain_node_url = blockchain_node_urls[0]

    result = ethereum_utilities._create_single_node_connection(
        blockchain_node_url)

    assert result == mocked_web3.Web3(
        mocked_web3.Web3.HTTPProvider(blockchain_node_url))


@unittest.mock.patch('pantos.common.blockchains.ethereum.web3')
def test_create_single_node_connection_extra_data_lenght_correct(
        mocked_web3, ethereum_utilities, blockchain_node_urls):
    mocked_web3.exceptions.ExtraDataLengthError = \
        web3.exceptions.ExtraDataLengthError
    blockchain_node_url = blockchain_node_urls[0]
    mocked_web3.Web3().is_connected.return_value = True
    mocked_web3.Web3(
    ).eth.get_block.side_effect = web3.exceptions.ExtraDataLengthError

    result = ethereum_utilities._create_single_node_connection(
        blockchain_node_url)

    assert result == mocked_web3.Web3(
        mocked_web3.Web3.HTTPProvider(blockchain_node_url))
    mocked_web3.Web3().middleware_onion.inject.assert_called_once_with(
        mocked_web3.middleware.geth_poa_middleware, layer=0)


@unittest.mock.patch('pantos.common.blockchains.ethereum.web3')
def test_create_single_node_connection_error(mocked_web3, blockchain_node_urls,
                                             ethereum_utilities):
    blockchain_node_url = blockchain_node_urls[0]
    mocked_web3.Web3.side_effect = Exception

    with pytest.raises(EthereumUtilitiesError):
        ethereum_utilities._create_single_node_connection(blockchain_node_url)


@unittest.mock.patch('pantos.common.blockchains.ethereum.web3')
def test_create_single_node_connection_not_connected_error(
        mocked_web3, blockchain_node_urls, ethereum_utilities):
    blockchain_node_url = blockchain_node_urls[0]
    mocked_web3.Web3().is_connected.return_value = False

    with pytest.raises(EthereumUtilitiesError):
        ethereum_utilities._create_single_node_connection(blockchain_node_url)


def test_retrieve_revert_message_correct(ethereum_utilities, w3,
                                         node_connections, transaction_id,
                                         transaction_contract_address):
    default_account = w3.eth.accounts[0]
    with unittest.mock.patch.object(
            w3.eth, 'get_transaction', return_value={
                'from': default_account,
                'to': transaction_contract_address,
                'value': 0,
                'input': "",
                'blockNumber': 1,
            }):
        with unittest.mock.patch.object(
                w3.eth, 'call', side_effect=web3.exceptions.ContractLogicError(
                    'revert message')):
            assert \
                ethereum_utilities._EthereumUtilities__retrieve_revert_message(
                    transaction_id, node_connections) == 'revert message'


def test_retrieve_revert_message_no_archive_node_available_error(
        ethereum_utilities, w3, node_connections, transaction_id,
        transaction_contract_address):
    default_account = w3.eth.accounts[0]
    with unittest.mock.patch.object(
            w3.eth, 'get_transaction', return_value={
                'from': default_account,
                'to': transaction_contract_address,
                'value': 0,
                'input': "",
                'blockNumber': 1,
            }):
        with unittest.mock.patch.object(
                w3.eth, 'call', side_effect=ValueError({
                    'message': f'{_NO_ARCHIVE_NODE_RPC_ERROR_MESSAGE} 0x...'
                })):
            assert \
                ethereum_utilities._EthereumUtilities__retrieve_revert_message(
                    transaction_id, node_connections) == \
                f'unknown {_NO_ARCHIVE_NODE_LOG_MESSAGE}'


def test_retrieve_revert_message_correct_no_error(
        ethereum_utilities, w3, node_connections, transaction_id,
        transaction_contract_address):
    default_account = w3.eth.accounts[0]
    with unittest.mock.patch.object(
            w3.eth, 'get_transaction', return_value={
                'from': default_account,
                'to': transaction_contract_address,
                'value': 0,
                'input': "",
                'blockNumber': 1,
            }):
        with unittest.mock.patch.object(w3.eth, 'call', return_value=''):
            assert \
                ethereum_utilities._EthereumUtilities__retrieve_revert_message(
                    transaction_id, node_connections) == 'unknown'


def test_retrieve_revert_message_correct_error(ethereum_utilities, w3,
                                               node_connections,
                                               transaction_id,
                                               transaction_contract_address):
    default_account = w3.eth.accounts[0]
    with unittest.mock.patch.object(
            w3.eth, 'get_transaction', return_value={
                'from': default_account,
                'to': transaction_contract_address,
                'value': 0,
                'input': "",
                'blockNumber': 1,
            }):
        with unittest.mock.patch.object(w3.eth, 'call', side_effect=Exception):
            assert \
                ethereum_utilities._EthereumUtilities__retrieve_revert_message(
                    transaction_id, node_connections) == 'unknown'

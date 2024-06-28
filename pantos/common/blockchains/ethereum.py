"""Module for Ethereum-specific utilities and errors.

"""
import logging
import typing
import urllib.parse

import semantic_version  # type: ignore
import web3
import web3.contract.contract
import web3.exceptions
import web3.middleware
import web3.types

from pantos.common.blockchains.base import GENERAL_RPC_ERROR_MESSAGE
from pantos.common.blockchains.base import BlockchainUtilities
from pantos.common.blockchains.base import BlockchainUtilitiesError
from pantos.common.blockchains.base import NodeConnections
from pantos.common.blockchains.base import ResultsNotMatchingError
from pantos.common.blockchains.base import SingleNodeConnectionError
from pantos.common.blockchains.base import UnhealthyNode
from pantos.common.blockchains.base import VersionedContractAbi
from pantos.common.blockchains.enums import Blockchain
from pantos.common.blockchains.enums import ContractAbi
from pantos.common.entities import TransactionStatus
from pantos.common.types import BlockchainAddress

_NONCE_TOO_LOW = ['nonce too low', 'invalid nonce', 'ERR_INCORRECT_NONCE']
"""Possible nonce too low error messages."""

_TRANSACTION_METHOD_NAMES = [
    'send_transaction', 'replace_transaction', 'modify_transaction',
    'send_raw_transaction', 'transact'
]
"""The names of methods of the blockchain interactor object which
send transactions."""

_NO_ARCHIVE_NODE_RPC_ERROR_MESSAGE = 'missing trie node'

_NO_ARCHIVE_NODE_LOG_MESSAGE = 'due to the absence of an archive node'

_logger = logging.getLogger(__name__)


class EthereumUtilitiesError(BlockchainUtilitiesError):
    """Exception class for all Ethereum utilities errors.

    """
    pass


class EthereumUtilities(BlockchainUtilities):
    """Class for Ethereum-specific utilities.

    """
    def __init__(self, blockchain_node_urls: list[str],
                 fallback_blockchain_node_urls: list[str],
                 average_block_time: int,
                 required_transaction_confirmations: int,
                 transaction_network_id: typing.Optional[int],
                 default_private_key: typing.Optional[tuple[str, str]] = None,
                 celery_tasks_enabled: bool = False):
        # Docstring inherited
        if transaction_network_id is None:
            raise self._create_error(
                'transaction network ID (chain ID) must be given')
        super().__init__(blockchain_node_urls, fallback_blockchain_node_urls,
                         average_block_time,
                         required_transaction_confirmations,
                         transaction_network_id,
                         default_private_key=default_private_key,
                         celery_tasks_enabled=celery_tasks_enabled)

    def create_node_connections(
            self,
            timeout: typing.Optional[typing.Union[float, tuple]] = None) \
            -> NodeConnections[web3.Web3]:
        # Docstring inherited
        return super().create_node_connections(timeout)

    def create_contract(
            self, contract_address: BlockchainAddress,
            versioned_contract_abi: VersionedContractAbi,
            node_connections: typing.Optional[NodeConnections] = None) \
            -> NodeConnections.Wrapper[web3.contract.Contract]:
        """Create a contract instance.

        Parameters
        ----------
        contract_address : BlockchainAddress
            The address of the contract.
        versioned_contract_abi : VersionedContractAbi
            The version and the contract ABI to load.
        w3 : web3.Web3, optional
            The Web3 instance to use.

        Returns
        -------
        NodeConnections.Wrapper[web3.contract.Contract]
            The wrapper instance over the contract object.

        Raises
        ------
        EthereumUtilitiesError
            If the contract instance cannot be created.

        """
        if not self.is_valid_address(contract_address):
            raise self._create_error('invalid contract address',
                                     contract_address=contract_address)
        node_connections = self.__get_node_connections(node_connections)
        try:
            return node_connections.eth.contract(
                address=typing.cast(web3.types.ChecksumAddress,
                                    contract_address),
                abi=self.load_contract_abi(versioned_contract_abi))
        except Exception:
            raise self._create_error(
                'unable to create a contract instance',
                contract_address=contract_address,
                contract_abi=versioned_contract_abi.contract_abi,
                version=versioned_contract_abi.version)

    def get_address(self, private_key: str) -> str:
        # Docstring inherited
        try:
            return web3.Account.from_key(private_key).address
        except Exception:
            raise self._create_error(
                'cannot determine the address from a private key')

    def get_balance(
            self, account_address: str,
            token_address: typing.Optional[str] = None,
            node_connections: typing.Optional[NodeConnections] = None) -> int:
        # Docstring inherited
        if not self.is_valid_address(account_address):
            raise self._create_error('invalid account address')
        node_connections = self.__get_node_connections(node_connections)
        if token_address is None:
            try:
                return node_connections.eth.get_balance(
                    typing.cast(web3.types.ChecksumAddress,
                                account_address)).get()
            except ResultsNotMatchingError:
                raise
            except Exception:
                raise self._create_error('cannot determine balance')
        else:
            versioned_contract_abi = VersionedContractAbi(
                ContractAbi.STANDARD_TOKEN, semantic_version.Version('1.0.0'))
            if not self.is_valid_address(token_address):
                raise self._create_error('invalid token address')
            erc20_contract = self.create_contract(
                BlockchainAddress(token_address), versioned_contract_abi,
                node_connections)
            try:
                return erc20_contract.functions.\
                    balanceOf(account_address).call().get()
            except ResultsNotMatchingError:
                raise
            except Exception:
                raise self._create_error("cannot call the contract")

    @classmethod
    def get_blockchain(cls) -> Blockchain:
        # Docstring inherited
        return Blockchain.ETHEREUM

    @classmethod
    def get_error_class(cls) -> type[BlockchainUtilitiesError]:
        # Docstring inherited
        return EthereumUtilitiesError

    def get_logs(
            self,
            event: NodeConnections.Wrapper[
                web3.contract.contract.ContractEvent],
            from_block_number: int, to_block_number: int) \
            -> typing.List[web3.types.EventData]:
        """Retrieves the logs of a contract event from a block range.

        Parameters
        ----------
        event : NodeConnections.Wrapper[
                    web3.contract.contract.ContractEvent]
            The instance of the wrapper over the contract event,
            used for retrieving the associated logs.
        from_block_number : int
            The block number to start the search from.
        to_block_number : int
            The block number to end the search at.

        Returns
        -------
        list of web3.types.EventData
            The logs of the contract event.

        Raises
        ------
        ResultsNotMatchingError
            If the results given by the configured blockchain
            nodes do not match.
        BlockchainUtilitiesError
            If the balance cannot be fetched.

        """
        try:
            # Query all events of the contract event.address between the two
            # specified block numbers
            logs = event.get_logs(fromBlock=from_block_number,
                                  toBlock=to_block_number, argument_filters={
                                      'address': event.address
                                  }).get()
            return logs
        except ResultsNotMatchingError:
            raise
        except Exception:
            assert event is not None
            raise self._create_error(
                'cannot process the "{}" event logs of the contract with the '
                'address "{}"'.format(event.event_name, event.address))

    def is_valid_address(self, address: str) -> bool:
        # Docstring inherited
        return web3.Web3.is_checksum_address(address)

    def is_equal_address(self, address_one: str, address_two: str) -> bool:
        # Docstring inherited
        return address_one.lower() == address_two.lower()

    def get_unhealthy_nodes(
            self, blockchain_nodes: list[str],
            timeout: float | tuple | None = None) -> list[UnhealthyNode]:
        # Docstring inherited
        unhealthy_nodes = []
        for blockchain_node in blockchain_nodes:
            try:
                self._create_single_node_connection(blockchain_node, timeout)
            except SingleNodeConnectionError:
                unhealthy_nodes.append(
                    UnhealthyNode(
                        urllib.parse.urlparse(blockchain_node).netloc,
                        GENERAL_RPC_ERROR_MESSAGE))
        return unhealthy_nodes

    def _get_transaction_method_names(self) -> list[str]:
        # Docstring inherited
        return _TRANSACTION_METHOD_NAMES

    def decrypt_private_key(self, encrypted_key: str, password: str) -> str:
        # Docstring inherited
        try:
            private_key = web3.Account.decrypt(encrypted_key, password).hex()
        except Exception:
            raise self._create_error('cannot load the private key')
        # Return the private key hex string without the leading 0x
        assert private_key.startswith('0x')
        return private_key[2:]

    def read_transaction_status(
            self, transaction_id: str,
            node_connections: typing.Optional[NodeConnections] = None) \
            -> TransactionStatus:
        # Docstring inherited
        try:
            node_connections = self.__get_node_connections(node_connections)
            try:
                transaction_receipt = \
                    node_connections.eth.get_transaction_receipt(
                        typing.cast(web3.types.HexStr, transaction_id)).get()
            except web3.exceptions.TransactionNotFound:
                return TransactionStatus.UNINCLUDED
            assert (
                transaction_receipt['transactionHash'].hex() == transaction_id)
            transaction_block_number = transaction_receipt['blockNumber']
            if transaction_block_number is None:
                return TransactionStatus.UNINCLUDED
            current_block_number = \
                node_connections.eth.get_block_number().get_minimum_result()
            confirmations = current_block_number - transaction_block_number
            assert confirmations >= 0
            if confirmations < self.required_transaction_confirmations:
                return TransactionStatus.UNCONFIRMED
            transaction_status = transaction_receipt['status']
            if transaction_status != 1:
                revert_message = self.__retrieve_revert_message(
                    transaction_id, node_connections)
                _logger.info(revert_message, extra=transaction_receipt)
                return TransactionStatus.REVERTED
            return TransactionStatus.CONFIRMED
        except ResultsNotMatchingError:
            raise
        except Exception:
            raise self._create_error(
                'unable to read the status of a transaction',
                transaction_id=transaction_id)

    def submit_transaction(
            self, request: BlockchainUtilities.TransactionSubmissionRequest,
            node_connections: typing.Optional[NodeConnections] = None) \
            -> BlockchainUtilities.TransactionSubmissionResponse:
        # Docstring inherited
        if self._default_private_key is None:
            raise self._create_error('default private key must be available')
        self.__check_transaction_submission_request(request)
        try:
            node_connections = self.__get_node_connections(node_connections)
            transaction_parameters, adaptable_fee_per_gas = \
                self.__create_transaction_parameters(request, node_connections)
            _logger.info('new transaction to be submitted',
                         extra=vars(request) | transaction_parameters)
            contract = self.create_contract(request.contract_address,
                                            request.versioned_contract_abi,
                                            node_connections)
            contract_function = contract.get_function_by_selector(
                request.function_selector)
            transaction = contract_function(
                *request.function_args).build_transaction(
                    transaction_parameters).get()
            signed_transaction = web3.Account.sign_transaction(
                transaction, private_key=self._default_private_key)
            transaction_hash = self.__send_raw_transaction(
                signed_transaction.rawTransaction, node_connections)
            return BlockchainUtilities.TransactionSubmissionResponse(
                transaction_hash, adaptable_fee_per_gas)
        except EthereumUtilitiesError:
            raise
        except ResultsNotMatchingError:
            raise
        except Exception:
            raise self._create_error('unable to submit a transaction',
                                     request=request)

    def _create_single_node_connection(
            self, blockchain_node_url: str,
            timeout: float | tuple | None = None) -> typing.Any:
        # Docstring inherited
        request_kwargs = {'timeout': timeout}
        try:
            w3 = web3.Web3(
                web3.Web3.HTTPProvider(blockchain_node_url,
                                       request_kwargs=request_kwargs))
            if w3.is_connected():
                try:
                    w3.eth.get_block('latest')
                except web3.exceptions.ExtraDataLengthError:
                    w3.middleware_onion.inject(
                        web3.middleware.geth_poa_middleware, layer=0)
                _logger.info(
                    'new blockchain node connection', extra={
                        'blockchain': self.get_blockchain(),
                        'blockchain_node_domain': urllib.parse.urlparse(
                            blockchain_node_url).netloc,
                        'client_version': w3.client_version
                    })
                return w3
        except Exception:
            raise self._create_single_node_connection_error()
        raise self._create_single_node_connection_error()

    def _type_2_transactions_supported(self) -> bool:
        return True  # pragma: no cover

    def __check_transaction_submission_request(
            self, request: BlockchainUtilities.TransactionSubmissionRequest) \
            -> None:
        if request.gas is not None and request.gas < 21000:
            raise self._create_error('gas must be >= 21000', request=request)
        if request.min_adaptable_fee_per_gas < 0:
            raise self._create_error(
                'minimum adaptable fee per gas must be >= 0', request=request)
        if (request.max_total_fee_per_gas is not None
                and request.min_adaptable_fee_per_gas
                > request.max_total_fee_per_gas):
            raise self._create_max_total_fee_per_gas_exceeded_error(
                request=request)
        if request.amount is not None and request.amount < 0:
            raise self._create_error('amount must be >= 0', request=request)
        if request.nonce < 0:
            raise self._create_error('nonce must be >= 0', request=request)

    def __create_transaction_parameters(
            self, request: BlockchainUtilities.TransactionSubmissionRequest,
            node_connections: NodeConnections[web3.Web3]) -> \
            tuple[web3.types.TxParams, int]:
        assert self.transaction_network_id is not None
        assert self._default_address is not None
        transaction_parameters: web3.types.TxParams = {
            'chainId': self.transaction_network_id,
            'from': self._default_address,
            'nonce': web3.types.Nonce(request.nonce)
        }
        if request.gas is not None:
            # If gas is not explicitly specified, it is automatically
            # estimated using w3.eth.estimate_gas()
            transaction_parameters['gas'] = web3.types.Wei(request.gas)
        if request.amount is not None:
            transaction_parameters['value'] = web3.types.Wei(request.amount)
        if self._type_2_transactions_supported():
            # EIP-1559 transaction
            base_fee_per_gas = node_connections.eth.get_block(
                'latest')['baseFeePerGas'].get_minimum_result()
            max_priority_fee_per_gas = request.min_adaptable_fee_per_gas
            max_fee_per_gas = 2 * base_fee_per_gas + max_priority_fee_per_gas
            if (request.max_total_fee_per_gas is not None
                    and request.max_total_fee_per_gas < max_fee_per_gas):
                _logger.warning(
                    f'maximum total fee per gas < {max_fee_per_gas}',
                    extra=vars(request))
                max_fee_per_gas = request.max_total_fee_per_gas
            transaction_parameters['maxPriorityFeePerGas'] = web3.types.Wei(
                max_priority_fee_per_gas)
            transaction_parameters['maxFeePerGas'] = web3.types.Wei(
                max_fee_per_gas)
            adaptable_fee_per_gas = max_priority_fee_per_gas
        else:
            # Legacy type-0 transaction
            gas_price = max(
                node_connections.eth.gas_price.get_minimum_result(),
                request.min_adaptable_fee_per_gas)
            if (request.max_total_fee_per_gas is not None
                    and request.max_total_fee_per_gas < gas_price):
                _logger.warning(f'maximum total fee per gas < {gas_price}',
                                extra=vars(request))
                gas_price = request.max_total_fee_per_gas
            transaction_parameters['gasPrice'] = web3.types.Wei(gas_price)
            adaptable_fee_per_gas = gas_price
        return transaction_parameters, adaptable_fee_per_gas

    def __send_raw_transaction(
            self, raw_transaction: bytes,
            node_connections: NodeConnections[web3.Web3]) -> str:
        try:
            return typing.cast(
                str,
                node_connections.eth.send_raw_transaction(
                    raw_transaction).hex())
        except ValueError as error:
            if any(error_message in str(error)
                   for error_message in _NONCE_TOO_LOW):
                raise self._create_transaction_nonce_too_low_error()
            if 'transaction underpriced' in str(error):
                raise self._create_transaction_underpriced_error()
            raise

    def __get_node_connections(
            self, node_connections: typing.Optional[NodeConnections] = None) \
            -> NodeConnections[web3.Web3]:
        if node_connections is None:
            node_connections = self.create_node_connections()
        return node_connections

    def __retrieve_revert_message(
            self, transaction_hash: str,
            node_connections: NodeConnections[web3.Web3]) -> str:
        revert_message = 'unknown'
        try:
            full_tx = node_connections.eth.get_transaction(
                typing.cast(web3.types.HexStr, transaction_hash)).get()
            replay_tx = {
                'from': full_tx['from'],
                'to': full_tx['to'],
                'value': full_tx['value'],
                'data': full_tx['input']
            }
            context_block_number = full_tx['blockNumber'] - 1
            try:
                node_connections.eth.call(
                    typing.cast(web3.types.TxParams, replay_tx),
                    context_block_number).get()
            except web3.exceptions.ContractLogicError as error:
                revert_message = str(error)
            except ValueError as error:
                if _NO_ARCHIVE_NODE_RPC_ERROR_MESSAGE in error.args[0].get(
                        'message'):
                    revert_message += f' {_NO_ARCHIVE_NODE_LOG_MESSAGE}'
        except Exception:
            _logger.warning('unable to retrieve the revert message',
                            exc_info=True)
        return revert_message

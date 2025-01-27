"""Base module that defines the common class and error interfaces for
all blockchain utilities modules.

"""
import abc
import collections
import copy
import dataclasses
import importlib
import importlib.resources
import inspect
import json
import logging
import math
import pathlib
import pkgutil
import random
import typing
import urllib.parse
import uuid

import semantic_version  # type: ignore

from pantos.common.blockchains.enums import Blockchain
from pantos.common.blockchains.enums import ContractAbi
from pantos.common.entities import TransactionStatus
from pantos.common.exceptions import BaseError
from pantos.common.exceptions import ErrorCreator
from pantos.common.types import BlockchainAddress
from pantos.common.types import ContractFunctionArgs

_BASE_CONTRACT_ABI_PACKAGE = 'pantos.common.blockchains.contracts'

MIN_ADAPTABLE_FEE_INCREASE_FACTOR = 1.101
"""The minimum factor for increasing the adaptable fee per gas in
transaction resubmissions.
"""

GENERAL_RPC_ERROR_MESSAGE = 'unreachable'

H = typing.TypeVar('H', bound='BlockchainHandler')
T = typing.TypeVar('T',
                   bound='BlockchainUtilities.TransactionSubmissionRequest')
N = typing.TypeVar('N')
W = typing.TypeVar('W')

_logger = logging.getLogger(__name__)


class BlockchainUtilitiesError(BaseError):
    """Exception class for all blockchain utilities errors.

    """
    pass


class NodeConnectionError(BaseError):
    """Exception class for all node connection errors.

    """
    pass


class MaxTotalFeePerGasExceededError(BlockchainUtilitiesError):
    """Exception to be raised if the maximum total fee per gas would be
    exceeded for a transaction to be submitted.

    """
    def __init__(self, **kwargs: typing.Any):
        # Docstring inherited
        super().__init__('maximum total fee per gas exceeded', **kwargs)


class TransactionNonceTooLowError(BlockchainUtilitiesError):
    """Exception to be raised if a transaction has been submitted with a
    nonce too low.

    """
    def __init__(self, **kwargs: typing.Any):
        # Docstring inherited
        super().__init__('transaction nonce too low', **kwargs)


class TransactionUnderpricedError(BlockchainUtilitiesError):
    """Exception to be raised if a transaction has been submitted as an
    underpriced transaction.

    """
    def __init__(self, **kwargs: typing.Any):
        # Docstring inherited
        super().__init__('transaction underpriced', **kwargs)


class SingleNodeConnectionError(BlockchainUtilitiesError):
    """Exception to be raised if a blockchain specific node
    connection cannot be established.

    """
    def __init__(self, **kwargs: typing.Any):
        # Docstring inherited
        super().__init__('single node connection error', **kwargs)


class ResultsNotMatchingError(NodeConnectionError):
    """Exception to be raised if the results given by the blockchain
    nodes do not match.

    """
    def __init__(self, **kwargs: typing.Any):
        # Docstring inherited
        super().__init__('results not matching', **kwargs)


class NodeConnections(typing.Generic[N]):
    """Class for managing node connections in a blockchain-agnostic way.

    """
    __node_connections: list[N]
    __transaction_method_names: list[str]

    class Wrapper(typing.Generic[W]):
        """Class for wrapping blockchain interactor objects.

        """
        __is_transaction_function: bool
        __objects: list[typing.Any]
        __transaction_method_names: list[str]

        def __init__(self, objects: list[typing.Any], attr_name: str,
                     transaction_method_names: list[str]):
            """Construct the wrapper instance.

            Parameters
            ----------
            objects : list
                The list of wrapped blockchain interactor objects.
            attr_name : str
                The name of the attribute.
            transaction_method_names : list of str
                The list with method names which are sending
                transactions to the blockchain nodes.

            """
            self.__transaction_method_names = transaction_method_names

            self.__is_transaction_function = (attr_name
                                              in transaction_method_names)

            if self.__is_transaction_function:
                self.__objects = [getattr(objects[0], attr_name)]
            else:
                self.__objects = [
                    getattr(object_, attr_name) for object_ in objects
                ]

        def get(self) -> typing.Any:
            """Get the compared results of wrapped objects. If they
            do not match, then a ResultsNotMatchingError is raised.

            Returns
            -------
            Any
                The matching result of wrapped objects.

            Raises
            ------
            ResultsNotMatchingError
                If the results do not match.

            """
            result = self.__objects[0]
            if not all(result == other_result
                       for other_result in self.__objects[1:]):
                raise ResultsNotMatchingError(
                    **{
                        str(index): result
                        for index, result in enumerate(self.__objects)
                    })
            return result

        def get_minimum_result(self, *args: typing.Any,
                               **kwargs: typing.Any) -> int:
            """Get the minimum result value from the wrapped objects.

            Returns
            -------
            int
                The minimum result of the wrapped objects.

            Raises
            ------
            NodeConnectionError
                If result values are not instances of int.

            """
            self.__check_results_are_instances_of_int()
            return min(self.__objects)

        def get_maximum_result(self, *args: typing.Any,
                               **kwargs: typing.Any) -> int:
            """Get the maximum result value from the wrapped objects.

            Returns
            -------
            int
                The maximum result of the wrapped objects.

            Raises
            ------
            NodeConnectionError
                If result values are not instances of int.

            """
            self.__check_results_are_instances_of_int()
            return max(self.__objects)

        def __check_results_are_instances_of_int(self):
            if not all(isinstance(value, int) for value in self.__objects):
                raise NodeConnectionError('the result values from the wrapped '
                                          'objects must be instances of int')

        def __getattr__(self, attr_name: str) -> 'NodeConnections.Wrapper':
            """Create a new wrapper of the currently wrapped objects
            with the given attribute.

            Parameters
            ----------
            attr_name : str
                The attribute name.

            Returns
            -------
            Wrapper
                Object which wraps the currently wrapped objects
                with the given attribute.

            """
            return NodeConnections.Wrapper(self.__objects, attr_name,
                                           self.__transaction_method_names)

        def __getitem__(self, index: typing.Any) -> 'NodeConnections.Wrapper':
            """Forward the retrieval of the item found at the given
            index to the wrapped objects.

            Parameters
            ----------
            index : int
                The index of the requested item.

            Returns
            -------
            Wrapper
                The wrapper object with the inner wrapped items
                retrieved.

            Raises
            ------
            IndexError
                If the list index is out of range.

            """
            self.__objects = [object_[index] for object_ in self.__objects]
            return self

        def __call__(
                self, *args: typing.Any, **kwargs: typing.Any) -> \
                typing.Union['NodeConnections.Wrapper', typing.Any]:
            """Forward the called method to the wrapped objects. If it
            sends a transaction to the blockchain node, it will be
            forwarded to only one of them, randomly chosen.

            Returns
            -------
            Wrapper or Any
                If the called method is a transaction function, the
                result. Otherwise, the wrapper object
                with the inner wrapped objects called.

            """
            if self.__is_transaction_function:
                random_node_index = random.randint(0, len(self.__objects) - 1)
                return self.__objects[random_node_index](*args, **kwargs)
            self.__objects = [
                object_(*args, **kwargs) for object_ in self.__objects
            ]
            return self

    def __init__(self, transaction_method_names: list[str] = []):
        """Construct an instance.

        Parameters
        ----------
        transaction_method_names : list of str
            The list with method names which are sending transactions
            to the blockchain nodes.

        """
        self.__node_connections = []
        self.__transaction_method_names = transaction_method_names

    def add_node_connection(self, node_connection: N) -> None:
        """Add a node connection to the list of node connections.

        Parameters
        ----------
        node_connection : N
            The node connection to be added.

        """
        self.__node_connections.append(node_connection)

    def get_configured_node_connections(self) -> list[N]:
        """Get the node connections.

        Returns
        -------
        list[N]
            The list of node connections.

        """
        return self.__node_connections

    def __getattr__(self, attr_name: str) -> Wrapper:
        """Creates a wrapper object for the node connections with the
        given attribute name.

        Parameters
        ----------
        attr_name : str
            The name of the attribute.

        Raises
        ------
        NodeConnectionError
            If no node connection was added.

        Returns
        -------
        Wrapper
            Object which wraps the current node connections
            with the given attribute.

        """
        if len(self.__node_connections) == 0:
            raise NodeConnectionError(
                'at least one valid connection must be established')
        return NodeConnections.Wrapper(self.__node_connections, attr_name,
                                       self.__transaction_method_names)


class BlockchainHandler(abc.ABC):
    """Base class for all classes that handle blockchain-specific data
    and operations. These include blockchain clients and utilities.

    """
    @classmethod
    @abc.abstractmethod
    def get_blockchain(cls) -> Blockchain:
        """Get the blockchain the handler is implemented for.

        Returns
        -------
        Blockchain
            The supported blockchain.

        """
        pass  # pragma: no cover

    @classmethod
    def get_blockchain_name(cls) -> str:
        """Get the name of the blockchain the handler is implemented
        for.

        Returns
        -------
        str
            The name of the supported blockchain.

        """
        return cls.get_blockchain().name

    @classmethod
    def find_subclasses(cls: type[H]) -> dict[Blockchain, type[H]]:
        """Find all subclasses of the blockchain handler in the
        handler's package.

        Returns
        -------
        dict
            A dictionary of the blockchain handler's subclasses with
            their supported blockchains as keys.

        """
        package_name = cls.__module__.rpartition('.')[0]
        package_path = str(pathlib.Path(inspect.getfile(cls)).parent)
        # Only subclasses in imported modules can be found
        for module in pkgutil.iter_modules([package_path]):
            full_name = f'{package_name}.{module.name}'
            if full_name != 'pantos.common.blockchains.tasks':
                importlib.import_module(full_name)
        blockchain_handlers = {}
        handler_classes = collections.deque[type[H]](cls.__subclasses__())
        while len(handler_classes) > 0:
            handler_class = handler_classes.pop()
            if not inspect.isabstract(handler_class):
                blockchain = handler_class.get_blockchain()
                blockchain_handlers[blockchain] = handler_class
            handler_classes.extendleft(handler_class.__subclasses__())
        return blockchain_handlers


@dataclasses.dataclass
class VersionedContractAbi:
    """Class which encapsulates the ABI definition of a contract
    with support for versioning.

    Attributes
    ----------
    contract_abi : ContractAbi
        Supported contract ABI.
    version : semantic_version.Version
        The version of the Pantos protocol.

    """
    contract_abi: ContractAbi
    version: semantic_version.Version


@dataclasses.dataclass
class UnhealthyNode:
    """Entity which encapsulates information about an unhealthy node.

    Attributes
    ----------
    node_domain : str
        The domain of the node's URL.
    status : str
        The status of the node.

    """
    node_domain: str
    status: str


class BlockchainUtilities(BlockchainHandler,
                          ErrorCreator[BlockchainUtilitiesError]):
    """Base class for all blockchain utilities classes.

    Attributes
    ----------
    average_block_time : int
        The average time in seconds required to generate a new block of
        the blockchain.
    required_transaction_confirmations : int
        The number of required confirmations for a transaction to be
        considered included in the blockchain.
    transaction_network_id : int or None
        The unique public (i.e. non-Pantos-specific) blockchain network
        identifier (partly called chain ID) to be used for signing
        transactions (to prevent replay attacks between different
        compatible blockchain networks).

    """
    def __init__(self, blockchain_node_urls: list[str],
                 fallback_blockchain_node_urls: list[str],
                 average_block_time: int,
                 required_transaction_confirmations: int,
                 transaction_network_id: typing.Optional[int],
                 default_private_key: typing.Optional[tuple[str, str]] = None,
                 celery_tasks_enabled: bool = False):
        """Construct a blockchain utilities instance.

        Parameters
        ----------
        blockchain_node_urls : list of str
            The URLs of the nodes to use for communication with the
            blockchain network.
        fallback_blockchain_node_urls : list[str]
            The URLs of the fallback nodes to use for communication
            with the blockchain network.
        average_block_time : int
            The average time in seconds required to generate a new block
            of the blockchain.
        required_transaction_confirmations : int
            The number of required confirmations for a transaction to be
            considered included in the blockchain.
        transaction_network_id : int or None
            The unique public (i.e. non-Pantos-specific) blockchain
            network identifier (partly called chain ID) to be used for
            signing transactions (to prevent replay attacks between
            different compatible blockchain networks). It is assumed to
            be the identifier of the main or a test network of the
            blockchain supported by the blockchain utilities subclass.
        default_private_key : tuple of str and str, optional
            The keystore value and password of the default private
            key to be used by the blockchain utilities. (default: None).
        celery_tasks_enabled : bool, optional
            If True, Celery tasks are enabled for enhanced
            functionalities (default: False). This requires a proper
            Celery environment to be set up by the project using the
            blockchain utilities.

        Raises
        ------
        BlockchainUtilitiesError
            If the blockchain utilities initialization fails.

        """
        if average_block_time <= 0:
            raise self._create_error('average block time must be > 0',
                                     average_block_time=average_block_time)
        if required_transaction_confirmations < 0:
            raise self._create_error(
                'required transaction confirmations must be >= 0',
                required_transaction_confirmations=  # noqa: E251
                required_transaction_confirmations)
        if transaction_network_id is not None and transaction_network_id <= 0:
            raise self._create_error(
                'transaction network ID must be > 0',
                transaction_network_id=transaction_network_id)
        if len(blockchain_node_urls) == 0:
            raise self._create_error(
                'at least one blockchain node URL is expected')
        self.average_block_time = average_block_time
        self.required_transaction_confirmations = \
            required_transaction_confirmations
        self.transaction_network_id = transaction_network_id
        self._blockchain_node_urls = blockchain_node_urls
        self._fallback_blockchain_node_urls = fallback_blockchain_node_urls
        self._default_private_key = (
            None if default_private_key is None else self.decrypt_private_key(
                default_private_key[0], default_private_key[1]))
        self._default_address = (None if self._default_private_key is None else
                                 self.get_address(self._default_private_key))
        self._celery_tasks_enabled = celery_tasks_enabled
        self.__loaded_contract_abis: dict[ContractAbi, list[typing.Any]] = {}

    def create_node_connections(
            self,
            timeout: typing.Optional[typing.Union[float, tuple]] = None) \
            -> NodeConnections:
        """Create blockchain node connections.

        Parameters
        ----------
        timeout : float or tuple
            How long to wait for the server to send data before giving up,
            as a float, or a (connect timeout, read timeout) tuple.

        Returns
        -------
        NodeConnections
            The initialized object with valid connections.

        Raises
        ------
        BlockchainUtilities
            Raised if the node connection cannot be initialized.

        """
        fallback_nodes = self._fallback_blockchain_node_urls.copy()
        node_connections = NodeConnections[typing.Any](
            self._get_transaction_method_names())

        for blockchain_node_url in self._blockchain_node_urls:
            node_connection = self.__create_valid_node_connection(
                blockchain_node_url, fallback_nodes, timeout)
            node_connections.add_node_connection(node_connection)

        return node_connections

    def __create_valid_node_connection(
            self, blockchain_node_url: str,
            fallback_blockchain_node_urls: list[str],
            timeout: typing.Optional[typing.Union[float, tuple]] = None):
        blockchain_node_urls = ([blockchain_node_url] +
                                fallback_blockchain_node_urls)
        for blockchain_node_url_ in blockchain_node_urls:
            try:
                valid_node_connection = self._create_single_node_connection(
                    blockchain_node_url_, timeout)
                if blockchain_node_url_ != blockchain_node_url:
                    fallback_blockchain_node_urls.remove(blockchain_node_url_)
                return valid_node_connection
            except SingleNodeConnectionError:
                continue
        blockchain_node_domains = [
            urllib.parse.urlparse(blockchain_node_url).netloc
            for blockchain_node_url in blockchain_node_urls
        ]
        raise self._create_error(
            'cannot connect to any of the blockchain nodes with the domains '
            f'"{blockchain_node_domains}"')

    @abc.abstractmethod
    def get_address(self, private_key: str) -> str:
        """Determine the blockchain address from a private key.

        Parameters
        ----------
        private_key : str
            The unencrypted private key.

        Returns
        -------
        str
            The blockchain address for the given private key.

        Raises
        ------
        BlockchainUtilitiesError
            If the address cannot be determined from the private key.

        """
        pass  # pragma: no cover

    @abc.abstractmethod
    def get_balance(
            self, account_address: str,
            token_address: typing.Optional[str] = None,
            node_connections: typing.Optional[NodeConnections] = None) -> int:
        """Determine the balance of native coins or tokens of an
        address.

        Parameters
        ----------
        account_address : str
            The address that will be evaluated.
        token_address : str, optional
            The address of the token that will be interrogated.
        node_connections : NodeConnections, optional
            The node connections object to be used (default: None).

        Returns
        -------
        int
            Balance of the address.

        Raises
        ------
        BlockchainUtilitiesError
            If the balance cannot be fetched.
        ResultsNotMatchingError
            If the results given by the configured blockchain
            nodes do not match.

        """
        pass  # pragma: no cover

    @abc.abstractmethod
    def is_valid_address(self, address: str) -> bool:
        """Determine if an address string is a valid address on the
        blockchain.

        Parameters
        ----------
        address : str
            The address string to check.

        Returns
        -------
        bool
            True if the given address string is a valid address on the
            blockchain, else False.

        """
        pass  # pragma: no cover

    @abc.abstractmethod
    def is_equal_address(self, address_one: str, address_two: str) -> bool:
        """Determine if two addresses are equal.

        Parameters
        ----------
        address_one : str
            The first address string to check.
        address_two : str
            The second address string to check.

        Returns
        -------
        bool
            True if the given addresses are equal, else False.

        """
        pass  # pragma: no cover

    @abc.abstractmethod
    def is_protocol_version_supported_by_contract(
            self, contract_address: BlockchainAddress,
            versioned_contract_abi: VersionedContractAbi,
            node_connections: NodeConnections | None = None) -> bool:
        """Determine if a given protocol version is supported by a given
        contract.

        Parameters
        ----------
        contract_address : BlockchainAddress
            The address of the contract.
        versioned_contract_abi : VersionedContractAbi
            The contract's ABI and expected protocol version.
        node_connections : NodeConnections, optional
            The blockchain node connections to be used.

        Returns
        -------
        bool
            True if the contract supports the protocol version.

        """
        pass  # pragma: no cover

    @abc.abstractmethod
    def get_unhealthy_nodes(
            self, blockchain_nodes: list[str],
            timeout: float | tuple | None = None) -> list[UnhealthyNode]:
        """Determine the health of the blockchain nodes.

        Parameters
        ----------
        blockchain_nodes : list of str
            The URLs of the blockchain nodes to check.
        timeout : float, tuple or None
            How long to wait for the server to send data before giving up,
            as a float, or a (connect timeout, read timeout) tuple.

        Returns
        -------
        list[UnhealthyNode]
            The list of unhealthy nodes.

        """
        pass

    @abc.abstractmethod
    def _get_transaction_method_names(self) -> list[str]:
        """Determine the blockchain interactor method names which
        are sending transactions.

        Returns
        -------
        list[str]
            The list of method names which are sending
            transactions.

        """
        pass  # pragma: no cover

    def load_contract_abi(
            self,
            versioned_contract_abi: VersionedContractAbi) -> list[typing.Any]:
        """Load a contract ABI, according to its version, as a list
        from a JSON file. If a contract ABI has already been loaded
        before, a cached version is returned.

        Parameters
        ----------
        versioned_contract_abi : VersionedContractAbi
            The version and the contract ABI to load.

        Returns
        -------
        list
            The loaded contract ABI.

        """
        contract_abi = versioned_contract_abi.contract_abi
        version = versioned_contract_abi.version
        if contract_abi in self.__loaded_contract_abis:
            return self.__loaded_contract_abis[contract_abi]
        contract_abi_file_name = contract_abi.get_file_name(
            self.get_blockchain())
        versioned_contract_abi_package = (
            f'{_BASE_CONTRACT_ABI_PACKAGE}.v'
            f'{version.major}_{version.minor}_{version.patch}')
        try:
            with importlib.resources.open_text(
                    versioned_contract_abi_package,
                    contract_abi_file_name) as contract_abi_file:
                loaded_contract_abi = json.load(contract_abi_file)
            self.__loaded_contract_abis[contract_abi] = loaded_contract_abi
            return loaded_contract_abi
        except Exception:
            raise self._create_error('unable to load a contract ABI',
                                     contract_abi=contract_abi,
                                     version=version)

    @abc.abstractmethod
    def decrypt_private_key(self, encrypted_key: str, password: str) -> str:
        """Load the private key from a password-encrypted key.

        Parameters
        ----------
        encrypted_key: str
            The encrypted key.
        password : str
            The password to decrypt the key.

        Returns
        -------
        str
            The decrypted private key.

        Raises
        ------
        BlockchainUtilitiesError
            If the private key cannot be decrypted.

        """
        pass  # pragma: no cover

    @abc.abstractmethod
    def read_transaction_status(
            self, transaction_id: str,
            node_connections: typing.Optional[NodeConnections] = None) \
            -> TransactionStatus:
        """Read the status of a transaction.

        Parameters
        ----------
        transaction_id : str
            The ID/hash of the transaction.
        node_connections : NodeConnections, optional
            The node connections object to be used (default: None).

        Returns
        -------
        TransactionStatus
            The transaction's current status.

        Raises
        ------
        BlockchainUtilitiesError
            If the transaction status cannot be read.
        ResultsNotMatchingError
            If the results given by the configured blockchain
            nodes do not match.

        """
        pass  # pragma: no cover

    @dataclasses.dataclass
    class TransactionSubmissionRequest:
        """Request data for submitting a transaction.

        Attributes
        ----------
        contract_address : BlockchainAddress
            The address of the contract to invoke a function on in the
            transaction.
        versioned_contract_abi : VersionedContractAbi
            The version and the ABI of the contract to invoke a function
            on in the transaction.
        function_selector : str
            The selector of the contract function to be invoked in the
            transaction.
        function_args : ContractFunctionArgs
            The arguments of the contract function to be invoked in the
            transaction.
        gas : int or None
            The gas to be provided for the transaction. Depending on the
            blockchain, it may not be necessary to specify the gas
            explicitly or it may be possible to estimate the required gas
            automatically.
        min_adaptable_fee_per_gas : int
            The minimum adaptable fee per gas. The definition of the
            adaptable fee per gas depends on the blockchain's
            transaction fee model.
        max_total_fee_per_gas : int or None
            The maximum total fee per gas. Since the total fee per gas
            will anyway be kept as low as possible for the transaction
            to be included in a block, it is recommended to specify a
            large maximum total fee per gas. If it is not specified at
            all, no upper limit for the total fee per gas will be
            enforced.
        amount : int or None
            The amount of native coins to be sent in the transaction
            (specified in the blockchain's smallest coin denomination).
        nonce : int
            The unique transaction nonce of the account controlled by
            the default private key.

        """
        contract_address: BlockchainAddress
        versioned_contract_abi: VersionedContractAbi
        function_selector: str
        function_args: ContractFunctionArgs
        gas: typing.Optional[int]
        min_adaptable_fee_per_gas: int
        max_total_fee_per_gas: typing.Optional[int]
        amount: typing.Optional[int]
        nonce: int

        def to_dict(self) -> dict[str, typing.Any]:
            """Convert the request instance to its corresponding
            dictionary representation.

            Returns
            -------
            dict
                The dictionary representation.

            """
            request_dict = dataclasses.asdict(self)
            request_dict['versioned_contract_abi']['contract_abi'] = \
                self.versioned_contract_abi.contract_abi.value
            request_dict['versioned_contract_abi']['version'] = \
                str(self.versioned_contract_abi.version)
            return request_dict

        @classmethod
        def from_dict(cls: type[T], request_dict: dict[str, typing.Any]) -> T:
            """Convert the dictionary representation of a request to its
            corresponding request instance.

            Parameters
            ----------
            request_dict : dict
                The dictionary representation.

            Returns
            -------
            TransactionSubmissionRequest
                The request instance.

            """
            request_dict = copy.deepcopy(request_dict)
            request_dict['versioned_contract_abi'] = VersionedContractAbi(
                ContractAbi(
                    request_dict['versioned_contract_abi']['contract_abi']),
                semantic_version.Version(
                    request_dict['versioned_contract_abi']['version']))
            return cls(**request_dict)

    @dataclasses.dataclass
    class TransactionSubmissionResponse:
        """Response data from submitting a transaction.

        Attributes
        ----------
        transaction_id : str
            The ID/hash of the submitted transaction.
        adaptable_fee_per_gas : int
            The adaptable fee per gas actually used for submitting the
            transaction.

        """
        transaction_id: str
        adaptable_fee_per_gas: int

    @abc.abstractmethod
    def submit_transaction(
            self, request: TransactionSubmissionRequest,
            node_connections: typing.Optional[NodeConnections] = None) \
            -> TransactionSubmissionResponse:
        """Submit a transaction.

        Parameters
        ----------
        request : TransactionSubmissionRequest
            The request data for submitting a transaction.
        node_connections : NodeConnections, optional
            The node connections object to be used (default: None).

        Returns
        -------
        TransactionSubmissionResponse
            The response data from submitting a transaction.

        Raises
        ------
        MaxTotalFeePerGasExceededError
            If the maximum total fee per gas would be exceeded for the
            transaction to be submitted.
        TransactionUnderpricedError
            If the transaction has been submitted as an underpriced
            transaction.
        TransactionNonceTooLowError
            If the transaction has been submitted with a nonce too low.
        ResultsNotMatchingError
            If the results given by the configured blockchain
            nodes do not match.
        BlockchainUtilitiesError
            If the transaction cannot be submitted for any other reason.

        """
        pass  # pragma: no cover

    @dataclasses.dataclass
    class TransactionResubmissionRequest(TransactionSubmissionRequest):
        """Request data for resubmitting a transaction.

        Attributes
        ----------
        adaptable_fee_increase_factor : float
            The factor for increasing the adaptable fee per gas.

        """
        adaptable_fee_increase_factor: float

    @dataclasses.dataclass
    class TransactionResubmissionResponse(TransactionSubmissionResponse):
        """Response data from resubmitting a transaction.

        """
        pass

    def resubmit_transaction(
            self, request: TransactionResubmissionRequest,
            node_connections: typing.Optional[NodeConnections] = None) \
            -> TransactionResubmissionResponse:
        """Resubmit (i.e. replace) a transaction.

        Parameters
        ----------
        request : TransactionResubmissionRequest
            The request data for resubmitting a transaction.
        node_connections : NodeConnections, optional
            The node connections object to be used (default: None).

        Returns
        -------
        TransactionResubmissionResponse
            The response data from resubmitting a transaction.

        Raises
        ------
        MaxTotalFeePerGasExceededError
            If the maximum total fee per gas would be exceeded for the
            transaction to be resubmitted.
        TransactionNonceTooLowError
            If the transaction has been resubmitted with a nonce too
            low.
        ResultsNotMatchingError
            If the results given by the configured blockchain
            nodes do not match.
        BlockchainUtilitiesError
            If the transaction cannot be resubmitted for any other
            reason.

        """
        if request.min_adaptable_fee_per_gas < 0:
            raise self._create_error(
                'previous minimum adaptable fee per gas must be >= 0',
                request=request)
        if (request.adaptable_fee_increase_factor
                < MIN_ADAPTABLE_FEE_INCREASE_FACTOR):
            raise self._create_error(
                'adaptable fee increase factor must be >= '
                f'{MIN_ADAPTABLE_FEE_INCREASE_FACTOR}', request=request)
        response = None
        while response is None:
            # Minimum adaptable fee per gas must be 1 for the
            # resubmission if the previous minimum adaptable fee per gas
            # has been 0
            min_adaptable_fee_per_gas = max(
                1,
                math.ceil(request.min_adaptable_fee_per_gas *
                          request.adaptable_fee_increase_factor))
            if (request.max_total_fee_per_gas is not None and
                    min_adaptable_fee_per_gas > request.max_total_fee_per_gas):
                raise self._create_max_total_fee_per_gas_exceeded_error(
                    request=request)
            request = dataclasses.replace(
                request, min_adaptable_fee_per_gas=min_adaptable_fee_per_gas)
            try:
                response = self.submit_transaction(request, node_connections)
            except TransactionUnderpricedError:
                _logger.warning('resubmitted transaction underpriced',
                                extra=vars(request))
        return BlockchainUtilities.TransactionResubmissionResponse(
            response.transaction_id, response.adaptable_fee_per_gas)

    @dataclasses.dataclass
    class TransactionSubmissionStartRequest(TransactionResubmissionRequest):
        """Request data for starting a transaction submission.

        Attributes
        ----------
        blocks_until_resubmission : int
            The number of blocks to wait until the transaction is
            resubmitted if it has not yet been included in a block.

        """
        blocks_until_resubmission: int

    def start_transaction_submission(
            self, request: TransactionSubmissionStartRequest,
            node_connections: typing.Optional[NodeConnections] = None) \
            -> uuid.UUID:
        """Start a transaction submission. The transaction is
        automatically resubmitted with higher transaction fees until it
        is included in a block. Celery tasks need to be enabled for this
        function.

        Parameters
        ----------
        request : TransactionSubmissionStartRequest
            The request data for starting a transaction submission.
        node_connections : NodeConnections, optional
            The node connections object to be used (default: None).

        Returns
        -------
        uuid.UUID
            The unique internal transaction ID, which can be used later
            to retrieve the status of the transaction submission.

        Raises
        ------
        MaxTotalFeePerGasExceededError
            If the maximum total fee per gas would be exceeded for the
            transaction to be submitted.
        TransactionNonceTooLowError
            If the transaction has been submitted with a nonce too low.
        ResultsNotMatchingError
            If the results given by the configured blockchain
            nodes do not match.
        BlockchainUtilitiesError
            If the transaction submission cannot be started for any
            other reason.

        """
        if not self._celery_tasks_enabled:
            raise self._create_error('Celery tasks disabled')
        if request.blocks_until_resubmission <= 0:
            raise self._create_error('blocks until resubmission must be > 0',
                                     request=request)
        if (request.adaptable_fee_increase_factor
                < MIN_ADAPTABLE_FEE_INCREASE_FACTOR):
            raise self._create_error(
                'adaptable fee increase factor must be >= '
                f'{MIN_ADAPTABLE_FEE_INCREASE_FACTOR}', request=request)
        try:
            response = self.submit_transaction(request, node_connections)
        except TransactionUnderpricedError:
            _logger.warning('initially submitted transaction underpriced',
                            extra=vars(request))
            response = self.resubmit_transaction(request, node_connections)
        try:
            from pantos.common.blockchains.tasks import \
                create_transaction_resubmission_task
            internal_transaction_id = create_transaction_resubmission_task(
                self.get_blockchain(), request, response)
        except Exception:
            raise self._create_error(
                'unable to create a transaction resubmission task',
                request=request, transaction_id=response.transaction_id)
        return internal_transaction_id

    @dataclasses.dataclass
    class TransactionSubmissionStatusResponse:
        """Response data from retrieving the status of a transaction
        submission.

        Attributes
        ----------
        transaction_submission_completed : bool
            True if and only if the transaction submission has been
            completed (i.e. the transaction is either confirmed or
            reverted).
        transaction_status : TransactionStatus or None
            The status of the submitted (and eventually included)
            transaction (available if the transaction submission has
            been completed).
        transaction_id : str or None
            The ID/hash of the submitted (and eventually included)
            transaction (available if the transaction submission has
            been completed).

        """
        transaction_submission_completed: bool
        transaction_status: typing.Optional[TransactionStatus] = None
        transaction_id: typing.Optional[str] = None

    def get_transaction_submission_status(
            self, internal_transaction_id: uuid.UUID) \
            -> TransactionSubmissionStatusResponse:
        """Retrieve the status of a transaction submission. Celery tasks
        need to be enabled for this function.

        Parameters
        ----------
        internal_transaction_id : uuid.UUID
            The unique internal transaction ID.

        Returns
        -------
        TransactionSubmissionStatusResponse
            The response data from retrieving the status of a
            transaction submission.

        Raises
        ------
        BlockchainUtilitiesError
            If the status of the transaction submission cannot be
            retrieved or if there has been an unresolvable error during
            the transaction submission.

        """
        if not self._celery_tasks_enabled:
            raise self._create_error('Celery tasks disabled')
        try:
            from pantos.common.blockchains.tasks import \
                get_transaction_resubmission_task_result
            task_result = get_transaction_resubmission_task_result(
                internal_transaction_id)
        except Exception:
            raise self._create_error(
                'unable to get a transaction resubmission task result',
                internal_transaction_id=internal_transaction_id)
        if task_result is None:
            return BlockchainUtilities.TransactionSubmissionStatusResponse(
                False)
        transaction_status = task_result[0]
        transaction_id = task_result[1]
        return BlockchainUtilities.TransactionSubmissionStatusResponse(
            True, transaction_status, transaction_id)

    @abc.abstractmethod
    def _create_single_node_connection(
            self, blockchain_node_url: str,
            timeout: float | tuple | None = None) -> typing.Any:
        """Create a single blockchain-specific node connection
        with the given URL.

        Parameters
        ----------
        blockchain_node_url : str
            The blockchain node URL.
        timeout : float, tuple or None
            How long to wait for the server to send data before giving up,
            as a float, or a (connect timeout, read timeout) tuple.

        Returns
        -------
        typing.Any
            The blockchain-specific node connection.

        Raises
        ------
        SingleNodeConnectionError
            If the node connection cannot be established.

        """
        pass  # pragma: no cover

    def _create_max_total_fee_per_gas_exceeded_error(
            self, **kwargs: typing.Any) -> BlockchainUtilitiesError:
        return self._create_error(
            specialized_error_class=MaxTotalFeePerGasExceededError, **kwargs)

    def _create_transaction_nonce_too_low_error(
            self, **kwargs: typing.Any) -> BlockchainUtilitiesError:
        return self._create_error(
            specialized_error_class=TransactionNonceTooLowError, **kwargs)

    def _create_transaction_underpriced_error(
            self, **kwargs: typing.Any) -> BlockchainUtilitiesError:
        return self._create_error(
            specialized_error_class=TransactionUnderpricedError, **kwargs)

    def _create_single_node_connection_error(
            self, **kwargs: typing.Any) -> BlockchainUtilitiesError:
        return self._create_error(
            specialized_error_class=SingleNodeConnectionError, **kwargs)

"""Factory for Pantos blockchain utilities.

"""
import typing

from pantos.common.blockchains.base import BlockchainUtilities
from pantos.common.blockchains.enums import Blockchain
from pantos.common.exceptions import NotInitializedError

_blockchain_utilities: dict[Blockchain, BlockchainUtilities] = {}
"""Blockchain-specific utilities objects."""

_blockchain_utilities_classes = BlockchainUtilities.find_subclasses()
"""Blockchain-specific utilities classes."""


def initialize_blockchain_utilities(
        blockchain: Blockchain, blockchain_node_urls: list[str],
        fallback_blockchain_node_urls: list[str], average_block_time: int,
        required_transaction_confirmations: int,
        transaction_network_id: typing.Optional[int],
        default_private_key: typing.Optional[tuple[str, str]] = None,
        celery_tasks_enabled: bool = False) -> None:
    """Initialize the utilities for the specified blockchain.

    Parameters
    ----------
    blockchain : Blockchain
        The blockchain to initialize a utilities instance for.
    blockchain_node_urls : str
        The URLs of the blockchain nodes to use for the specified
        blockchain.
    fallback_blockchain_node_urls : list[str]
        The URLs of the fallback nodes to use for communication
        with the blockchain network.
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
        compatible blockchain networks). It is assumed to be the
        identifier of the main or a test network of the specified
        blockchain.
    default_private_key : tuple of str and str, optional
        The keystore value and password of the default private
        key to be used by the blockchain utilities. (default: None).
    celery_tasks_enabled : bool, optional
        If True, Celery tasks are enabled for enhanced functionalities
        (default: False). This requires a proper Celery environment to
        be set up by the project using the blockchain utilities.

    Raises
    ------
    BlockchainUtilitiesError
        If the blockchain-specific utilities cannot be initialized.

    """
    utilities_class = _blockchain_utilities_classes[blockchain]
    _blockchain_utilities[blockchain] = utilities_class(
        blockchain_node_urls, fallback_blockchain_node_urls,
        average_block_time, required_transaction_confirmations,
        transaction_network_id, default_private_key=default_private_key,
        celery_tasks_enabled=celery_tasks_enabled)


def get_blockchain_utilities(blockchain: Blockchain) -> BlockchainUtilities:
    """Factory for blockchain-specific utilities objects.

    Parameters
    ----------
    blockchain : Blockchain
        The blockchain to get the utilities instance for.

    Returns
    -------
    BlockchainUtilities
        A blockchain utilities instance for the specified blockchain.

    Raises
    ------
    NotInitializedError
        If the utilities have not been initialized for the specified
        blockchain.

    """
    try:
        return _blockchain_utilities[blockchain]
    except KeyError:
        raise NotInitializedError(
            f'{blockchain.name} utilities have not been initialized')

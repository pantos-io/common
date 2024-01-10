import unittest.mock

import pytest

from pantos.common.blockchains.avalanche import AvalancheUtilities
from pantos.common.blockchains.base import BlockchainUtilities
from pantos.common.blockchains.bnbchain import BnbChainUtilities
from pantos.common.blockchains.celo import CeloUtilities
from pantos.common.blockchains.cronos import CronosUtilities
from pantos.common.blockchains.enums import Blockchain
from pantos.common.blockchains.ethereum import EthereumUtilities
from pantos.common.blockchains.factory import _blockchain_utilities
from pantos.common.blockchains.factory import get_blockchain_utilities
from pantos.common.blockchains.factory import initialize_blockchain_utilities
from pantos.common.blockchains.fantom import FantomUtilities
from pantos.common.blockchains.polygon import PolygonUtilities
from pantos.common.blockchains.solana import SolanaUtilities
from pantos.common.exceptions import NotInitializedError


@pytest.fixture(autouse=True)
def clear_blockchain_utilities():
    _blockchain_utilities.clear()


@pytest.mark.parametrize('blockchain',
                         [blockchain for blockchain in Blockchain])
def test_get_blockchain_utilities_initialized(
        blockchain, blockchain_node_urls, fallback_blockchain_node_urls,
        average_block_time, required_transaction_confirmations,
        transaction_network_id):
    blockchain_utilities_class = _get_blockchain_utilities_class(blockchain)
    with unittest.mock.patch.object(blockchain_utilities_class, '__init__',
                                    lambda *args, **kwargs: None):
        initialize_blockchain_utilities(blockchain, blockchain_node_urls,
                                        fallback_blockchain_node_urls,
                                        average_block_time,
                                        required_transaction_confirmations,
                                        transaction_network_id)
        blockchain_utilities = get_blockchain_utilities(blockchain)
        assert isinstance(blockchain_utilities, BlockchainUtilities)
        assert isinstance(blockchain_utilities, blockchain_utilities_class)


@pytest.mark.parametrize('blockchain',
                         [blockchain for blockchain in Blockchain])
def test_get_blockchain_utilities_not_initialized(blockchain):
    with pytest.raises(NotInitializedError):
        get_blockchain_utilities(blockchain)


def _get_blockchain_utilities_class(blockchain):
    if blockchain is Blockchain.AVALANCHE:
        return AvalancheUtilities
    if blockchain is Blockchain.BNB_CHAIN:
        return BnbChainUtilities
    if blockchain is Blockchain.CELO:
        return CeloUtilities
    if blockchain is Blockchain.CRONOS:
        return CronosUtilities
    if blockchain is Blockchain.ETHEREUM:
        return EthereumUtilities
    if blockchain is Blockchain.FANTOM:
        return FantomUtilities
    if blockchain is Blockchain.POLYGON:
        return PolygonUtilities
    if blockchain is Blockchain.SOLANA:
        return SolanaUtilities
    raise NotImplementedError

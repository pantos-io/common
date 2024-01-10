import pytest

from pantos.common.blockchains.enums import Blockchain
from pantos.common.blockchains.solana import SolanaUtilities
from pantos.common.blockchains.solana import SolanaUtilitiesError


@pytest.fixture(scope='module')
def solana_utilities(blockchain_node_urls, fallback_blockchain_node_urls,
                     average_block_time, required_transaction_confirmations,
                     transaction_network_id):
    return SolanaUtilities(blockchain_node_urls, fallback_blockchain_node_urls,
                           average_block_time,
                           required_transaction_confirmations,
                           transaction_network_id)


def test_get_blockchain_correct(solana_utilities):
    assert solana_utilities.get_blockchain() is Blockchain.SOLANA
    assert SolanaUtilities.get_blockchain() is Blockchain.SOLANA


def test_get_error_class_correct(solana_utilities):
    assert solana_utilities.get_error_class() is SolanaUtilitiesError
    assert SolanaUtilities.get_error_class() is SolanaUtilitiesError


def test_is_equal_address_not_implemented(solana_utilities):
    with pytest.raises(NotImplementedError):
        solana_utilities.is_equal_address('address_one', 'address_two')

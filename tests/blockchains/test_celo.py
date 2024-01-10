import pytest

from pantos.common.blockchains.celo import CeloUtilities
from pantos.common.blockchains.celo import CeloUtilitiesError
from pantos.common.blockchains.enums import Blockchain


@pytest.fixture(scope='module')
def celo_utilities(blockchain_node_urls, fallback_blockchain_node_urls,
                   average_block_time, required_transaction_confirmations,
                   transaction_network_id):
    return CeloUtilities(blockchain_node_urls, fallback_blockchain_node_urls,
                         average_block_time,
                         required_transaction_confirmations,
                         transaction_network_id)


def test_get_blockchain_correct(celo_utilities):
    assert celo_utilities.get_blockchain() is Blockchain.CELO
    assert CeloUtilities.get_blockchain() is Blockchain.CELO


def test_get_error_class_correct(celo_utilities):
    assert celo_utilities.get_error_class() is CeloUtilitiesError
    assert CeloUtilities.get_error_class() is CeloUtilitiesError

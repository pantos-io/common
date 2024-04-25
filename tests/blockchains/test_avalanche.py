import pytest

from pantos.common.blockchains.avalanche import AvalancheUtilities
from pantos.common.blockchains.avalanche import AvalancheUtilitiesError
from pantos.common.blockchains.enums import Blockchain


@pytest.fixture(scope='module')
def avalanche_utilities(blockchain_node_urls, fallback_blockchain_node_urls,
                        average_block_time, required_transaction_confirmations,
                        transaction_network_id):
    return AvalancheUtilities(blockchain_node_urls,
                              fallback_blockchain_node_urls,
                              average_block_time,
                              required_transaction_confirmations,
                              transaction_network_id)


def test_get_blockchain_correct(avalanche_utilities):
    assert avalanche_utilities.get_blockchain() is Blockchain.AVALANCHE
    assert AvalancheUtilities.get_blockchain() is Blockchain.AVALANCHE


def test_get_error_class_correct(avalanche_utilities):
    assert avalanche_utilities.get_error_class() is AvalancheUtilitiesError
    assert AvalancheUtilities.get_error_class() is AvalancheUtilitiesError

import pytest

from pantos.common.blockchains.enums import Blockchain
from pantos.common.blockchains.fantom import FantomUtilities
from pantos.common.blockchains.fantom import FantomUtilitiesError


@pytest.fixture(scope='module')
def fantom_utilities(blockchain_node_urls, fallback_blockchain_node_urls,
                     average_block_time, required_transaction_confirmations,
                     transaction_network_id):
    return FantomUtilities(blockchain_node_urls, fallback_blockchain_node_urls,
                           average_block_time,
                           required_transaction_confirmations,
                           transaction_network_id)


def test_get_blockchain_correct(fantom_utilities):
    assert fantom_utilities.get_blockchain() is Blockchain.FANTOM
    assert FantomUtilities.get_blockchain() is Blockchain.FANTOM


def test_get_error_class_correct(fantom_utilities):
    assert fantom_utilities.get_error_class() is FantomUtilitiesError
    assert FantomUtilities.get_error_class() is FantomUtilitiesError

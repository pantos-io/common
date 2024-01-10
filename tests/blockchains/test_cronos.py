import pytest

from pantos.common.blockchains.cronos import CronosUtilities
from pantos.common.blockchains.cronos import CronosUtilitiesError
from pantos.common.blockchains.enums import Blockchain


@pytest.fixture(scope='module')
def cronos_utilities(blockchain_node_urls, fallback_blockchain_node_urls,
                     average_block_time, required_transaction_confirmations,
                     transaction_network_id):
    return CronosUtilities(blockchain_node_urls, fallback_blockchain_node_urls,
                           average_block_time,
                           required_transaction_confirmations,
                           transaction_network_id)


def test_get_blockchain_correct(cronos_utilities):
    assert cronos_utilities.get_blockchain() is Blockchain.CRONOS
    assert CronosUtilities.get_blockchain() is Blockchain.CRONOS


def test_get_error_class_correct(cronos_utilities):
    assert cronos_utilities.get_error_class() is CronosUtilitiesError
    assert CronosUtilities.get_error_class() is CronosUtilitiesError

import pytest

from pantos.common.blockchains.enums import Blockchain
from pantos.common.blockchains.sonic import SonicUtilities
from pantos.common.blockchains.sonic import SonicUtilitiesError


@pytest.fixture(scope='module')
def sonic_utilities(blockchain_node_urls, fallback_blockchain_node_urls,
                    average_block_time, required_transaction_confirmations,
                    transaction_network_id):
    return SonicUtilities(blockchain_node_urls, fallback_blockchain_node_urls,
                          average_block_time,
                          required_transaction_confirmations,
                          transaction_network_id)


def test_get_blockchain_correct(sonic_utilities):
    assert sonic_utilities.get_blockchain() is Blockchain.SONIC
    assert SonicUtilities.get_blockchain() is Blockchain.SONIC


def test_get_error_class_correct(sonic_utilities):
    assert sonic_utilities.get_error_class() is SonicUtilitiesError
    assert SonicUtilities.get_error_class() is SonicUtilitiesError

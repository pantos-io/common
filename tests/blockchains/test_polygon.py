import pytest

from pantos.common.blockchains.enums import Blockchain
from pantos.common.blockchains.polygon import PolygonUtilities
from pantos.common.blockchains.polygon import PolygonUtilitiesError


@pytest.fixture(scope='module')
def polygon_utilities(blockchain_node_urls, fallback_blockchain_node_urls,
                      average_block_time, required_transaction_confirmations,
                      transaction_network_id):
    return PolygonUtilities(blockchain_node_urls,
                            fallback_blockchain_node_urls, average_block_time,
                            required_transaction_confirmations,
                            transaction_network_id)


def test_get_blockchain_correct(polygon_utilities):
    assert polygon_utilities.get_blockchain() is Blockchain.POLYGON
    assert PolygonUtilities.get_blockchain() is Blockchain.POLYGON


def test_get_error_class_correct(polygon_utilities):
    assert polygon_utilities.get_error_class() is PolygonUtilitiesError
    assert PolygonUtilities.get_error_class() is PolygonUtilitiesError

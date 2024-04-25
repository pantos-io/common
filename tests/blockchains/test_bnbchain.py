import pytest

from pantos.common.blockchains.bnbchain import BnbChainUtilities
from pantos.common.blockchains.bnbchain import BnbChainUtilitiesError
from pantos.common.blockchains.enums import Blockchain


@pytest.fixture(scope='module')
def bnb_chain_utilities(blockchain_node_urls, fallback_blockchain_node_urls,
                        average_block_time, required_transaction_confirmations,
                        transaction_network_id):
    return BnbChainUtilities(blockchain_node_urls,
                             fallback_blockchain_node_urls, average_block_time,
                             required_transaction_confirmations,
                             transaction_network_id)


def test_get_blockchain_correct(bnb_chain_utilities):
    assert bnb_chain_utilities.get_blockchain() is Blockchain.BNB_CHAIN
    assert BnbChainUtilities.get_blockchain() is Blockchain.BNB_CHAIN


def test_get_error_class_correct(bnb_chain_utilities):
    assert bnb_chain_utilities.get_error_class() is BnbChainUtilitiesError
    assert BnbChainUtilities.get_error_class() is BnbChainUtilitiesError

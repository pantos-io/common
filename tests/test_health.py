import unittest.mock

import pytest

from pantos.common.blockchains.base import GENERAL_RPC_ERROR_MESSAGE
from pantos.common.blockchains.enums import Blockchain
from pantos.common.exceptions import NotInitializedError
from pantos.common.health import NodesHealth
from pantos.common.health import check_blockchain_nodes_health

NODE_RPC_DOMAIN_1 = 'domain.example.com'
NODE_RPC_DOMAIN_2 = 'domain.example2.com'


@unittest.mock.patch(
    'pantos.common.health._blockchain_nodes',
    {Blockchain.ETHEREUM: ([NODE_RPC_DOMAIN_1, NODE_RPC_DOMAIN_2], 10)})
@unittest.mock.patch('pantos.common.health.get_blockchain_utilities')
def test_check_blockchain_nodes_health_correct(
        mocked_get_blockchain_utilities):
    mocked_get_blockchain_utilities().get_unhealthy_nodes.return_value = [
        (NODE_RPC_DOMAIN_1, GENERAL_RPC_ERROR_MESSAGE),
        (NODE_RPC_DOMAIN_2, GENERAL_RPC_ERROR_MESSAGE)
    ]
    expected_result = {
        Blockchain.ETHEREUM: NodesHealth(
            healthy_total=0, unhealthy_total=2,
            unhealthy_nodes=[(NODE_RPC_DOMAIN_1, GENERAL_RPC_ERROR_MESSAGE),
                             (NODE_RPC_DOMAIN_2, GENERAL_RPC_ERROR_MESSAGE)])
    }

    result = check_blockchain_nodes_health()

    assert result == expected_result


@unittest.mock.patch('pantos.common.health._blockchain_nodes', {})
def test_check_blockchain_nodes_health_uninitialized_nodes():
    with pytest.raises(NotInitializedError):
        check_blockchain_nodes_health()

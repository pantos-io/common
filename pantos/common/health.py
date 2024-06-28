"""Module for analyzing the health of the system.

"""
import dataclasses

from pantos.common.blockchains.base import UnhealthyNode
from pantos.common.blockchains.enums import Blockchain
from pantos.common.blockchains.factory import get_blockchain_utilities
from pantos.common.exceptions import NotInitializedError

_blockchain_nodes: dict[Blockchain, tuple[list[str], float | tuple]] = {}


@dataclasses.dataclass
class NodesHealth:
    """Entity which provides information about the health status
    of the nodes requested for a blockchain network.

    Attributes
    ----------
    healthy_total : int
        The total number of healthy nodes.
    unhealthy_total : int
        The total number of unhealthy nodes.
    unhealthy_nodes : list[str, str]
        The list of unhealthy nodes with their respective status.

    """
    healthy_total: int
    unhealthy_total: int
    unhealthy_nodes: list[UnhealthyNode]


def check_blockchain_nodes_health() -> dict[Blockchain, NodesHealth]:
    """Check the health of the blockchain nodes.

    Returns
    -------
    dict[Blockchain, NodesHealth]
        The health status of the blockchain nodes.

    Raises
    ------
    NotInitializedError
        If the blockchain nodes have not been initialized yet.

    """
    if _blockchain_nodes == {}:
        raise NotInitializedError(
            'the blockchain nodes have not been initialized yet')
    nodes_health = {}
    for blockchain in _blockchain_nodes:
        blockchain_utilities = get_blockchain_utilities(blockchain)
        blockchain_nodes = _blockchain_nodes[blockchain][0]
        timeout = _blockchain_nodes[blockchain][1]
        unhealthy_nodes = blockchain_utilities.get_unhealthy_nodes(
            blockchain_nodes, timeout)
        nodes_health[blockchain] = NodesHealth(
            len(blockchain_nodes) - len(unhealthy_nodes), len(unhealthy_nodes),
            unhealthy_nodes)
    return nodes_health


def initialize_blockchain_nodes(
    blockchain_nodes: dict[Blockchain, tuple[list[str],
                                             float | tuple]]) -> None:
    """Initialize the blockchain nodes.

    Parameters
    ----------
    blockchain_nodes : dict[Blockchain, tuple[list[str], float | tuple]]
        The blockchain nodes to be initialized.

    """
    global _blockchain_nodes
    if _blockchain_nodes != blockchain_nodes:  # pragma: no cover
        _blockchain_nodes = blockchain_nodes

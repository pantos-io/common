"""Module for Avalanche-specific utilities and errors. Since the
Avalanche C-Chain is Ethereum-compatible, the utilities implementation
inherits from the pantos.common.blockchains.ethereum module.

"""
from pantos.common.blockchains.base import BlockchainUtilitiesError
from pantos.common.blockchains.enums import Blockchain
from pantos.common.blockchains.ethereum import EthereumUtilities
from pantos.common.blockchains.ethereum import EthereumUtilitiesError


class AvalancheUtilitiesError(EthereumUtilitiesError):
    """Exception class for all Avalanche utilities errors.

    """
    pass


class AvalancheUtilities(EthereumUtilities):
    """Class for Avalanche-specific utilities.

    """
    @classmethod
    def get_blockchain(cls) -> Blockchain:
        # Docstring inherited
        return Blockchain.AVALANCHE

    @classmethod
    def get_error_class(cls) -> type[BlockchainUtilitiesError]:
        # Docstring inherited
        return AvalancheUtilitiesError

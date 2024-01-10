"""Module for Cronos-specific utilities and errors. Since Cronos is
Ethereum-compatible, the utilities implementation inherits from the
pantos.common.blockchains.ethereum module.

"""
from pantos.common.blockchains.base import BlockchainUtilitiesError
from pantos.common.blockchains.enums import Blockchain
from pantos.common.blockchains.ethereum import EthereumUtilities
from pantos.common.blockchains.ethereum import EthereumUtilitiesError


class CronosUtilitiesError(EthereumUtilitiesError):
    """Exception class for all Cronos utilities errors.

    """
    pass


class CronosUtilities(EthereumUtilities):
    """Class for Cronos-specific utilities.

    """
    @classmethod
    def get_blockchain(cls) -> Blockchain:
        # Docstring inherited
        return Blockchain.CRONOS

    @classmethod
    def get_error_class(cls) -> type[BlockchainUtilitiesError]:
        # Docstring inherited
        return CronosUtilitiesError

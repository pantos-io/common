"""Module for Celo-specific utilities and errors. Since Celo is
Ethereum-compatible, the utilities implementation inherits from the
pantos.common.blockchains.ethereum module.

"""
from pantos.common.blockchains.base import BlockchainUtilitiesError
from pantos.common.blockchains.enums import Blockchain
from pantos.common.blockchains.ethereum import EthereumUtilities
from pantos.common.blockchains.ethereum import EthereumUtilitiesError


class CeloUtilitiesError(EthereumUtilitiesError):
    """Exception class for all Celo utilities errors.

    """
    pass


class CeloUtilities(EthereumUtilities):
    """Class for Celo-specific utilities.

    """
    @classmethod
    def get_blockchain(cls) -> Blockchain:
        # Docstring inherited
        return Blockchain.CELO

    @classmethod
    def get_error_class(cls) -> type[BlockchainUtilitiesError]:
        # Docstring inherited
        return CeloUtilitiesError

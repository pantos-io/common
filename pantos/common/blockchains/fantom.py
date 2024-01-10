"""Module for Fantom-specific utilities and errors. Since Fantom is
Ethereum-compatible, the utilities implementation inherits from the
pantos.common.blockchains.ethereum module.

"""
from pantos.common.blockchains.base import BlockchainUtilitiesError
from pantos.common.blockchains.enums import Blockchain
from pantos.common.blockchains.ethereum import EthereumUtilities
from pantos.common.blockchains.ethereum import EthereumUtilitiesError


class FantomUtilitiesError(EthereumUtilitiesError):
    """Exception class for all Fantom utilities errors.

    """
    pass


class FantomUtilities(EthereumUtilities):
    """Class for Fantom-specific utilities.

    """
    @classmethod
    def get_blockchain(cls) -> Blockchain:
        # Docstring inherited
        return Blockchain.FANTOM

    @classmethod
    def get_error_class(cls) -> type[BlockchainUtilitiesError]:
        # Docstring inherited
        return FantomUtilitiesError

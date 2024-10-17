"""Module for Sonic-specific utilities and errors. Since Sonic is
Ethereum-compatible, the utilities implementation inherits from the
pantos.common.blockchains.ethereum module.

Note that Pantos used to support Sonic's predecessor Fantom. This module
was renamed accordingly on 2024-10-17.

"""
from pantos.common.blockchains.base import BlockchainUtilitiesError
from pantos.common.blockchains.enums import Blockchain
from pantos.common.blockchains.ethereum import EthereumUtilities
from pantos.common.blockchains.ethereum import EthereumUtilitiesError


class SonicUtilitiesError(EthereumUtilitiesError):
    """Exception class for all Sonic utilities errors.

    """
    pass


class SonicUtilities(EthereumUtilities):
    """Class for Sonic-specific utilities.

    """
    @classmethod
    def get_blockchain(cls) -> Blockchain:
        # Docstring inherited
        return Blockchain.SONIC

    @classmethod
    def get_error_class(cls) -> type[BlockchainUtilitiesError]:
        # Docstring inherited
        return SonicUtilitiesError

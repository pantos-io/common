"""Module for BNB-Chain-specific utilities and errors. Since the BNB
Smart Chain is Ethereum-compatible, the utilities implementation
inherits from the pantos.common.blockchains.ethereum module.

"""
from pantos.common.blockchains.base import BlockchainUtilitiesError
from pantos.common.blockchains.enums import Blockchain
from pantos.common.blockchains.ethereum import EthereumUtilities
from pantos.common.blockchains.ethereum import EthereumUtilitiesError


class BnbChainUtilitiesError(EthereumUtilitiesError):
    """Exception class for all BNB Chain utilities errors.

    """
    pass


class BnbChainUtilities(EthereumUtilities):
    """Class for BNB-Chain-specific utilities.

    """
    @classmethod
    def get_blockchain(cls) -> Blockchain:
        # Docstring inherited
        return Blockchain.BNB_CHAIN

    @classmethod
    def get_error_class(cls) -> type[BlockchainUtilitiesError]:
        # Docstring inherited
        return BnbChainUtilitiesError

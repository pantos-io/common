"""Module that defines blockchain-specific enumerations.

"""
import enum


class Blockchain(enum.IntEnum):
    """Enumeration of supported blockchain networks.

    """
    ETHEREUM = 0
    BNB_CHAIN = 1
    # Decommissioned: BITCOIN_RSK = 2
    AVALANCHE = 3
    SOLANA = 4
    POLYGON = 5
    CRONOS = 6
    FANTOM = 7
    CELO = 8
    # Decomissioned: AURORA = 9

    @property
    def name_in_pascal_case(self) -> str:
        """The name of the blockchain network in pascal case.

        """
        return ''.join(word.capitalize() for word in self.name.split('_'))

    @staticmethod
    def from_name(name: str) -> 'Blockchain':
        """Find an enumeration member by its name.

        Parameters
        ----------
        name : str
            The name to search for.

        Raises
        ------
        NameError
            If no enumeration member can be found for the given name.

        """
        name_upper = name.upper()
        for blockchain in Blockchain:
            if name_upper == blockchain.name:
                return blockchain
        raise NameError(name)


class ContractAbi(enum.Enum):
    """Enumeration of supported contract ABIs.

    """
    STANDARD_TOKEN = 0
    PANTOS_TOKEN = 1
    PANTOS_HUB = 2
    PANTOS_FORWARDER = 3

    def get_file_name(self, blockchain: Blockchain) -> str:
        """Get the name of the contract ABI file.

        Parameters
        ----------
        blockchain : Blockchain
            The blockchain to get the contract ABI file name for.

        Returns
        -------
        str
            The name of the contract ABI file.

        """
        return f'{blockchain.name.lower()}_{self.name.lower()}.abi'

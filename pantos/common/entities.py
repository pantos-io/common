"""Module that defines Pantos entities.

"""
import dataclasses
import enum
import typing

from pantos.common.blockchains.enums import Blockchain
from pantos.common.types import Amount
from pantos.common.types import BlockchainAddress


@dataclasses.dataclass
class ServiceNodeBid:
    """Entity that represents a Pantos service node bid.

    Attributes
    ----------
    source_blockchain : Blockchain
        The source blockchain of token transfers covered by the
        service node bid.
    destination_blockchain : Blockchain
        The destination blockchain of token transfers covered by the
        service node bid.
    fee : Amount
        The service node's fee for a token transfer.
    execution_time : int
        The time (in seconds since the epoch) the service node has
        available for executing a token transfer on the source
        blockchain.
    valid_until : int
        The time (in seconds since the epoch) until which the bid is
        valid.
    signature : str
        The signature over the the service node's bid. The signature is over
        ```
        sig(fee,
             bid_valid_until,
             source_blockchain_id,
             destination_blockchain_id,
             execution_time)
        ```

    """
    source_blockchain: Blockchain
    destination_blockchain: Blockchain
    fee: Amount
    execution_time: int
    valid_until: int
    signature: str


@dataclasses.dataclass
class TokenDeploymentRequest:
    """Request data for submitting a new deployment request to the
    Pantos token creator service.

    Attributes
    ----------
    deployment_blockchain_ids : list of int
        The deployment blockchain ids.
    token_name : str
        The name of the token.
    token_symbol : str
        The symbol of the token.
    token_decimals : int
        The number of decimals of the token.
    token_pausable : bool
        If the token is pausable.
    token_burnable : bool
        If the token is burnable.
    token_supply : int
        The supply of the token.
    payment_blockchain_id : int
        The blockchain id of the blockchain where the deployment
        fee will be paid.
    payer_address : BlockchainAddress
        The blockchain address of the payer.
    deployment_fee : int
        The deployment fee to be paid.
    deployment_fee_signature : str
        The deployment fee signature.
    deployment_fee_valid_until : int
        The timestamp until when the deployment fee can be submitted
        to the token creator service (in seconds since the epoch).
    bid_fee : Amount
        The fee of the bid.
    bid_execution_time : int
        The execution time of the bid.
    bid_valid_until : int
        The time (in seconds since the epoch) until the
        service node is able to execute the token
        transfer on the source blockchain.
    bid_signature : str
        The signature of the bid given by the service node.
    payment_nonce : int
        The nonce of the payment.
    payment_valid_until : int
        The timestamp until when the payment can be submitted
        to the service node (in seconds since the epoch).
    payment_signature : str
        The signature of the payment.

    """
    deployment_blockchain_ids: typing.List[int]
    token_name: str
    token_symbol: str
    token_decimals: int
    token_pausable: bool
    token_burnable: bool
    token_supply: int
    payment_blockchain_id: int
    payer_address: BlockchainAddress
    deployment_fee: int
    deployment_fee_signature: str
    deployment_fee_valid_until: int
    bid_fee: Amount
    bid_execution_time: int
    bid_valid_until: int
    bid_signature: str
    payment_nonce: int
    payment_valid_until: int
    payment_signature: str


BlockchainAddressBidPair = typing.Tuple[BlockchainAddress, ServiceNodeBid]


class ServiceNodeTransferStatus(enum.IntEnum):
    """Enumeration of possible transfer status values.

    """
    ACCEPTED = 0
    FAILED = 1
    SUBMITTED = 2
    REVERTED = 3
    CONFIRMED = 4

    @staticmethod
    def from_name(name: str) -> 'ServiceNodeTransferStatus':
        """Convert a string to a ServiceNodeTransferStatus object
        (if possible).

        Parameters
        ----------
        name : str
            The name of the status to be converted.

        Raises
        ------
        NameError
            If the type conversion is not possible.

        """
        for status in ServiceNodeTransferStatus:
            if name.upper() == status.name:
                return status
        raise NameError(name)


class TransactionStatus(enum.Enum):
    """Enumeration of blockchain transaction status values.

    """
    UNINCLUDED = 0
    UNCONFIRMED = 1
    CONFIRMED = 2
    REVERTED = 3

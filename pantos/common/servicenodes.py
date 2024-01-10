"""Module for communicating with Pantos service nodes.

"""
import dataclasses
import typing
import uuid

import requests

from pantos.common.blockchains.enums import Blockchain
from pantos.common.entities import ServiceNodeBid
from pantos.common.entities import ServiceNodeTransferStatus
from pantos.common.exceptions import BaseError
from pantos.common.types import BlockchainAddress

_TRANSFER_RESOURCE = 'transfer'
_STATUS_RESOURCE = 'status'
_BID_RESOURCE = 'bids'


class ServiceNodeClientError(BaseError):
    """Exception class for all service node client errors.

    """
    pass


class ServiceNodeClient:
    """Client for communicating with Pantos service nodes.

    """
    @dataclasses.dataclass
    class SubmitTransferRequest:
        """Request data for submitting a new token transfer request to a
        Pantos service node.

        Attributes
        ----------
        service_node_url : str
            The chosen service node's base URL.
        source_blockchain: Blockchain
            The token transfer's source blockchain.
        destination_blockchain: Blockchain
            The token transfer's destination blockchain.
        sender_address: BlockchainAddress
            The address of the sender on the source blockchain.
        recipient_address: BlockchainAddress
            The address of the recipient on the destination blockchain.
        source_token_address: BlockchainAddress
            The address of the transferred token on the source
            blockchain.
        destination_token_address: BlockchainAddress
            The address of the transferred token on the destination
            blockchain.
        token_amount: int
            The amount of tokens to be transferred.
        service_node_bid: ServiceNodeBid
            The chosen service node bid.
        sender_nonce: int
            The unique sender nonce for the new token transfer.
        valid_until: int
            The timestamp until when the token transfer can be included
            on the source blockchain (in seconds since the epoch).
        signature: str
            The sender's signature for the new token transfer.

        """
        service_node_url: str
        source_blockchain: Blockchain
        destination_blockchain: Blockchain
        sender_address: BlockchainAddress
        recipient_address: BlockchainAddress
        source_token_address: BlockchainAddress
        destination_token_address: BlockchainAddress
        token_amount: int
        service_node_bid: ServiceNodeBid
        sender_nonce: int
        valid_until: int
        signature: str

    @dataclasses.dataclass
    class TransferStatusResponse:
        """Response data for checking the status of a transfer at a
        service node.

        Attributes
        ----------
        task_id: uuid.UUID
            The unique task ID of the token transfer.
        source_blockchain: Blockchain
            The token transfer's source blockchain.
        destination_blockchain: Blockchain
            The token transfer's destination blockchain.
        sender_address: BlockchainAddress
            The address of the sender on the source blockchain.
        recipient_address: BlockchainAddress
            The address of the recipient on the destination blockchain.
        source_token_address: BlockchainAddress
            The address of the transferred token on the source
            blockchain.
        destination_token_address: BlockchainAddress
            The address of the transferred token on the destination
            blockchain.
        token_amount: int
            The amount of tokens transferred.
        fee: int
            The fee paid to the service node for the transfer.
        status: ServiceNodeTransferStatus
            The service node transfer status.
        transfer_id: int
            The Pantos transfer ID.
        transaction_id: str
            The ID/hash of the token transfer's transaction.

        """
        task_id: uuid.UUID
        source_blockchain: Blockchain
        destination_blockchain: Blockchain
        sender_address: BlockchainAddress
        recipient_address: BlockchainAddress
        source_token_address: BlockchainAddress
        destination_token_address: BlockchainAddress
        token_amount: int
        fee: int
        status: ServiceNodeTransferStatus
        transfer_id: int
        transaction_id: str

    def submit_transfer(self, request: SubmitTransferRequest,
                        timeout: typing.Optional[float] = None) -> uuid.UUID:
        """Submit a new token transfer request to a Pantos service node.

        Parameters
        ----------
        request : SubmitTransferRequest
            The request data for a new token transfer.

        Returns
        -------
        uuid.UUID
            The service node's task ID.

        Raises
        ------
        ServiceNodeClientError
            If the token transfer request cannot be submitted
            successfully.

        """
        service_node_request = {
            'source_blockchain_id': request.source_blockchain.value,
            'destination_blockchain_id': request.destination_blockchain.value,
            'sender_address': request.sender_address,
            'recipient_address': request.recipient_address,
            'source_token_address': request.source_token_address,
            'destination_token_address': request.destination_token_address,
            'amount': request.token_amount,
            'bid': {
                'fee': request.service_node_bid.fee,
                'execution_time': request.service_node_bid.execution_time,
                'valid_until': request.service_node_bid.valid_until,
                'signature': request.service_node_bid.signature
            },
            'nonce': request.sender_nonce,
            'valid_until': request.valid_until,
            'signature': request.signature
        }
        transfer_url = self.__build_transfer_url(request.service_node_url)
        try:
            service_node_response = requests.post(transfer_url,
                                                  json=service_node_request,
                                                  timeout=timeout)
            # Raise an error in case of a 4xx or 5xx response status code
            service_node_response.raise_for_status()
            task_id = service_node_response.json()['task_id']
            return uuid.UUID(task_id)
        except (requests.exceptions.RequestException, KeyError):
            response_message = self.__read_response_message(
                service_node_response)
            raise ServiceNodeClientError(
                'unable to submit a new token transfer request',
                request=request, transfer_url=transfer_url,
                response_message=response_message)

    def bids(
            self, service_node_url: str, source_blockchain: Blockchain,
            destination_blockchain: Blockchain,
            timeout: typing.Optional[float] = None) \
            -> typing.List[ServiceNodeBid]:
        """Retrieve the bids of the service node found at the given
        service node url.

        Parameters
        ----------
        service_node_url : str
            The url of the service node.
        source_blockchain : Blockchain
            The source blockchain of the bid.
        destination_blockchain : Blockchain
            The destination blockchain of the bid.

        Returns
        -------
        list of ServiceNodeBid
            The list of service node bid given by the service node.

        Raises
        -------
        ServiceNodeClientError
            If unable to retrieve the bids.

        """
        bids_url = self.__build_bids_url(service_node_url,
                                         str(source_blockchain.value),
                                         str(destination_blockchain.value))
        try:
            service_node_response = requests.get(bids_url, timeout=timeout)
            service_node_response.raise_for_status()
            bids = service_node_response.json()
            response = []
            for bid in bids:
                response.append(
                    ServiceNodeBid(source_blockchain, destination_blockchain,
                                   bid['fee'], bid['execution_time'],
                                   bid['valid_until'], bid['signature']))
            return response
        except (requests.exceptions.RequestException, ValueError, KeyError):
            response_message = self.__read_response_message(
                service_node_response)
            raise ServiceNodeClientError(
                'unable to get the bids of the service node',
                service_node_url=service_node_url,
                source_blockchain=source_blockchain,
                destination_blockchain=destination_blockchain,
                response_message=response_message)

    def status(
            self, service_node_url: str, task_id: uuid.UUID,
            timeout: typing.Optional[float] = None) -> TransferStatusResponse:
        """Retrieve the status of a transfer.

        Parameters
        ----------
        service_node_url : str
            The url of the service node.
        task_id : uuid.UUID
            The task id of the transfer.

        Returns
        -------
        TransferStatusResponse
            The transfer status response.

        Raises
        ------
        ServiceNodeClientError
            If unable to get the status of a transfer.

        """
        status_url = self.__build_status_url(service_node_url, task_id)
        try:
            service_node_response = requests.get(status_url, timeout=timeout)
            service_node_response.raise_for_status()
            json_response = service_node_response.json()
            transfer_status_response = self.TransferStatusResponse(
                uuid.UUID(json_response['task_id']),
                Blockchain(json_response['source_blockchain_id']),
                Blockchain(json_response['destination_blockchain_id']),
                BlockchainAddress(json_response['sender_address']),
                BlockchainAddress(json_response['recipient_address']),
                BlockchainAddress(json_response['source_token_address']),
                BlockchainAddress(json_response['destination_token_address']),
                json_response['amount'], json_response['fee'],
                ServiceNodeTransferStatus.from_name(json_response['status']),
                json_response['transfer_id'], json_response['transaction_id'])
            return transfer_status_response
        except (requests.exceptions.RequestException, ValueError, KeyError):
            response_message = self.__read_response_message(
                service_node_response)
            raise ServiceNodeClientError(
                'unable to get the status of the transfer',
                service_node_url=service_node_url, task_id=task_id,
                response_message=response_message)

    def __build_transfer_url(self, service_node_url: str) -> str:
        transfer_url = service_node_url
        if not service_node_url.endswith('/'):
            transfer_url += '/'
        transfer_url += _TRANSFER_RESOURCE
        return transfer_url

    def __build_bids_url(self, service_node_url: str, source_blockchain: str,
                         destination_blockchain: str) -> str:
        bids_url = service_node_url
        if not service_node_url.endswith('/'):
            bids_url += '/'
        return (f'{bids_url}{_BID_RESOURCE}?'
                f'source_blockchain={source_blockchain}&'
                f'destination_blockchain={destination_blockchain}')

    def __build_status_url(self, service_node_url: str,
                           task_id: uuid.UUID) -> str:
        transfer_url = self.__build_transfer_url(service_node_url)
        return f'{transfer_url}/{str(task_id)}/{_STATUS_RESOURCE}'

    def __read_response_message(
            self, response: requests.Response) -> typing.Optional[str]:
        response_message = None
        if 'application/json' in response.headers.get('content-type', ''):
            response_message = response.json().get('message')
        return response_message

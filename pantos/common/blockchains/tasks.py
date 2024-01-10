import dataclasses
import logging
import typing
import uuid

import celery  # type: ignore
import celery.result  # type: ignore

from pantos.common.blockchains.base import BlockchainUtilities
from pantos.common.blockchains.base import MaxTotalFeePerGasExceededError
from pantos.common.blockchains.enums import Blockchain
from pantos.common.blockchains.factory import get_blockchain_utilities
from pantos.common.entities import TransactionStatus

_MAX_TRANSACTION_RESUBMISSION_TASK_RETRIES = 1000

TransactionResubmissionRequest = \
    BlockchainUtilities.TransactionResubmissionRequest

TransactionSubmissionResponse = \
    BlockchainUtilities.TransactionSubmissionResponse

TransactionSubmissionStartRequest = \
    BlockchainUtilities.TransactionSubmissionStartRequest

assert (sorted(
    field.name
    for field in dataclasses.fields(TransactionResubmissionRequest)) == sorted(
        field.name
        for field in dataclasses.fields(TransactionSubmissionStartRequest)
        if field.name != 'blocks_until_resubmission'))

_logger = logging.getLogger(__name__)


def create_transaction_resubmission_task(
        blockchain: Blockchain, request: TransactionSubmissionStartRequest,
        response: TransactionSubmissionResponse) -> uuid.UUID:
    """Create a new transaction resubmission task execution after the
    initial transaction submission.

    Parameters
    ----------
    blockchain : Blockchain
        The blockchain the transaction has been submitted to.
    request : TransactionSubmissionStartRequest
        The original request for starting the transaction submission.
    response : TransactionSubmissionResponse
        The response from the initial transaction submission.

    Returns
    -------
    uuid.UUID
        The internal transaction ID associated with the task.

    Raises
    ------
    Exception
        If Celery has an issue with submitting the new task.

    """
    internal_transaction_id = uuid.uuid4()
    blockchain_utilities = get_blockchain_utilities(blockchain)
    request = dataclasses.replace(
        request, min_adaptable_fee_per_gas=response.adaptable_fee_per_gas)
    request_dict = request.to_dict()
    del request_dict['blocks_until_resubmission']
    task_args = (blockchain.value, request.blocks_until_resubmission,
                 response.transaction_id, request_dict)
    task_id = str(internal_transaction_id)
    countdown = (blockchain_utilities.average_block_time *
                 request.blocks_until_resubmission)
    _transaction_resubmission_task.apply_async(args=task_args, task_id=task_id,
                                               countdown=countdown)
    return internal_transaction_id


def get_transaction_resubmission_task_result(
        internal_transaction_id: uuid.UUID) \
        -> typing.Optional[tuple[TransactionStatus, str]]:
    """Get the result of a transaction resubmission task execution.

    Parameters
    ----------
    internal_transaction_id : uuid.UUID
        The internal transaction ID associated with the task.

    Returns
    -------
    tuple or None
        None if the task has not yet finished, else a pair of the status
        and ID of the submitted transaction.

    Raises
    ------
    Exception
        If there has been an unresolvable error during the task
        execution.

    """
    task_id = str(internal_transaction_id)
    task_result = celery.result.AsyncResult(task_id)
    if not task_result.ready():
        return None
    assert task_result.state in ['SUCCESS', 'FAILURE']
    transaction_status_id, transaction_id = task_result.get(
        disable_sync_subtasks=False)
    return TransactionStatus(transaction_status_id), transaction_id


@celery.shared_task(bind=True,
                    max_retries=_MAX_TRANSACTION_RESUBMISSION_TASK_RETRIES)
def _transaction_resubmission_task(
        self, blockchain_id: int, blocks_until_resubmission: int,
        transaction_id: str,
        request_dict: dict[str, typing.Any]) -> tuple[int, str]:
    blockchain = Blockchain(blockchain_id)
    blockchain_utilities = get_blockchain_utilities(blockchain)
    task_info = request_dict | {
        'blockchain': blockchain,
        'blocks_until_resubmission': blocks_until_resubmission,
        'transaction_id': transaction_id,
        'internal_transaction_id': self.request.id
    }
    resubmission_countdown = (blockchain_utilities.average_block_time *
                              blocks_until_resubmission)
    confirmation_countdown = (
        blockchain_utilities.average_block_time *
        blockchain_utilities.required_transaction_confirmations)
    try:
        transaction_status = blockchain_utilities.read_transaction_status(
            transaction_id)
    except Exception as error:
        _logger.error('unable to read the transaction status', extra=task_info,
                      exc_info=True)
        raise self.retry(countdown=resubmission_countdown, exc=error)
    _logger.info(f'transaction {transaction_status.name.lower()}',
                 extra=task_info)
    if transaction_status is TransactionStatus.UNINCLUDED:
        request = TransactionResubmissionRequest.from_dict(request_dict)
        try:
            response = blockchain_utilities.resubmit_transaction(request)
        except MaxTotalFeePerGasExceededError as error:
            _logger.warning(
                'unable to further increase the adaptable fee per gas',
                extra=task_info)
            countdown = confirmation_countdown * self.request.retries
            raise self.retry(countdown=countdown, exc=error)
        except Exception as error:
            _logger.error('unable to resubmit a transaction', extra=task_info,
                          exc_info=True)
            raise self.retry(countdown=resubmission_countdown, exc=error)
        _logger.info(
            'adaptable fee per gas increased to '
            f'{response.adaptable_fee_per_gas}', extra=task_info)
        request.min_adaptable_fee_per_gas = response.adaptable_fee_per_gas
        task_args = (blockchain_id, blocks_until_resubmission,
                     response.transaction_id, request.to_dict())
        raise self.retry(args=task_args, countdown=resubmission_countdown)
    if transaction_status is TransactionStatus.UNCONFIRMED:
        raise self.retry(countdown=confirmation_countdown)
    assert transaction_status in [
        TransactionStatus.CONFIRMED, TransactionStatus.REVERTED
    ]
    return transaction_status.value, transaction_id

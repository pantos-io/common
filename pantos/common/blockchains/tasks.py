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
_MAX_DEPENDENT_TRANSACTION_CHECKS_TASK_RETRIES = 100

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


@celery.shared_task(bind=True,
                    max_retries=_MAX_DEPENDENT_TRANSACTION_CHECKS_TASK_RETRIES)
def _dependent_transaction_submission_task(
        self, blockchain_id: int, prerequisite_internal_id: str,
        blocks_to_wait: int, average_block_time: int,
        request: dict[str, typing.Any]) -> bool | str:
    """Task which checks the status of a prerequisite transaction and submits
    a dependent transaction if the prerequisite transaction is confirmed.

    Parameters
    ----------
    blockchain_id : int
        The ID of the blockchain the transactions are submitted to.
    prerequisite_internal_id : str
        The internal ID of the prerequisite transaction.
    blocks_to_wait : int
        The number of blocks to wait for the prerequisite transaction to be
        confirmed.
    average_block_time : int
        The average block time of the blockchain.
    request : dict
        The request for starting the dependent transaction submission. The dict
        should contain attributes of the TransactionSubmissionStartRequest
        class.

    Returns
    -------
    bool or str
        False if the prerequisite transaction has been reverted, else the
        internal ID of the dependent transaction.
    """
    blockchain = Blockchain(blockchain_id)
    blockchain_utils = get_blockchain_utilities(blockchain)
    prerequisite_internal_uuid = uuid.UUID(prerequisite_internal_id)
    status = blockchain_utils.get_transaction_submission_status(
        prerequisite_internal_uuid)

    task_info = {
        'blockchain': blockchain,
        'prerequisite_internal_id': prerequisite_internal_id,
        'required_blocks_to_wait': blocks_to_wait
    }

    if status.transaction_status in [
            TransactionStatus.UNCONFIRMED, TransactionStatus.UNINCLUDED
    ]:
        _logger.info(
            "Prerequisite transaction "
            "is not confirmed yet. Retrying...", extra=task_info)
        raise self.retry(countdown=average_block_time)
    task_info = task_info | {
        'prerequisite_transaction_id': status.transaction_id
    }
    if status.transaction_status == TransactionStatus.REVERTED:
        _logger.info("Prerequisite transaction reverted. Aborting...",
                     extra=task_info)
        return False

    if status.transaction_status == TransactionStatus.CONFIRMED:
        _logger.info("Prerequisite transaction is confirmed.", extra=task_info)
        try:
            transaction_status, number_of_confirmations = \
                blockchain_utils.get_number_of_confirmations(
                    status.transaction_id)  # type: ignore
            _logger.info(
                "No. of confirmations for prerequisite transaction: "
                f"{number_of_confirmations}", extra=task_info)
        except Exception:
            _logger.exception(
                "Unable to get number of confirmations "
                f"on {blockchain.name}. Going to retry...", extra=task_info)
            raise self.retry(countdown=average_block_time)
        if number_of_confirmations >= blocks_to_wait:
            # Submit the dependent transaction
            _logger.info("Submitting dependent transaction...")
            following_request = BlockchainUtilities \
                .TransactionSubmissionStartRequest.from_dict(request)
            return str(
                blockchain_utils.start_transaction_submission(
                    following_request))
    raise self.retry(countdown=average_block_time)

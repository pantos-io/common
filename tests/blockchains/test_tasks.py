import unittest.mock
import uuid

import pytest
from celery.exceptions import Retry  # type: ignore

from pantos.common.blockchains.base import BlockchainUtilities
from pantos.common.blockchains.base import BlockchainUtilitiesError
from pantos.common.blockchains.base import MaxTotalFeePerGasExceededError
from pantos.common.blockchains.base import ResultsNotMatchingError
from pantos.common.blockchains.factory import initialize_blockchain_utilities
from pantos.common.blockchains.tasks import \
    _dependent_transaction_submission_task
from pantos.common.blockchains.tasks import _transaction_resubmission_task
from pantos.common.blockchains.tasks import \
    create_transaction_resubmission_task
from pantos.common.blockchains.tasks import \
    get_transaction_resubmission_task_result
from pantos.common.entities import TransactionStatus


class _RetryError(Exception):
    def __init__(*args, **kwargs):
        # Accept any arguments
        pass


@unittest.mock.patch(
    'pantos.common.blockchains.tasks._transaction_resubmission_task')
def test_create_transaction_resubmission_task_correct(
        mock_transaction_resubmission_task, blockchain, blockchain_node_urls,
        fallback_blockchain_node_urls, average_block_time,
        required_transaction_confirmations, transaction_network_id,
        transaction_submission_start_request, transaction_submission_response):
    initialize_blockchain_utilities(blockchain, blockchain_node_urls,
                                    fallback_blockchain_node_urls,
                                    average_block_time,
                                    required_transaction_confirmations,
                                    transaction_network_id)
    internal_transaction_id = create_transaction_resubmission_task(
        blockchain, transaction_submission_start_request,
        transaction_submission_response)
    assert (str(internal_transaction_id) == mock_transaction_resubmission_task.
            apply_async.call_args.kwargs['task_id'])


@pytest.mark.parametrize(
    'transaction_status',
    [TransactionStatus.CONFIRMED, TransactionStatus.REVERTED])
@pytest.mark.parametrize('ready', [True, False])
@unittest.mock.patch('celery.result.AsyncResult')
def test_get_transaction_resubmission_task_result_correct(
        mock_async_result, ready, transaction_status, transaction_id):
    mock_async_result().ready.return_value = ready
    mock_async_result.return_value.state = 'SUCCESS'
    mock_async_result().get.return_value = (transaction_status.value,
                                            transaction_id)
    task_result = get_transaction_resubmission_task_result(uuid.uuid4())
    if ready:
        assert task_result[0] is transaction_status
        assert task_result[1] == transaction_id
    else:
        assert task_result is None


@unittest.mock.patch('celery.result.AsyncResult')
def test_get_transaction_resubmission_task_result_error(mock_async_result):
    mock_async_result.ready.return_value = True
    mock_async_result.return_value.state = 'FAILURE'
    mock_async_result().get.side_effect = Exception
    with pytest.raises(Exception):
        get_transaction_resubmission_task_result(uuid.uuid4())


@pytest.mark.parametrize('transaction_status', TransactionStatus)
@unittest.mock.patch(
    'pantos.common.blockchains.tasks.get_blockchain_utilities')
@unittest.mock.patch.object(_transaction_resubmission_task, 'retry',
                            _RetryError)
def test_transaction_resubmission_task_correct(
        mock_get_blockchain_utilities, transaction_status, blockchain,
        transaction_blocks_until_resubmission, transaction_id,
        transaction_resubmission_request_dict,
        transaction_resubmission_response):
    mock_get_blockchain_utilities().read_transaction_status.return_value = \
        transaction_status
    mock_get_blockchain_utilities().resubmit_transaction.return_value = \
        transaction_resubmission_response
    if transaction_status in [
            TransactionStatus.UNINCLUDED, TransactionStatus.UNCONFIRMED
    ]:
        with pytest.raises(_RetryError):
            _transaction_resubmission_task(
                blockchain.value, transaction_blocks_until_resubmission,
                transaction_id, transaction_resubmission_request_dict)
    else:
        task_result = _transaction_resubmission_task(
            blockchain.value, transaction_blocks_until_resubmission,
            transaction_id, transaction_resubmission_request_dict)
        assert task_result[0] == transaction_status.value
        assert task_result[1] == transaction_id


@unittest.mock.patch(
    'pantos.common.blockchains.tasks.get_blockchain_utilities')
@unittest.mock.patch.object(_transaction_resubmission_task, 'retry',
                            _RetryError)
def test_transaction_resubmission_task_read_transaction_status_error(
        mock_get_blockchain_utilities, blockchain,
        transaction_blocks_until_resubmission, transaction_id,
        transaction_resubmission_request_dict):
    mock_get_blockchain_utilities().read_transaction_status.side_effect = \
        BlockchainUtilitiesError
    with pytest.raises(_RetryError):
        _transaction_resubmission_task(blockchain.value,
                                       transaction_blocks_until_resubmission,
                                       transaction_id,
                                       transaction_resubmission_request_dict)


@pytest.mark.parametrize(
    'error', [MaxTotalFeePerGasExceededError, BlockchainUtilitiesError])
@unittest.mock.patch(
    'pantos.common.blockchains.tasks.get_blockchain_utilities')
@unittest.mock.patch.object(_transaction_resubmission_task, 'retry',
                            _RetryError)
def test_transaction_resubmission_task_resubmit_transaction_error(
        mock_get_blockchain_utilities, error, blockchain,
        transaction_blocks_until_resubmission, transaction_id,
        transaction_resubmission_request_dict):
    mock_get_blockchain_utilities().read_transaction_status.return_value = \
        TransactionStatus.UNINCLUDED
    mock_get_blockchain_utilities().resubmit_transaction.side_effect = error
    with pytest.raises(_RetryError):
        _transaction_resubmission_task(blockchain.value,
                                       transaction_blocks_until_resubmission,
                                       transaction_id,
                                       transaction_resubmission_request_dict)


@pytest.mark.parametrize(
    'transaction_status',
    [TransactionStatus.UNINCLUDED, TransactionStatus.UNCONFIRMED])
@unittest.mock.patch(
    'pantos.common.blockchains.tasks.get_blockchain_utilities')
def test_dependent_transaction_submission_task_prerequisite_tx_not_included(
        mocked_get_blockchain_utilities, transaction_status, blockchain,
        transaction_submission_start_request_dict, transaction_id):
    mocked_get_blockchain_utilities() \
        .get_transaction_submission_status.return_value = \
        BlockchainUtilities.TransactionSubmissionStatusResponse(
            False, transaction_status, transaction_id)

    with pytest.raises(Retry):
        _dependent_transaction_submission_task(
            blockchain.value, str(uuid.uuid4()), 0, 0,
            transaction_submission_start_request_dict)


@unittest.mock.patch(
    'pantos.common.blockchains.tasks.get_blockchain_utilities')
def test_dependent_transaction_submission_task_prerequisite_tx_reverted(
        mocked_get_blockchain_utilities, blockchain,
        transaction_submission_start_request_dict, transaction_id):
    mocked_get_blockchain_utilities() \
        .get_transaction_submission_status.return_value = \
        BlockchainUtilities.TransactionSubmissionStatusResponse(
            True, TransactionStatus.REVERTED, transaction_id)

    return_value = _dependent_transaction_submission_task(
        blockchain.value, str(uuid.uuid4()), 0, 0,
        transaction_submission_start_request_dict)

    assert return_value is False


@pytest.mark.parametrize('error',
                         [ResultsNotMatchingError, BlockchainUtilitiesError])
@unittest.mock.patch(
    'pantos.common.blockchains.tasks.get_blockchain_utilities')
def test_dependent_transaction_submission_task_prerequisite_tx_receipt_missing(
        mocked_get_blockchain_utilities, error, blockchain,
        transaction_submission_start_request_dict, transaction_id):

    mocked_get_blockchain_utilities() \
        .get_transaction_submission_status.return_value = \
        BlockchainUtilities.TransactionSubmissionStatusResponse(
            True, TransactionStatus.CONFIRMED, transaction_id)
    mocked_get_blockchain_utilities() \
        .get_number_of_confirmations.side_effect = error

    with pytest.raises(Retry):
        _dependent_transaction_submission_task(
            blockchain.value, str(uuid.uuid4()), 0, 0,
            transaction_submission_start_request_dict)


@unittest.mock.patch(
    'pantos.common.blockchains.tasks.get_blockchain_utilities')
def test_dependent_transaction_submission_task_submit_dependent_tx(
        mocked_get_blockchain_utilities, commit_wait_period, blockchain,
        transaction_submission_start_request_dict,
        transaction_submission_start_request, transaction_id):

    mocked_get_blockchain_utilities() \
        .get_transaction_submission_status.return_value = \
        BlockchainUtilities.TransactionSubmissionStatusResponse(
            True, TransactionStatus.CONFIRMED, transaction_id)
    mocked_get_blockchain_utilities() \
        .get_number_of_confirmations.return_value = \
        (TransactionStatus.CONFIRMED, commit_wait_period)

    _dependent_transaction_submission_task(
        blockchain.value, str(uuid.uuid4()), commit_wait_period, 0,
        transaction_submission_start_request_dict)

    mocked_get_blockchain_utilities(
    ).start_transaction_submission.assert_called_with(
        transaction_submission_start_request)


@unittest.mock.patch(
    'pantos.common.blockchains.tasks.get_blockchain_utilities')
def test_dependent_transaction_submission_task_prereq_tx_not_enough_confs(
        mocked_get_blockchain_utilities, commit_wait_period, blockchain,
        transaction_submission_start_request_dict,
        transaction_submission_start_request, transaction_id):

    mocked_get_blockchain_utilities() \
        .get_transaction_submission_status.return_value = \
        BlockchainUtilities.TransactionSubmissionStatusResponse(
            True, TransactionStatus.CONFIRMED, transaction_id)
    mocked_get_blockchain_utilities() \
        .get_number_of_confirmations.return_value = \
        (TransactionStatus.CONFIRMED, commit_wait_period / 2)

    with pytest.raises(Retry):
        _dependent_transaction_submission_task(
            blockchain.value, str(uuid.uuid4()), commit_wait_period, 0,
            transaction_submission_start_request_dict)

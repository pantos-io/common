import atexit
import dataclasses
import pathlib
import tempfile
import uuid

import pytest

from pantos.common.blockchains.base import BlockchainUtilities
from pantos.common.blockchains.base import VersionedContractAbi
from pantos.common.blockchains.enums import Blockchain
from pantos.common.blockchains.enums import ContractAbi

_ACCOUNT_ADDRESS = '0x352F6A5abD3564d5016336e5dA91389B7C47f6dd'

_ACCOUNT_KEYSTORE = (
    '{"address":"352f6a5abd3564d5016336e5da91389b7c47f6dd","crypto":{"cipher"'
    ':"aes-128-ctr","ciphertext":"452df17b9bb624246a66b16585c4aece1adefc30cc0'
    '0bfc6db3108a771b91033","cipherparams":{"iv":"b14fdbc0984c4b8d1769ff74d1e'
    'd8f79"},"kdf":"scrypt","kdfparams":{"dklen":32,"n":262144,"p":1,"r":8,"s'
    'alt":"4a094c0a4f152b3908854074e12c9eca2427d10bff5686a519626d6b07a7dc77"}'
    ',"mac":"58c24387604f78f55cd962da62681aba710e6aa4afea9d44b52ced29e7c317bd'
    '"},"id":"c69596a7-c2f6-4d37-a4fb-cefe4b3f432d","version":3}')

_ACCOUNT_KEYSTORE_PASSWORD = 'Mu(bK{!z'

_ACCOUNT_PRIVATE_KEY = \
    'cf10f5c9b5229dbcc5bee72d6309192da944dc837efb703581b5e91795adfab2'

_AVERAGE_BLOCK_TIME = 14

_COMMIT_WAIT_PERIOD = 10

_BLOCKCHAIN_NODE_URL = 'https://some.url'

_FALLBACK_BLOCKCHAIN_NODE_URL = 'https://some2.url'

_INACTIVE_BLOCKCHAINS = [Blockchain.SOLANA]

_REQUIRED_TRANSACTION_CONFIRMATIONS = 20

_TRANSACTION_NETWORK_ID = 1

_CONTRACT_ADDRESS = '0xB685E5B2b9fB7a3EbD196f4C0eb8B8AB6d589a12'

_TRANSACTION_FUNCTION_SELECTOR = '0xa9059c1b'

_TRANSACTION_FUNCTION_ARGS = (236421, 956782234, True)

_TRANSACTION_GAS = 90000

_TRANSACTION_MIN_ADAPTABLE_FEE_PER_GAS = int(1e8)

_TRANSACTION_MAX_TOTAL_FEE_PER_GAS = int(1e10)

_TRANSACTION_AMOUNT = int(1e16)

_TRANSACTION_NONCE = 6790134

_TRANSACTION_ADAPTABLE_FEE_INCREASE_FACTOR = 1.101

_TRANSACTION_BLOCKS_UNTIL_RESUBMISSION = 10

_TRANSACTION_ID = \
    '0xf8d93e2c7052875c7bfbaeb008c1988f30666a584ed544d9246b3b0a8287bd35'

_TRANSACTION_ADAPTABLE_FEE_PER_GAS = int(1.1e8)


@dataclasses.dataclass
class Account:
    address: str
    private_key: str
    keystore: str
    keystore_password: str
    keystore_path: pathlib.Path = dataclasses.field(init=False)

    def __post_init__(self):
        self.keystore_path = pathlib.Path(tempfile.mkstemp()[1])
        with self.keystore_path.open('w') as keystore_file:
            keystore_file.write(self.keystore)
        atexit.register(self.keystore_path.unlink)


@pytest.fixture(scope='package')
def account():
    return Account(_ACCOUNT_ADDRESS, _ACCOUNT_PRIVATE_KEY, _ACCOUNT_KEYSTORE,
                   _ACCOUNT_KEYSTORE_PASSWORD)


@pytest.fixture(scope='package', params=Blockchain)
def blockchain(request):
    return request.param


@pytest.fixture(scope='package')
def commit_wait_period():
    return _COMMIT_WAIT_PERIOD


@pytest.fixture(
    scope='package', params=[
        blockchain for blockchain in Blockchain
        if blockchain not in _INACTIVE_BLOCKCHAINS
    ])
def active_blockchain(request):
    return request.param


@pytest.fixture(scope='package')
def average_block_time():
    return _AVERAGE_BLOCK_TIME


@pytest.fixture(scope='package')
def blockchain_node_urls():
    return [_BLOCKCHAIN_NODE_URL]


@pytest.fixture(scope='package')
def fallback_blockchain_node_urls():
    return [_FALLBACK_BLOCKCHAIN_NODE_URL]


@pytest.fixture(scope='package')
def required_transaction_confirmations():
    return _REQUIRED_TRANSACTION_CONFIRMATIONS


@pytest.fixture(scope='package')
def transaction_network_id():
    return _TRANSACTION_NETWORK_ID


@pytest.fixture(scope='package')
def contract_address():
    return _CONTRACT_ADDRESS


@pytest.fixture(scope='package')
def transaction_function_selector():
    return _TRANSACTION_FUNCTION_SELECTOR


@pytest.fixture(scope='package')
def transaction_function_args():
    return _TRANSACTION_FUNCTION_ARGS


@pytest.fixture(scope='package', params=[None, _TRANSACTION_GAS])
def transaction_gas(request):
    return request.param


@pytest.fixture(scope='package')
def transaction_min_adaptable_fee_per_gas():
    return _TRANSACTION_MIN_ADAPTABLE_FEE_PER_GAS


@pytest.fixture(scope='package',
                params=[None, _TRANSACTION_MAX_TOTAL_FEE_PER_GAS])
def transaction_max_total_fee_per_gas(request):
    return request.param


@pytest.fixture(scope='package', params=[None, _TRANSACTION_AMOUNT])
def transaction_amount(request):
    return request.param


@pytest.fixture(scope='package')
def transaction_nonce():
    return _TRANSACTION_NONCE


@pytest.fixture(scope='package')
def transaction_adaptable_fee_increase_factor():
    return _TRANSACTION_ADAPTABLE_FEE_INCREASE_FACTOR


@pytest.fixture(scope='package')
def transaction_blocks_until_resubmission():
    return _TRANSACTION_BLOCKS_UNTIL_RESUBMISSION


@pytest.fixture(scope='package')
def transaction_id():
    return _TRANSACTION_ID


@pytest.fixture(scope='package')
def transaction_adaptable_fee_per_gas():
    return _TRANSACTION_ADAPTABLE_FEE_PER_GAS


@pytest.fixture(scope='package', params=ContractAbi)
def versioned_contract_abi(request, protocol_version):
    return VersionedContractAbi(request.param, protocol_version)


@pytest.fixture
def transaction_submission_request(contract_address, versioned_contract_abi,
                                   transaction_function_selector,
                                   transaction_function_args, transaction_gas,
                                   transaction_min_adaptable_fee_per_gas,
                                   transaction_max_total_fee_per_gas,
                                   transaction_amount, transaction_nonce):
    return BlockchainUtilities.TransactionSubmissionRequest(
        contract_address, versioned_contract_abi,
        transaction_function_selector, transaction_function_args,
        transaction_gas, transaction_min_adaptable_fee_per_gas,
        transaction_max_total_fee_per_gas, transaction_amount,
        transaction_nonce)


@pytest.fixture
def transaction_submission_response(transaction_id,
                                    transaction_adaptable_fee_per_gas):
    return BlockchainUtilities.TransactionSubmissionResponse(
        transaction_id, transaction_adaptable_fee_per_gas)


@pytest.fixture
def transaction_resubmission_request(
        contract_address, versioned_contract_abi,
        transaction_function_selector, transaction_function_args,
        transaction_gas, transaction_min_adaptable_fee_per_gas,
        transaction_max_total_fee_per_gas, transaction_amount,
        transaction_nonce, transaction_adaptable_fee_increase_factor):
    return BlockchainUtilities.TransactionResubmissionRequest(
        contract_address, versioned_contract_abi,
        transaction_function_selector, transaction_function_args,
        transaction_gas, transaction_min_adaptable_fee_per_gas,
        transaction_max_total_fee_per_gas, transaction_amount,
        transaction_nonce, transaction_adaptable_fee_increase_factor)


@pytest.fixture
def transaction_resubmission_request_dict(transaction_resubmission_request):
    return transaction_resubmission_request.to_dict()


@pytest.fixture
def transaction_resubmission_response(transaction_id,
                                      transaction_adaptable_fee_per_gas):
    return BlockchainUtilities.TransactionResubmissionResponse(
        transaction_id, transaction_adaptable_fee_per_gas)


@pytest.fixture
def transaction_submission_start_request(
        contract_address, versioned_contract_abi,
        transaction_function_selector, transaction_function_args,
        transaction_gas, transaction_min_adaptable_fee_per_gas,
        transaction_max_total_fee_per_gas, transaction_amount,
        transaction_nonce, transaction_adaptable_fee_increase_factor,
        transaction_blocks_until_resubmission):
    return BlockchainUtilities.TransactionSubmissionStartRequest(
        contract_address, versioned_contract_abi,
        transaction_function_selector, transaction_function_args,
        transaction_gas, transaction_min_adaptable_fee_per_gas,
        transaction_max_total_fee_per_gas, transaction_amount,
        transaction_nonce, transaction_adaptable_fee_increase_factor,
        transaction_blocks_until_resubmission)


@pytest.fixture
def transaction_submission_start_request_dict(
        transaction_submission_start_request):
    return transaction_submission_start_request.to_dict()


@pytest.fixture(scope='package')
def internal_transaction_id():
    return uuid.uuid4()

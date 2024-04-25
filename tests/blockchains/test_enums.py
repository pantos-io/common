import pytest

from pantos.common.blockchains.enums import Blockchain
from pantos.common.blockchains.enums import ContractAbi


@pytest.mark.parametrize(('blockchain', 'name_in_pascal_case'),
                         [(Blockchain.ETHEREUM, 'Ethereum'),
                          (Blockchain.BNB_CHAIN, 'BnbChain'),
                          (Blockchain.AVALANCHE, 'Avalanche')])
def test_blockchain_name_in_pascal_case_correct(blockchain,
                                                name_in_pascal_case):
    assert blockchain.name_in_pascal_case == name_in_pascal_case


@pytest.mark.parametrize('blockchain',
                         [blockchain for blockchain in Blockchain])
def test_blockchain_from_name_correct(blockchain):
    assert Blockchain.from_name(blockchain.name.lower()) is blockchain
    assert Blockchain.from_name(blockchain.name.upper()) is blockchain


def test_blockchain_from_name_error():
    with pytest.raises(NameError):
        Blockchain.from_name('unknown_blockchain')


@pytest.mark.parametrize(
    ('contract_abi', 'blockchain', 'file_name'),
    [(ContractAbi.PANTOS_HUB, Blockchain.ETHEREUM, 'ethereum_pantos_hub.abi'),
     (ContractAbi.STANDARD_TOKEN, Blockchain.BNB_CHAIN,
      'bnb_chain_standard_token.abi'),
     (ContractAbi.PANTOS_FORWARDER, Blockchain.CELO,
      'celo_pantos_forwarder.abi'),
     (ContractAbi.PANTOS_TOKEN, Blockchain.AVALANCHE,
      'avalanche_pantos_token.abi')])
def test_contract_abi_get_file_name_correct(contract_abi, blockchain,
                                            file_name):
    assert contract_abi.get_file_name(blockchain) == file_name

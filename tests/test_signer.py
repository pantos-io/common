from unittest.mock import MagicMock
from unittest.mock import patch

import pytest

from pantos.common.blockchains.enums import Blockchain
from pantos.common.signer import SignerError
from pantos.common.signer import get_signer


def test_signer_init_unable_to_load_key():
    with pytest.raises(SignerError):
        get_signer('', '')


@patch('pantos.common.signer._signer', None)
@patch('pantos.common.signer.Crypto')
@patch('pantos.common.signer.getpass')
def test_signer_load_signer_correct_path(mocked_getpass, mocked_crypto):
    get_signer('', None)

    mocked_getpass.getpass.assert_called_once_with(
        'Password for decrypting the pem file')
    mocked_crypto.PublicKey.ECC.import_key.assert_called_once_with(
        '', passphrase=mocked_getpass.getpass())


@patch('pantos.common.signer._signer', None)
@patch('pantos.common.signer.Crypto')
def test_signer_load_signer_correct_value(mocked_crypto):
    get_signer('test', 'mocked_password')

    mocked_crypto.Signature.eddsa.new.assert_called_once()


@patch('pantos.common.signer._signer', None)
@patch('pantos.common.signer.Crypto')
@patch('pantos.common.signer.getpass')
def test_signer_sign_message_correct(mocked_getpass, mocked_crypto):
    signer = get_signer('', None)

    signer.sign_message('')

    mocked_crypto.Signature.eddsa.new().sign.assert_called_once()


@patch('pantos.common.signer.Crypto')
@patch('pantos.common.signer.getpass')
def test_signer_sign_message_error(mocked_getpass, mocked_crypto):
    signer = get_signer('', None)
    message = MagicMock()
    message.encode.side_effect = Exception

    with pytest.raises(SignerError):
        signer.sign_message(message)


@patch('pantos.common.signer.Crypto')
@patch('pantos.common.signer.getpass')
def test_signer_verify_message_correct(mocked_getpass, mocked_crypto):
    signer = get_signer('', None)

    result = signer.verify_message('message', '')

    assert result is True


@patch('pantos.common.signer.Crypto')
@patch('pantos.common.signer.getpass')
def test_signer_verify_message_false(mocked_getpass, mocked_crypto):
    signer = get_signer('', None)

    result = signer.verify_message('message', 'signature')

    assert result is False


@patch('pantos.common.signer.Crypto')
@patch('pantos.common.signer.getpass')
def test_signer_verify_message_raises_exception(mocked_getpass, mocked_crypto):
    signer = get_signer('', None)

    message = MagicMock()
    message.encode.side_effect = Exception

    with pytest.raises(SignerError):
        signer.verify_message(message, '')


@patch('pantos.common.signer.Crypto')
@patch('pantos.common.signer.getpass')
def test_build_message(mocked_getpass, mocked_crypto):
    signer = get_signer('', None)

    message = signer.build_message('-', 0, 0, [Blockchain.ETHEREUM])

    assert message == '0-0-[<Blockchain.ETHEREUM: 0>]'

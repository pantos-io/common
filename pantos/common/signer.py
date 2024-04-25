import getpass
import typing

import Crypto.PublicKey.ECC
import Crypto.Signature.eddsa


class SignerError(Exception):
    """Exception class for signer errors.

    """
    def __init__(self, message: str, name: str = 'signer error',
                 **kwargs: typing.Any):
        """Construct a signer error.

        Parameters
        ----------
        message : str
            Explanation of the error.
        name : str
            Human-readable name of the error.
        **kwargs : dict
            Additional information about the error as keyword arguments.

        """
        super().__init__(message, name, **kwargs)


class _Signer:
    def __init__(self, pem_value: str, pem_password: str):
        """
        Constructor of Signer class.

        Parameters
        ----------
        pem_value : str
            Value of the encrypted private key.
        pem_password : str
            Password to unlock the PEM file.

        """
        self.__signer = self._load_signer(pem_value, pem_password)

    def sign_message(self, message: str) -> str:
        """Sign a message.

        Parameters
        ----------
        message : str
            The message to be signed.

        Returns
        -------
        str
            The signature of the message.

        Raises
        ------
        SignerError
            If the message cannot be signed.

        """
        try:
            message_bytes = message.encode()
            signature = self.__signer.sign(message_bytes)
            return signature.hex()
        except Exception:
            raise SignerError(
                f'unable to compute signature of message: {message}')

    def verify_message(self, message: str, signature: str) -> bool:
        """Verify that the message is valid (signed by the same
        private key).

        Parameters
        ----------
        message : str
            The message to be verified.
        signature : str
            The signature of the message.

        Returns
        -------
        bool
            If the signature of the message is valid.

        Raises
        ------
        SignerError
            If the message cannot be verified.

        """
        try:
            message_bytes = message.encode()
            try:
                self.__signer.verify(message_bytes, bytes.fromhex(signature))
                return True
            except ValueError:
                return False
        except Exception:
            raise SignerError(
                f'unable to verify signature of message {message}')

    def build_message(self, separator: str = '', *message_parts:
                      typing.Any) -> str:
        """Build a message.

        Parameters
        ----------
        message_parts : typing.Any
            Ordered number of message parts to be concatenated into one
            message.
        separator : str
            String which is separating each part of the message.

        Returns
        -------
        str
            The built message.

        """
        message = ''
        for message_part in message_parts:
            message += f'{str(message_part)}{separator}'
        # cutting of last separator
        return message[:-1]

    def _load_signer(
            self, pem_value: str,
            pem_password: str) -> Crypto.Signature.eddsa.EdDSASigScheme:
        """Load the EdDSA signer object from a password-encrypted pem file.
        The key must be on the curve Ed25519 or Ed448.

        Parameters
        ----------
        pem_value : str
            Value of the encrypted private key.
        pem_password : str
            Password to unlock the PEM file.

        Returns
        -------
        Crypto.Signature.eddsa.EdDSASigScheme
            An EdDSA signature object.

        Raises
        ------
        SignerError
            If the EdDSA signer cannot be loaded.

        """
        try:
            if pem_password is None:
                pem_password = getpass.getpass(
                    'Password for decrypting the pem file')

            private_key = Crypto.PublicKey.ECC.import_key(
                pem_value, passphrase=pem_password)
            return Crypto.Signature.eddsa.new(private_key,
                                              'rfc8032')  # type: ignore
        except SignerError:
            raise
        except Exception:
            raise SignerError('cannot load the private key')


_signer: typing.Optional[_Signer] = None


def get_signer(pem_value: str, pem_password: str) -> _Signer:
    """Get a _Signer object.

    Parameters
    ----------
    pem_value : str
        Value of the encrypted private key.
    pem_password : str
        Password to unlock the PEM file.

    Returns
    -------
    _Signer
        Signer object used for signing and verifying messages.

    Raises
    ------
    SignerError
        If the signer cannot be gotten.

    """
    global _signer
    if not _signer:
        _signer = _Signer(pem_value, pem_password)
    return _signer

"""Module that defines value object types.

"""
import collections.abc
import decimal
import typing


class BlockchainAddress(str):
    pass


class PrivateKey(str):
    pass


class TokenSymbol(str):
    pass


AccountId = typing.Union[BlockchainAddress, PrivateKey]

Amount = typing.Union[int, decimal.Decimal]

ContractFunctionArgs = collections.abc.Sequence[typing.Union[
    bool, int, str, collections.abc.Sequence[typing.Union[bool, int, str]]]]

TokenId = typing.Union[BlockchainAddress, TokenSymbol]

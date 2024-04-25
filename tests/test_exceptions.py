import itertools

import pytest

from pantos.common.exceptions import BaseError
from pantos.common.exceptions import ErrorCreator


class _SuperclassError(BaseError):
    pass


class _SubclassError(_SuperclassError):
    pass


class _SpecializedErrorWithMessage(_SuperclassError):
    _message = 'specialized error message'

    def __init__(self, **kwargs):
        super().__init__(self._message, **kwargs)


class _SpecializedErrorWithoutMessage(_SuperclassError):
    pass


class _Superclass(ErrorCreator[_SuperclassError]):
    pass


class _Subclass(_Superclass):
    @classmethod
    def get_error_class(cls):
        return _SubclassError


@pytest.mark.parametrize('third_kwarg', [None, ('third', True)])
@pytest.mark.parametrize('second_kwarg', [None, ('second', 'some text')])
@pytest.mark.parametrize('first_kwarg', [None, ('first', 100)])
@pytest.mark.parametrize(
    'specialized_error_class',
    [None, _SpecializedErrorWithMessage, _SpecializedErrorWithoutMessage])
def test_error_creator_create_error_correct(specialized_error_class,
                                            first_kwarg, second_kwarg,
                                            third_kwarg):
    set_custom_message = (specialized_error_class
                          is not _SpecializedErrorWithMessage)
    message = ('custom error message'
               if set_custom_message else specialized_error_class._message)
    kwargs = {
        kwarg[0]: kwarg[1]
        for kwarg in [first_kwarg, second_kwarg, third_kwarg]
        if kwarg is not None
    }
    error = _Subclass()._create_error(
        message if set_custom_message else None,
        specialized_error_class=specialized_error_class, **kwargs)
    assert isinstance(error, Exception)
    assert isinstance(error, BaseError)
    assert isinstance(error, _SuperclassError)
    assert isinstance(error, _SubclassError)
    if specialized_error_class is not None:
        assert isinstance(error, specialized_error_class)
    assert not any(
        isinstance(error, error_class) for error_class in
        [_SpecializedErrorWithMessage, _SpecializedErrorWithoutMessage]
        if error_class is not specialized_error_class)
    assert message in str(error)
    assert all(
        str(part) in str(error)
        for part in itertools.chain.from_iterable(kwargs.items()))

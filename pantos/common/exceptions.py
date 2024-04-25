"""Common generic exceptions and related classes for Pantos.

"""
import abc
import typing

from pantos.common.blockchains.enums import Blockchain

E = typing.TypeVar('E', bound='BaseError')


class ErrorCreator(abc.ABC, typing.Generic[E]):
    """Base class that helps to properly create Pantos errors for a
    hierachy of related classes (like business-logic interactors or
    blockchain clients/utilities).

    """
    @classmethod
    @abc.abstractmethod
    def get_error_class(cls) -> type[E]:
        """Get the main error class of the subclass in the class
        hierarchy.

        Returns
        -------
        type[E]
            The error class.

        """
        pass  # pragma: no cover

    def _create_error(self, message: typing.Optional[str] = None, *,
                      specialized_error_class: typing.Optional[type[E]] = None,
                      **kwargs: typing.Any) -> E:
        """Create an error that can be catched as both the subclass's
        main error and (if specified) the specialized error (as well as
        their supertypes).

        Parameters
        ----------
        message : str, optional
            An explanation of the error (only to be specified if neither
            the subclass's main error class nor the specialized error
            class provides a default message).
        specialized_error_class : type[E], optional
            The specialized error class.
        **kwargs : dict
            Additional information about the error as keyword arguments.

        Returns
        -------
        E
            The error.

        """
        error_class = self.get_error_class()
        error_classes: tuple[type[E], ...] = ()
        if specialized_error_class is not None:
            error_classes += (specialized_error_class, )
        error_classes += (error_class, )

        class Error(*error_classes):  # type: ignore
            pass

        Error.__name__ = (error_class.__name__ if specialized_error_class
                          is None else specialized_error_class.__name__)
        Error.__qualname__ = Error.__name__
        Error.__module__ = error_class.__module__
        return Error(
            **kwargs) if message is None else Error(message=message, **kwargs)


class BaseError(Exception):
    """Base exception class for all Pantos errors.

    Attributes
    ----------
    details : dict
        Additional information about the error.

    """
    def __init__(self, message: str, **kwargs: typing.Any):
        """Construct an error instance.

        Parameters
        ----------
        message : str
            An explanation of the error.
        **kwargs : dict
            Additional information about the error as keyword arguments.

        """
        super().__init__(message)
        self.details = kwargs

    def __str__(self) -> str:
        string = f'{super().__str__()}'
        if self.details is not None:
            for key, value in self.details.items():
                value = value.name if isinstance(value, Blockchain) else value
                string += f' - {key}: {value}'
        return string


class NotInitializedError(BaseError):
    """Error to be raised if a Pantos resource has not been properly
    initialized when it is requested to be used.

    """
    pass

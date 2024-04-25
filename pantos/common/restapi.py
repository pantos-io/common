"""Common REST API resources.

"""
import json
import typing

import flask
import flask_restful  # type: ignore


class Live(flask_restful.Resource):
    """Flask resource class which specifies the health/live REST endpoint.

    """
    def get(self):
        """Return null response with status 200 if the service is up
        and running.

        """
        return None


def ok_response(
        data: typing.Union[typing.Dict, typing.List]) -> flask.Response:
    """Create a Flask response given some data.

    Parameters
    ----------
    data : dict or list
        The data that will be wrapped in a Flask response.

    Returns
    -------
    flask.Resposnse
        The response object that is used by Flask.

    """
    return flask.Response(json.dumps(data), status=200,
                          mimetype='application/json')


def conflict(error_message: str):
    """Raise an HTTPException when a request conflicts
    with the current state of the server.

    Parameters
    ----------
    error_message : str
        The message of the error.

    Raises
    ------
    HTTPException
        HTTP exception raised with the code 409.

    """
    flask_restful.abort(409, message=error_message)


def not_acceptable(error_message: typing.Union[typing.List[typing.Any],
                                               typing.Dict[typing.Any,
                                                           typing.Any]]):
    """Raise an HTTPException for non-acceptable requests.

    Parameters
    ----------
    error_message : str
        The message of the error.

    Raises
    ------
    HTTPException
        HTTP exception raised with the code 406.

    """
    flask_restful.abort(406, message=error_message)


def bad_request(error_message: typing.Union[typing.List[typing.Any],
                                            typing.Dict[typing.Any,
                                                        typing.Any]]):
    """Raise an HTTPException for bad requests.

    Parameters
    ----------
    error_message : str
        The message of the error.

    Raises
    ------
    HTTPException
        HTTP exception raised with the code 400.

    """
    flask_restful.abort(400, message=error_message)


def resource_not_found(error_message: str):
    """Raise an HTTPException if the resource has not been found.

    Parameters
    ----------
    error_message : str
        The message of the error.

    Raises
    ------
    HTTPException
        HTTP exception raised with the code 404.

    """
    flask_restful.abort(404, message=error_message)


def internal_server_error(error_message: typing.Optional[str] = None):
    """Raise an HTTPException for internal server errors.

    Parameters
    ----------
    error_message : str
        The message of the error (optional).

    Raises
    ------
    HTTPException
        HTTP exception raised with the code 500.

    """
    flask_restful.abort(500, message=error_message)

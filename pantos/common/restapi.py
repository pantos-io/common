"""Common REST API resources.

"""
import dataclasses
import json
import logging

import flask  # type: ignore
import flask_restful  # type: ignore

from pantos.common.exceptions import NotInitializedError
from pantos.common.health import check_blockchain_nodes_health

_logger = logging.getLogger(__name__)
"""Logger for this module."""


class Live(flask_restful.Resource):
    """Flask resource class which specifies the health/live REST endpoint.

    """
    def get(self):
        """Return null response with status 200 if the service is up
        and running.

        """
        return None  # pragma: no cover


class NodesHealthResource(flask_restful.Resource):
    """RESTful resource for the health status of the blockchain nodes.

    """
    def get(self):
        """Return the health status of the blockchain nodes.

        """
        try:
            _logger.info('checking blockchain nodes health')
            nodes_health = check_blockchain_nodes_health()
            return ok_response({
                blockchain.name.capitalize(): dataclasses.asdict(
                    nodes_health[blockchain])
                for blockchain in nodes_health
            })
        except NotInitializedError:
            _logger.warning('no blockchain nodes have been initialized yet')
            return internal_server_error(
                'no blockchain nodes have been initialized yet')
        except Exception:
            _logger.critical('cannot check blockchain nodes health',
                             exc_info=True)
            return internal_server_error()


def ok_response(data: list | dict) -> flask.Response:
    """Create a Flask response given some data.

    Parameters
    ----------
    data : list or dict
        The data that will be wrapped in a Flask response.

    Returns
    -------
    flask.Response
        The Flask response object.

    """
    return flask.Response(json.dumps(data), status=200,
                          mimetype='application/json')


def no_content_response() -> flask.Response:
    """Create a Flask response for a successful request without any
    content.

    Returns
    -------
    flask.Response
        The Flask response object.

    """
    return flask.Response(status=204)


def conflict(error_message: str):
    """Raise an HTTPException when a request conflicts
    with the current state of the server.

    Parameters
    ----------
    error_message : str
        The error message.

    Raises
    ------
    HTTPException
        HTTP exception raised with the code 409.

    """
    flask_restful.abort(409, message=error_message)


def not_acceptable(error_messages: str | list | dict):
    """Raise an HTTPException for non-acceptable requests.

    Parameters
    ----------
    error_messages : str or list or dict
        The error messages.

    Raises
    ------
    HTTPException
        HTTP exception raised with the code 406.

    """
    flask_restful.abort(406, message=error_messages)


def bad_request(error_messages: str | list | dict):
    """Raise an HTTPException for bad requests.

    Parameters
    ----------
    error_messages : str or list or dict
        The error messages.

    Raises
    ------
    HTTPException
        HTTP exception raised with the code 400.

    """
    flask_restful.abort(400, message=error_messages)


def forbidden(error_message: str):
    """Raise an HTTPException if a prohibited action is refused.

    Parameters
    ----------
    error_message : str
        The error message.

    Raises
    ------
    HTTPException
        HTTP exception raised with the code 403.

    """
    flask_restful.abort(403, message=error_message)


def resource_not_found(error_message: str):
    """Raise an HTTPException if the resource has not been found.

    Parameters
    ----------
    error_message : str
        The error message.

    Raises
    ------
    HTTPException
        HTTP exception raised with the code 404.

    """
    flask_restful.abort(404, message=error_message)


def internal_server_error(error_message: str | None = None):
    """Raise an HTTPException for internal server errors.

    Parameters
    ----------
    error_message : str, optional
        The error message.

    Raises
    ------
    HTTPException
        HTTP exception raised with the code 500.

    """
    flask_restful.abort(500, message=error_message)

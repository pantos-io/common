"""Common REST API resources.

"""
import dataclasses
import json
import logging

import flask  # type: ignore
import flask_restful  # type: ignore
import marshmallow

from pantos.common.exceptions import NotInitializedError
from pantos.common.health import check_blockchain_nodes_health

_logger = logging.getLogger(__name__)
"""Logger for this module."""


class _UnhealthyNodeSchema(marshmallow.Schema):
    node_domain = marshmallow.fields.String(
        required=True, description="The domain of the unhealthy node")
    status = marshmallow.fields.String(
        required=True, description="The status of the unhealthy node")


class _BlockchainStatusSchema(marshmallow.Schema):
    healthy_total = marshmallow.fields.Int(
        required=True, description="The total number of healthy nodes")
    unhealthy_total = marshmallow.fields.Int(
        required=True, description="The total number of unhealthy nodes")
    unhealthy_nodes = marshmallow.fields.List(
        marshmallow.fields.Nested(_UnhealthyNodeSchema), required=True,
        description="A list of unhealthy nodes")


def create_blockchain_health_response_schema(blockchain_names: list):
    """Dynamically create a schema with blockchain names as top-level keys."""
    fields_dict = {
        name: marshmallow.fields.Nested(_BlockchainStatusSchema,
                                        required=False)
        for name in blockchain_names
    }

    return type(
        "_BlockchainHealthResponseSchema",
        (marshmallow.Schema, ),
        fields_dict,
    )


class Live(flask_restful.Resource):
    """Flask resource class which specifies the health/live REST endpoint.

    """
    def get(self):
        """
        Endpoint that verify the liveness of the service.
        ---
        tags:
            - Health
            - Live
        responses:
            200:
                description: The service is up and running.
            default:
                description: Unexpected error.
        """
        return None  # pragma: no cover


class NodesHealthResource(flask_restful.Resource):
    """RESTful resource for the health status of the blockchain nodes.

    """
    def get(self):
        """
        Endpoint that returns an Json object with the health status of the
        blockchain nodes used by the service.
        ---
        tags:
            - Health
            - NodesHealth
        responses:
            200:
                description: Health status of blockchain nodes used by the
                    service.
                content:
                  application/json:
                    schema:
                      $ref: '#/components/schemas/_BlockchainHealthResponse'
            500:
                description: Either internal error or blockchains nodes have
                    not been initialized yet.
                content:
                    application/json:
                        type: string
                        items:
                            type: string
                        example: {'message': 'no blockchain nodes have been \
                            initialized yet'}
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


class _400ErrorSchema(marshmallow.Schema):
    """Validation schema for 4XX error messages.

    """
    message = marshmallow.fields.Dict(keys=marshmallow.fields.Str(),
                                      values=marshmallow.fields.Str(),
                                      required=True)


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

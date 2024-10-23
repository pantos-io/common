import pytest

from pantos.common.protocol import get_supported_protocol_versions


@pytest.fixture(scope='session', params=get_supported_protocol_versions())
def protocol_version(request):
    return request.param

import pytest

from pantos.common.entities import ServiceNodeTransferStatus


@pytest.mark.parametrize('name, status',
                         [('accepted', ServiceNodeTransferStatus.ACCEPTED),
                          ('failed', ServiceNodeTransferStatus.FAILED),
                          ('submitted', ServiceNodeTransferStatus.SUBMITTED),
                          ('reverted', ServiceNodeTransferStatus.REVERTED),
                          ('confirmed', ServiceNodeTransferStatus.CONFIRMED)])
def test_service_node_transfer_status_from_name_correct(name, status):
    assert ServiceNodeTransferStatus.from_name(name) == status


def test_service_node_transfer_status_from_name_raises_error():
    with pytest.raises(NameError):
        ServiceNodeTransferStatus.from_name('confirmedz')

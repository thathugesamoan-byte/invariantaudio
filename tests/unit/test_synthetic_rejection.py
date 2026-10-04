# SPDX-License-Identifier: GPL-3.0-or-later
import pytest
from invariantaudio.approvals.manifests import validate_synthetic_id_rejection

def test_reject_synthetic_uuids():
    with pytest.raises(ValueError, match="SYNTHETIC_UUID_REJECTED"):
        validate_synthetic_id_rejection("b1b1c1d1-0000-4000-8000-000000000001")

def test_accept_genuine_uuid():
    genuine = "6cf962c9-e695-4bbe-b795-c013a127fb50"
    assert validate_synthetic_id_rejection(genuine) is True

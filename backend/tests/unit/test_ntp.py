import pytest
from app.platform.distributed.clock.ntp_client import NTPClient
import ntplib

def test_ntp_sync_empty_servers(monkeypatch):
    from app.platform.core.config import settings
    monkeypatch.setattr(settings, "NTP_SERVERS", "")
    client = NTPClient()
    # Should not raise exception
    client.force_sync()
    assert client._offset == 0.0

def test_ntp_sync_success(monkeypatch):
    from app.platform.core.config import settings
    monkeypatch.setattr(settings, "NTP_SERVERS", "pool.ntp.org")
    class MockNTPResponse:
        offset = 1.5

    client = NTPClient()
    client.servers = ["pool.ntp.org"]
    client.ntp_client.request = lambda *args, **kwargs: MockNTPResponse()
    client.force_sync()
    assert client._offset == 1.5

def test_ntp_sync_failure(monkeypatch):
    from app.platform.core.config import settings
    monkeypatch.setattr(settings, "NTP_SERVERS", "pool.ntp.org")
    client = NTPClient()
    client.servers = ["pool.ntp.org"]
    def mock_request(*args, **kwargs):
        raise ntplib.NTPException("Mock timeout")
    client.ntp_client.request = mock_request
    client.force_sync()
    assert client._offset == 0.0

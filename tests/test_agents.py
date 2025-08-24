import pytest


def test_health(client):
    r = client.get('/health')
    assert r.status_code == 200

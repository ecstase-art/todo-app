import pytest
from app import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_home_page(client):
    response = client.get('/')
    assert response.status_code == 200
    assert b'\xd0\xa1\xd0\xbf\xd0\xb8\xd1\x81\xd0\xbe\xd0\xba \xd0\xb7\xd0\xb0\xd0\xb4\xd0\xb0\xd1\x87' in response.data

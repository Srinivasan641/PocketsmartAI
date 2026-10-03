import os, tempfile, pytest
from pathlib import Path
os.environ['DATABASE_URL']='sqlite:///test_pocketsmart.db'
os.environ['SECRET_KEY']='test-secret-key'
from database import DB_PATH, init_db
import main
from fastapi.testclient import TestClient

@pytest.fixture(autouse=True)
def reset_db():
    if DB_PATH.exists(): DB_PATH.unlink()
    init_db()
    yield
    if DB_PATH.exists(): DB_PATH.unlink()

@pytest.fixture
def client():
    return TestClient(main.app)

@pytest.fixture
def auth_client(client):
    r=client.post('/register',json={'username':'tester','email':'tester@example.com','password':'secret123','confirm_password':'secret123'})
    assert r.status_code==200
    return client

def test_register_login_logout(client):
    r=client.post('/register',json={'username':'alice','email':'alice@example.com','password':'secret123','confirm_password':'secret123'})
    assert r.status_code==200
    assert client.get('/session-info').status_code==200
    r=client.post('/logout'); assert r.status_code==200
    assert client.get('/session-info').status_code==401
    r=client.post('/login',json={'username':'alice','password':'secret123'}); assert r.status_code==200

def test_protected_route(client):
    assert client.get('/dashboard').status_code==401

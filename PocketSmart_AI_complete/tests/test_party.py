def test_party_planner(auth_client):
    r=auth_client.post('/generate-party',json={'total_budget':10000,'guests':50,'event_type':'Birthday','venue_type':'Home','catering':True,'decoration':True,'entertainment':True,'additional_requirements':''})
    assert r.status_code==200
    assert r.json()['result']['remaining_budget']>=0

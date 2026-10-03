def test_history_and_details(auth_client):
    auth_client.post('/generate-home',json={'total_budget':2000,'room_details':'Bedroom','lighting_requirements':1,'ceiling_fan_requirements':0,'furniture_requirements':'','table_quantity':0,'preferences':'Minimal','additional_requirements':''})
    h=auth_client.get('/history'); assert h.status_code==200 and 'Recommendation History' in h.text
    data=auth_client.get('/history-data').json(); assert len(data['history'])==1
    rid=data['history'][0]['id']; d=auth_client.get(f'/recommendations-details/{rid}'); assert d.status_code==200

def test_home_planner(auth_client):
    r=auth_client.post('/generate-home',json={'total_budget':5000,'room_details':'Living room','lighting_requirements':2,'ceiling_fan_requirements':1,'furniture_requirements':'Table and chairs','table_quantity':1,'preferences':'Modern','additional_requirements':''})
    assert r.status_code==200
    data=r.json()['result']; assert data['remaining_budget']>=0
    assert sum(i['estimated_price']*i['quantity'] for a in data['allocations'] for i in a['items']) <= 5000.01

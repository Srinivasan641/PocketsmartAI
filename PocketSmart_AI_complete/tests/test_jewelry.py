def test_jewelry_planner(auth_client):
    r=auth_client.post('/generate-jewelry',data={'budget':'3000','occasion':'Wedding','style_preference':'Traditional','outfit_description':'Blue silk saree'})
    assert r.status_code==200
    assert r.json()['result']['planner_type']=='jewelry'

def test_jewelry_image_upload(auth_client):
    # Minimal valid PNG bytes (1x1)
    png=bytes.fromhex('89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4890000000d49444154789c6360000000020001e221bc330000000049454e44ae426082')
    r=auth_client.post('/generate-jewelry',data={'budget':'3000','occasion':'Party','style_preference':'Minimal','outfit_description':''},files={'image':('outfit.png',png,'image/png')})
    assert r.status_code==200

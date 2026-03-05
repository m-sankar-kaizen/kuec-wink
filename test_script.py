import xmlrpc.client
url = 'http://localhost:8069'
db = 'sali7kaizena-kuec-portal1-dev-29336026'
username = 'admin'
password = 'admin'
try:
    common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
    uid = common.authenticate(db, username, password, {})
    if not uid:
        print('DB Auth failed for', db)
        import urllib.request, json
        req = urllib.request.Request(f'{url}/web/database/list', data=json.dumps({'params':{}}).encode('utf-8'), headers={'Content-Type': 'application/json'})
        resp = urllib.request.urlopen(req)
        print('Available DBs:', json.loads(resp.read().decode('utf-8')).get('result'))
    else:
        models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')
        
        # Look for S00055
        orders = models.execute_kw(db, uid, password, 'sale.order', 'search_read', [[('name', '=', 'S00055')]], {'fields': ['id', 'name', 'amount_total', 'state', 'wink_price_confirmed', 'order_line']})
        print('Order S00055:', orders)
        
        if orders:
            line_ids = orders[0].get('order_line', [])
            lines = models.execute_kw(db, uid, password, 'sale.order.line', 'read', [line_ids], {'fields': ['product_id', 'price_unit', 'price_subtotal', 'name']})
            print('Order Lines:', lines)
except Exception as e:
    print(f'Error: {e}')

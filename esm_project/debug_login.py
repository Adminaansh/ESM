import json
import urllib.request
import urllib.error

url='http://127.0.0.1:8000/api/v1/auth/login/'
req=urllib.request.Request(url, data=json.dumps({'username':'admin','password':'admin123'}).encode('utf-8'), headers={'Content-Type':'application/json'})
try:
    with urllib.request.urlopen(req, timeout=10) as resp:
        print('STATUS', resp.getcode())
        print(resp.read().decode())
except urllib.error.HTTPError as e:
    print('HTTPError', e.code)
    try:
        print(e.read().decode())
    except Exception:
        print('No body')
except Exception as e:
    print('ERROR', repr(e))

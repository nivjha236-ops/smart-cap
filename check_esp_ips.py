import requests

for ip in ['10.26.35.113', '10.26.35.22']:
    try:
        r = requests.get(f'http://{ip}/', stream=True, timeout=2)
        ct = r.headers.get('content-type', 'unknown')
        print(f"{ip} -> Content-Type: {ct}")
        r.close()
    except Exception as e:
        print(f"{ip} -> Error: {e}")

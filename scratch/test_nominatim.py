import requests

def test():
    address = "AV. LEON VELARDE 123"
    location = ', PUERTO MALDONADO, MADRE DE DIOS, PERÚ'
    params = {
        "q": address + location,
        "format": "json",
        "addressdetails": 1,
        "limit": 1
    }
    headers = {
        "User-Agent": "HydraBackend/2.0"
    }
    print(f"Testing URL: https://nominatim.openstreetmap.org/search?q={params['q']}")
    r = requests.get("https://nominatim.openstreetmap.org/search", params=params, headers=headers)
    print(f"Status Code: {r.status_code}")
    try:
        print(r.json())
    except Exception as e:
        print("Error parsing JSON:", e)

if __name__ == '__main__':
    test()

import requests


def test_hubeau_endpoints():
    """Test the 3 endpoints using V2 API"""
    
    base_url = "https://hubeau.eaufrance.fr/api/v2/qualite_rivieres"
    
    endpoints = {
        "Stations": "/station_pc",
        "Analyses": "/analyse_pc",
        "Parametres": "/operation_pc"
    }

    for name, endpoint in endpoints.items():
        print(f"\n--- Testing {name} Endpoint ---")
        url = f"{base_url}{endpoint}"
        
        # Test parameters (limit to 1 to just see the structure)
        params = {
            "size": 1
        }
        
        try:
            print(f"GET {url}")
            response = requests.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            print(f"✅ Success. Total records available: {data.get('count', 'Unknown')}")
            
            # Print the schema of the first item
            if data.get('data') and len(data['data']) > 0:
                first_item = data['data'][0]
                print(f"Sample fields: {list(first_item.keys())[:5]} ...")
                
        except Exception as e:
            print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    test_hubeau_endpoints()

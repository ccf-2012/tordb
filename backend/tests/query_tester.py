import requests
import json

# The URL of your locally running FastAPI server
API_URL = "http://127.0.0.1:6009/api/query"

# --- Define your test cases here ---
# Each item in the list is a dictionary representing the JSON payload to send.
# The `torname` is the only required field.
test_cases = [
    {
        "torname": "The Matrix 1999 2160p UHD BluRay TrueHD 7.1 x265-ABC",
        "subtitle": "The.Matrix.1999.2160p.UHD.BluRay.x265.10bit.HDR.TrueHD.7.1.Atmos-ABC",
    },
    {
        "torname": "The.Mandalorian.S03E01.2023.1080p.WEB-DL.DDP5.1.Atmos.H.264-XYZ",
        "subtitle": "The Mandalorian S03E01 Chapter 17 The Apostate",
    },
    {
        "torname": "Dune Part Two 2024",
        "tmdbstr": "movie-693134"  # Example of forcing a specific TMDb ID
    },
    {
        "torname": "Love Letter 2024 1080p WEB-DL H.264-CDE",
    },
    # -- Add more test cases below --
    # {
    #     "torname": "Your Test Torrent Name Here",
    #     "subtitle": "Optional subtitle info"
    # },
]


def run_tests():
    """Iterates through the test cases and prints the API response."""
    headers = {"Content-Type": "application/json"}
    
    for i, payload in enumerate(test_cases):
        print(f"--- Test Case {i+1} ---")
        print(f"Sending payload:\n{json.dumps(payload, indent=2)}\n")
        
        try:
            response = requests.post(API_URL, headers=headers, data=json.dumps(payload))
            
            print(f"Status Code: {response.status_code}")
            
            if response.status_code == 200:
                print("Response JSON:")
                # Pretty-print the JSON response
                print(json.dumps(response.json(), indent=2, ensure_ascii=False))
            else:
                print(f"Error Response: {response.text}")
                
        except requests.exceptions.RequestException as e:
            print(f"An error occurred: {e}")
            
        print("\n" + "="*40 + "\n")

if __name__ == "__main__":
    print(f"Starting tests against {API_URL}\n")
    run_tests()

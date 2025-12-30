import requests
import json
import datetime

import os
# User provided API KEY
API_KEY = os.getenv("DART_API_KEY", "YOUR_DART_API_KEY_HERE")

def get_recent_disclosures():
    url = "https://opendart.fss.or.kr/api/list.json"
    
    # Get Date formatted as eq YYYYMMDD
    today = datetime.datetime.now()
    week_ago = today - datetime.timedelta(days=7)
    bgn_de = week_ago.strftime("%Y%m%d")
    
    params = {
        "crtfc_key": API_KEY,
        "bgn_de": bgn_de,
        "page_count": 10,  # Just get 10 items for testing
        "pblntf_detail_ty": "B001" # Filter for Major Reports (주요사항보고서) often containing CB/BW
    }

    try:
        response = requests.get(url, params=params)
        data = response.json()
        
        status = data.get('status')
        message = data.get('message')
        
        if status == '000':
            print("✅ DART API Connection Successful!")
            print(f"Server Message: {message}")
            print("\n[Recent Major Reports (Potential Toxic Clause Targets)]")
            if 'list' in data:
                for item in data['list']:
                    print(f"- [{item['corp_name']}] {item['report_nm']} (Receipt No: {item['rcept_no']})")
                    if "전환사채" in item['report_nm']:
                         print(f"   *** TARGET FOUND: Convertible Bond Issuance detected! ***")
            else:
                print("No list data found.")
        else:
            print("❌ DART API Error")
            print(f"Status: {status}")
            print(f"Message: {message}")
            
    except Exception as e:
        print(f"❌ Connection Failed: {e}")

if __name__ == "__main__":
    get_recent_disclosures()

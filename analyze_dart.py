import requests
import io
import zipfile
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
import re
import datetime

API_KEY = "577d4d3fff35faf9705ef7383b323d98e87a84bd"

def find_cb_disclosure():
    """Find the most recent Convertible Bond issuance report."""
    print("🔍 Searching for recent Convertible Bond (CB) reports...")
    url = "https://opendart.fss.or.kr/api/list.json"
    
    # Check up to 30 days back to find a good example
    today = datetime.datetime.now()
    start_dt = today - datetime.timedelta(days=30)
    bgn_de = start_dt.strftime("%Y%m%d")
    
    params = {
        "crtfc_key": API_KEY,
        "bgn_de": bgn_de,
        "page_count": 50,
        "pblntf_detail_ty": "B001" # Major Report
    }
    
    try:
        resp = requests.get(url, params=params).json()
        if resp['status'] != '000' or 'list' not in resp:
            print(f"❌ Search failed: {resp.get('message')}")
            return None

        # Filter for "전환사채" in result title
        for item in resp['list']:
            if "전환사채" in item['report_nm']:
                print(f"✅ Found Target: [{item['corp_name']}] {item['report_nm']}")
                return item['rcept_no']
        
        print("⚠️ No CB issuance found in the last 30 days.")
        return None
        
    except Exception as e:
        print(f"❌ Error during search: {e}")
        return None

def download_and_parse(rcept_no):
    """Download the document ZIP and search for toxic clauses."""
    print(f"📥 Downloading document {rcept_no}...")
    url = "https://opendart.fss.or.kr/api/document.xml"
    params = {"crtfc_key": API_KEY, "rcept_no": rcept_no}
    
    try:
        resp = requests.get(url, params=params)
        # Handle ZIP file in memory
        with zipfile.ZipFile(io.BytesIO(resp.content)) as z:
            # Usually the main report is the first XML or HTML file in the zip
            file_list = z.namelist()
            print(f"   Files in ZIP: {file_list}")
            
            target_file = None
            for f in file_list:
                if f.endswith('.xml') or f.endswith('.html'):
                    target_file = f
                    break
            
            if not target_file:
                print("❌ No parseable file found in ZIP.")
                return

            print(f"👀 Parsing {target_file}...")
            content = z.read(target_file)
            
            # Use BS4 to strip tags and find text
            soup = BeautifulSoup(content, 'html.parser')
            text = soup.get_text('\n')
            
            analyze_text(text)
            
    except Exception as e:
        print(f"❌ Error during download/parsing: {e}")

def analyze_text(text):
    """Simple keyword analysis for toxic clauses."""
    print("\n🕵️ Analyzing for Toxic Clauses...\n")
    
    # Keywords to look for
    keywords = {
        "Refixing (Low Price)": [r"조정가액", r"조정후", r"리픽싱", r"70%", r"액면가"],
        "Call Option": [r"매도청구권", r"콜옵션", r"Call Option", r"최대주주"],
        "Put Option": [r"조기상환", r"풋옵션"]
    }
    
    found_something = False
    
    lines = text.split('\n')
    for i, line in enumerate(lines):
        line = line.strip()
        if not line: continue
        
        for category, patterns in keywords.items():
            for pat in patterns:
                if pat in line:
                    # Print context (previous line + current line)
                    context = (lines[i-1].strip() + " " if i > 0 else "") + line
                    # Limit length
                    if len(context) > 200: context = context[:200] + "..."
                    
                    print(f"⚠️ [{category}] Found: '{pat}'")
                    print(f"   Context: \"{context}\"")
                    print("-" * 50)
                    found_something = True
                    # Break purely to avoid printing same line multiple times for different keywords
                    break 
    
    if not found_something:
        log_file.write("✅ No obvious keywords found (or structure is complex).\n")
        log_file.write("   This is where we would plug in an LLM to read the full context.\n")

if __name__ == "__main__":
    # Redirect output to a file manually
    with open("result.txt", "w", encoding="utf-8") as f:
        global log_file
        log_file = f
        
        # Monkey patch print to write to file
        original_print = print
        def print(*args, **kwargs):
            # Write to file
            f.write(" ".join(map(str, args)) + "\n")
            # Also print to stdout so we see progress
            original_print(*args, **kwargs)
            
        rcept_no = find_cb_disclosure()
        if rcept_no:
            download_and_parse(rcept_no)

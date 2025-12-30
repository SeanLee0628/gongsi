import requests
import zipfile
import io
import datetime
import time
from bs4 import BeautifulSoup

API_KEY = "577d4d3fff35faf9705ef7383b323d98e87a84bd"

# User provided list (cleaned up)
target_companies_str = """
피엔티엠에스, 자화전자, 엑시온그룹, 씨씨에스, 넥스틸, 태광산업, 팡스카이, 인피니트헬스케어, 에스엘에스바이오, 신대양제지, 오에스피, 지에이이노더스, 광동제약, 드래곤플라이, 에코볼트, 엘리비젼, 동원개발, 셀루메드, 케이씨씨, 동성제약, 티에스넥스젠, 자이글, 범양건영, 아이에이, 코아스, EMB, 한국미라클피플사, 에코플라스틱, KS인더스트리, 영풍, 아이에스동서, 하나마이크론, 캔버스엔, 포스코DX, 서울도시가스, 휴먼테크놀로지, 크레오에스지, 드래곤플라이, 아미코젠, 더테크놀로지, 시스웍, 올리패스, 카이노스메드, 세경하이테크, 나노실리칸첨단소재, 진시스템, 신라젠, 한국유니온제약, 만호제강, 태광산업, 세중, 코나솔, 한진, 한성기업, 동성제약, 나노실리칸첨단소재, 쏘카, 씨엔플러스, 진원생명과학, 테라사이언스, 콜마비앤에이치, 파라텍, 씨씨에스, 오건에코텍, 멤레이비티, 코아스, 서진시스템, 조선내화, 신풍제약, 다올투자증권, 지더블유바이텍, 오건에코텍, 에이전트AI, GRT, 올리패스, 테라사이언스, 대산F&B, 인트로메딕, 아스타, 메디앙스, 로보쓰리에이아이, 이미지스, THE E&M, 인크레더블버즈, 세토피아, 에스앤더블류, DH오토넥스, 한세예스24홀딩스, 티에스넥스젠, 범양건영, HS효성첨단소재, 한국유니온제약, 제이스코홀딩스, 풀무원, 제이오, 광명전기, 알에프세미, 금호전기, OCI, 다보링크, 금양, 나라소프트, 바이온, 이수페타시스, 오텍, 코오롱생명과학, 디와이디, 제이에스링크, STX, 비츠로시스, 삼영이엔씨, 제이케이시냅스, 경인양행, 자이글, 테크트랜스, 한울앤제주, 싸이토젠, 대양금속, 고려아연, 노블엠앤비, 이오플로우, KS인더스트리, 한선엔지니어링, 알멕, 소프트센, 나노실리칸첨단소재, 프로브잇, 셀피글로벌, 옵트론텍, 국제약품
"""

# Convert to set for O(1) lookup
target_set = {name.strip() for name in target_companies_str.replace('\n', ',').split(',') if name.strip()}

def get_insincere_list():
    print(f"🎯 Target Companies: {len(target_set)} unique corps")
    print("📥 Searching DART for 'Insincere Disclosure' reports (Last 1 Year)...")
    
    url = "https://opendart.fss.or.kr/api/list.json"
    end_dt = datetime.datetime.now()
    start_dt = end_dt - datetime.timedelta(days=730) # 2 Years lookback
    
    all_insincere = []
    
    # Check 10 pages to be safe
    for page in range(1, 11):
        params = {
            "crtfc_key": API_KEY,
            "bgn_de": start_dt.strftime("%Y%m%d"),
            "end_de": end_dt.strftime("%Y%m%d"),
            "page_no": page,
            "page_count": 100,
            # Remove pblntf_detail_ty to search everywhere
        }
        resp = requests.get(url, params=params).json()
        if 'list' in resp:
            # DEBUG: Print first item to check
            if page == 1 and len(resp['list']) > 0:
                print(f"DEBUG: First item found -> {resp['list'][0]['corp_name']} : {resp['list'][0]['report_nm']}")

            for item in resp['list']:
                # Broaden filter: "불성실" keyword anywhere
                # Simplify to just check everything for now to debug
                if "불성실" in item['report_nm']:
                     all_insincere.append(item)
        else:
            print(f"DEBUG: No list in response. Status: {resp.get('status')}, Msg: {resp.get('message')}")
            break
        time.sleep(0.1) # Faster query
    
    print(f"✅ Found {len(all_insincere)} total insincere designations.")
    
    # Filter by user list
    matches = [item for item in all_insincere if item['corp_name'] in target_set]
    print(f"🔔 Matches in your list: {len(matches)}")
    return matches

def extract_violation_detail(rcept_no):
    url = "https://opendart.fss.or.kr/api/document.xml"
    params = {"crtfc_key": API_KEY, "rcept_no": rcept_no}
    
    try:
        resp = requests.get(url, params=params)
        with zipfile.ZipFile(io.BytesIO(resp.content)) as z:
            target_file = next((f for f in z.namelist() if f.endswith('.xml') or f.endswith('.html')), None)
            if not target_file: return "No XML"
            
            soup = BeautifulSoup(z.read(target_file), 'html.parser')
            text = soup.get_text('\n')
            
            # Extract relevant section
            lines = text.split('\n')
            detail = []
            capture = False
            
            # Keywords to find the reason
            start_keywords = ["불성실공시법인 지정내용", "지정내용", "공시위반 내용", "위반내용"]
            end_keywords = ["부과벌점", "공시위반제재금", "3.", "매매거래정지"]
            
            for line in lines:
                clean_line = line.strip()
                if not clean_line: continue
                
                # Start capture
                if not capture:
                    # Check if line contains keyword but isn't too long/garbage
                    if any(k in clean_line for k in start_keywords) and len(clean_line) < 50:
                        capture = True
                        continue
                        
                # End capture
                if capture:
                    if any(k in clean_line for k in end_keywords):
                        break
                    detail.append(clean_line)
            
            # Fallback text search if clean extract fails
            if not detail:
                for i, line in enumerate(lines):
                    if "사유" in line or "위반" in line:
                         detail.append(line)
                         if len(detail) > 3: break # Limit
            
            return " ".join(detail[:5]) if detail else "상세 내용 추출 실패"
            
    except Exception:
        return "Download Fail"

def main():
    matches = get_insincere_list()
    
    report_lines = ["# 🚨 불성실공시법인 위반 내용 분석 결과", f"분석일: {datetime.datetime.now().strftime('%Y-%m-%d')}", ""]
    
    for i, item in enumerate(matches):
        print(f"[{i+1}/{len(matches)}] Analyzing {item['corp_name']}...")
        reason = extract_violation_detail(item['rcept_no'])
        
        report_lines.append(f"### 🔴 {item['corp_name']}")
        report_lines.append(f"- **공시일**: {item['rcept_dt']}")
        report_lines.append(f"- **공시제목**: {item['report_nm']}")
        report_lines.append(f"- **위반/지정 상세사유**: \n  > {reason}")
        report_lines.append("---")
        
    with open("insincere_analysis.md", "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))
        
    print("\n✅ Done! Saved to insincere_analysis.md")

if __name__ == "__main__":
    main()

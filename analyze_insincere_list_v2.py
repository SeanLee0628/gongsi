import requests
import zipfile
import io
import datetime
import time
from bs4 import BeautifulSoup
from dateutil.relativedelta import relativedelta

API_KEY = "577d4d3fff35faf9705ef7383b323d98e87a84bd"

target_companies_str = """
피엔티엠에스, 자화전자, 엑시온그룹, 씨씨에스, 넥스틸, 태광산업, 팡스카이, 인피니트헬스케어, 에스엘에스바이오, 신대양제지, 오에스피, 지에이이노더스, 광동제약, 드래곤플라이, 에코볼트, 엘리비젼, 동원개발, 셀루메드, 케이씨씨, 동성제약, 티에스넥스젠, 자이글, 범양건영, 아이에이, 코아스, EMB, 한국미라클피플사, 에코플라스틱, KS인더스트리, 영풍, 아이에스동서, 하나마이크론, 캔버스엔, 포스코DX, 서울도시가스, 휴먼테크놀로지, 크레오에스지, 드래곤플라이, 아미코젠, 더테크놀로지, 시스웍, 올리패스, 카이노스메드, 세경하이테크, 나노실리칸첨단소재, 진시스템, 신라젠, 한국유니온제약, 만호제강, 태광산업, 세중, 코나솔, 한진, 한성기업, 동성제약, 나노실리칸첨단소재, 쏘카, 씨엔플러스, 진원생명과학, 테라사이언스, 콜마비앤에이치, 파라텍, 씨씨에스, 오건에코텍, 멤레이비티, 코아스, 서진시스템, 조선내화, 신풍제약, 다올투자증권, 지더블유바이텍, 오건에코텍, 에이전트AI, GRT, 올리패스, 테라사이언스, 대산F&B, 인트로메딕, 아스타, 메디앙스, 로보쓰리에이아이, 이미지스, THE E&M, 인크레더블버즈, 세토피아, 에스앤더블류, DH오토넥스, 한세예스24홀딩스, 티에스넥스젠, 범양건영, HS효성첨단소재, 한국유니온제약, 제이스코홀딩스, 풀무원, 제이오, 광명전기, 알에프세미, 금호전기, OCI, 다보링크, 금양, 나라소프트, 바이온, 이수페타시스, 오텍, 코오롱생명과학, 디와이디, 제이에스링크, STX, 비츠로시스, 삼영이엔씨, 제이케이시냅스, 경인양행, 자이글, 테크트랜스, 한울앤제주, 싸이토젠, 대양금속, 고려아연, 노블엠앤비, 이오플로우, KS인더스트리, 한선엔지니어링, 알멕, 소프트센, 나노실리칸첨단소재, 프로브잇, 셀피글로벌, 옵트론텍, 국제약품
"""

target_set = {name.strip() for name in target_companies_str.replace('\n', ',').split(',') if name.strip()}

def get_insincere_list_chunked():
    print(f"🎯 Target Companies: {len(target_set)} unique corps")
    url = "https://opendart.fss.or.kr/api/list.json"
    
    all_items = []
    
    # Iterate last 1 year in 3-month chunks
    end_date = datetime.datetime.now()
    start_date = end_date - relativedelta(years=1)
    
    current_start = start_date
    while current_start < end_date:
        current_end = current_start + relativedelta(months=3)
        if current_end > end_date: current_end = end_date
        
        print(f"⏳ Scanning: {current_start.strftime('%Y-%m-%d')} ~ {current_end.strftime('%Y-%m-%d')} ...")
        
        for page in range(1, 5): # Check up to 5 pages per chunk
            params = {
                "crtfc_key": API_KEY,
                "bgn_de": current_start.strftime("%Y%m%d"),
                "end_de": current_end.strftime("%Y%m%d"),
                "page_no": page,
                "page_count": 100
            }
            try:
                resp = requests.get(url, params=params).json()
                if resp.get('status') == '000' and 'list' in resp:
                    for item in resp['list']:
                        if "불성실" in item['report_nm']:
                            all_items.append(item)
                    if len(resp['list']) < 100: break # Last page
                else:
                    break
            except Exception as e:
                print(f"❌ Error: {e}")
                break
            time.sleep(0.1)
            
        current_start = current_end + relativedelta(days=1)

    print(f"✅ Total Insincere Reports Found: {len(all_items)}")
    
    # Filter
    matches = [item for item in all_items if item['corp_name'] in target_set]
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
            
            # Use lxml for better table parsing if available, else html.parser
            soup = BeautifulSoup(z.read(target_file), 'html.parser')
            
            # Strategy: Simply find where the 'designation content' starts
            # Usually inside a table or section titled "2. 불성실공시법인 지정내용"
            
            full_text = soup.get_text('\n')
            lines = [line.strip() for line in full_text.split('\n') if line.strip()]
            
            found_idx = -1
            keywords = ["지정내용", "위반내용", "공시위반 내용", "불성실공시법인 지정"]
            
            # 1. Find the starting line index
            for i, line in enumerate(lines):
                 if any(k in line for k in keywords) and len(line) < 50:
                     found_idx = i
                     break
            
            extracted = []
            if found_idx != -1:
                # Capture next 15 lines after the header
                # Filter out pure numbers or dates to get text
                count = 0
                for line in lines[found_idx+1:]:
                    if "3." in line or "부과벌점" in line: # Stop condition
                         extracted.append(line)
                         break 
                    extracted.append(line)
                    count += 1
                    if count > 10: break
            else:
                 # Fallback: Search for sentences containing specific patterns
                 for line in lines:
                     if "공시번복" in line or "공시불이행" in line or "변경" in line:
                         if len(line) > 10 and len(line) < 200:
                            extracted.append(line)

            return "\n".join(extracted) if extracted else "내용을 찾을 수 없습니다. (문서 구조가 특이함)"

    except Exception as e:
        return f"Error: {e}"

def main():
    matches = get_insincere_list_chunked()
    
    # Create Markdown Report
    report_content = f"# 🚨 불성실공시법인 분석 리포트\n작성일: {datetime.datetime.now().strftime('%Y-%m-%d')}\n\n"
    
    if not matches:
        report_content += "## ✅ 분석 결과: 해당 리스트 내 기업 중 최근 1년간 불성실공시 내역 없음.\n"
    else:
        for item in matches:
            report_content += f"## ⚠️ {item['corp_name']}\n"
            report_content += f"- **공시일**: {item['rcept_dt']}\n"
            report_content += f"- **공시명**: {item['report_nm']}\n"
            
            print(f"   > Fetching details for {item['corp_name']}...")
            detail = extract_violation_detail(item['rcept_no'])
            report_content += f"- **위반상세**: \n```\n{detail}\n```\n\n---\n"
            
    with open("insincere_report_final.md", "w", encoding="utf-8") as f:
        f.write(report_content)
    print("\n🎉 Report Saved: insincere_report_final.md")

if __name__ == "__main__":
    main()

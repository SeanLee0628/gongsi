import requests
import zipfile
import io
import datetime
from bs4 import BeautifulSoup
import re

API_KEY = "577d4d3fff35faf9705ef7383b323d98e87a84bd"

def fetch_insincere_corps():
    print("🔍 최근 6개월간 '불성실공시법인지정' 공시를 검색합니다...")
    url = "https://opendart.fss.or.kr/api/list.json"
    
    # 최근 6개월 조회
    end_dt = datetime.datetime.now()
    start_dt = end_dt - datetime.timedelta(days=180) 
    
    params = {
        "crtfc_key": API_KEY,
        "bgn_de": start_dt.strftime("%Y%m%d"),
        "end_de": end_dt.strftime("%Y%m%d"),
        "last_reprt_at": "Y", # 최종보고서만
        "page_count": 50,
        "pblntf_detail_ty": "I002" # 공정위/거래소 공시 -> 수시공시 쪽에는 코드가 다를 수 있어 텍스트 검색 병행
    }
    
    # NOTE: 불성실공시는 유형 코드가 애매할 수 있어 전체 수시공시(I002 등) 잡거나
    # 그냥 전체 검색 후 텍스트 필터링이 확실함. 여기선 검색 효율을 위해 전체 리스트에서 필터링.
    
    # Strategy Update: pblntf_detail_ty 없이 날짜로만 긁어서 이름으로 필터링 (가장 확실)
    del params["pblntf_detail_ty"] 
    
    targets = []
    
    try:
        resp = requests.get(url, params=params).json()
        if resp.get('status') == '000' and 'list' in resp:
            for item in resp['list']:
                if "불성실공시법인지정" in item['report_nm'] and "예고" not in item['report_nm']:
                     # "지정예고"는 확정이 아니므로 제외, "지정"만 포함
                     targets.append(item)
        else:
            print(f"❌ API Error: {resp.get('message')}")
            return
            
        print(f"✅ 총 {len(targets)}건의 지정 공시 발견! 상세 내용 분석 시작...\n")
        
        results = []
        
        # 5개만 샘플링 (너무 많으면 오래 걸림)
        for idx, item in enumerate(targets[:10]):
            rcept_no = item['rcept_no']
            corp_name = item['corp_name']
            
            print(f"[{idx+1}/{min(len(targets), 10)}] 분석 중: {corp_name} ...")
            
            detail = parse_insincere_detail(rcept_no)
            results.append(f"## {corp_name}\n- **공시 제목**: {item['report_nm']}\n- **위반/지정 사유**: {detail}\n")
            
        # Save to file
        with open("insincere_report.md", "w", encoding="utf-8") as f:
            f.write(f"# 불성실공시법인 지정 현황 (최근 6개월)\n작성일: {datetime.datetime.now().strftime('%Y-%m-%d')}\n\n")
            f.write("\n".join(results))
            
        print("\n🎉 분석 완료! 'insincere_report.md' 파일을 확인하세요.")
        
    except Exception as e:
        print(f"❌ Fail: {e}")

def parse_insincere_detail(rcept_no):
    url = "https://opendart.fss.or.kr/api/document.xml"
    params = {"crtfc_key": API_KEY, "rcept_no": rcept_no}
    
    try:
        resp = requests.get(url, params=params)
        with zipfile.ZipFile(io.BytesIO(resp.content)) as z:
            target_file = next((f for f in z.namelist() if f.endswith('.xml') or f.endswith('.html')), None)
            if not target_file: return "문서 파일 없음"
            
            soup = BeautifulSoup(z.read(target_file), 'html.parser')
            text = soup.get_text('\n')
            
            # Simple Text Extraction using Keywords
            # 찾아야 할 키워드: "불성실공시법인 지정내용", "공시위반 제재금", "부과벌점"
            # 보통 표 안에 있거나 "2. 지정내용" 섹션에 있음.
            
            lines = text.split('\n')
            extracted = []
            capture = False
            
            for line in lines:
                line = line.strip()
                if not line: continue
                
                # 트리거 키워드 발견 시 캡처 시작
                if any(k in line for k in ["2. 불성실공시법인 지정내용", "2. 지정내용", "2. 지정내역"]):
                    capture = True
                    continue
                
                # 3번 섹션 나오면 종료
                if "3." in line and capture: 
                    break
                    
                if capture:
                    # 너무 긴 라인(Base64 등) 제외
                    if len(line) < 200:
                        extracted.append(line)
                        
            if not extracted:
                # 섹션 번호가 없는 경우 (HTML 구조가 다를 때) -> "사유" 키워드 주변 탐색
                for i, line in enumerate(lines):
                    if "위반내용" in line or "지정사유" in line:
                         extracted.append(line)
                         if i+1 < len(lines): extracted.append(lines[i+1])
            
            if not extracted:
                return "내용 추출 실패 (서식 복잡함)"
                
            return " ".join(extracted[:10]) # 길면 자름
            
    except Exception as e:
        return f"파싱 에러: {str(e)}"

if __name__ == "__main__":
    fetch_insincere_corps()

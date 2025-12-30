from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, List, Any, Optional
import requests
import io
import zipfile
import json
import re
from bs4 import BeautifulSoup
import datetime

app = FastAPI(title="DART Toxic Clause Analyzer")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# User provided API KEY (Should be in env vars for production)
API_KEY = os.getenv("DART_API_KEY", "YOUR_DART_API_KEY_HERE")

# Load Patterns
try:
    with open("patterns.json", "r", encoding="utf-8") as f:
        PATTERNS: Dict[str, List[str]] = json.load(f)
except Exception as e:
    print(f"⚠️ Failed to load patterns.json: {e}")
    PATTERNS = {}

class AnalyzeReq(BaseModel):
    text: str
    company_name: Optional[str] = None
    ticker: Optional[str] = None
    title: Optional[str] = None

# --- Core Analysis Logic (Ported from Request) ---

def split_sentences(text: str) -> List[str]:
    parts = re.split(r"\n+|(?<=[.!?])\s+", text)
    return [p.strip() for p in parts if p.strip()]

def extract_evidence(text: str) -> List[Dict[str, Any]]:
    sents = split_sentences(text)
    out = []
    seen = set()

    for i, s in enumerate(sents):
        for cat, regs in PATTERNS.items():
            for rg in regs:
                if re.search(rg, s, flags=re.IGNORECASE):
                    key = f"{cat}::{s}"
                    # Allow extracting same sentence for different categories if meaningful,
                    # but here we use strict dedup based on category+sentence
                    if key not in seen:
                        seen.add(key)
                        out.append({"category": cat, "sentence": s, "matched": rg, "sent_idx": i})
                    break 

    # Limit per category
    limit = 5
    count = {}
    trimmed = []
    for e in out:
        c = e["category"]
        count[c] = count.get(c, 0) + 1
        if count[c] <= limit:
            trimmed.append(e)
    return trimmed

def rough_risk_score(evidence: List[Dict[str, Any]]) -> int:
    weight = {
        "FIN_DILUTION": 25,
        "FIN_COVENANT": 25,
        "FIN_CONTINGENT": 20,
        "RELATED_PARTY": 15,
        "MA_CONDITIONAL": 15,
        "DISCLOSURE_QUALITY": 10,
    }
    cats = {e["category"] for e in evidence}
    score = sum(weight.get(c, 0) for c in cats)
    return max(0, min(100, score))

def build_llm_input(company_name: str, ticker: str, title: str, evidence: List[Dict[str, Any]], full_text: str = ""):
    return {
        "instruction": (
            "너는 냉철한 금융 계약 분석가다. **모든 출력은 '초압축'되어야 하며, 반드시 '숫자'가 포함되어야 한다.**\n\n"
            "1. **Risk Score**: (0~100 점수 산정)\n"
            "2. **Insight (핵심 해석)**:\n"
            "   - **반드시 구체적인 숫자(금액, %, 날짜)를 포함하여 해석하라.**\n"
            "   - 막연한 표현('상당한', '대규모') 금지. 숫자로 증명하라.\n"
            "   - **1~2문장, 100자 이내**로 작성.\n"
            "   - 예: '풋옵션(9,715원) 행사 시 265억 원의 현금이 일시 유출될 위험이 있음.' (O)\n"
            "3. **Evidence (근거 문장)**:\n"
            "   - **가장 치명적인 '단 1개의 문장'만 발췌하라.**\n"
            "   - 길어지면 안 된다.\n\n"
            "**출력 형식(JSON)**:\n"
            "{\n"
            "  'summary': {'verdict': 'toxic', 'risk_score': 85},\n"
            "  'findings': [\n"
            "    {\n"
            "      'category': 'Option',\n"
            "      'insight': '행사가격(500원)까지 리픽싱 가능한 조건으로, 주가 하락 시 발행주식수가 최대 200만 주까지 늘어날 수 있음.',\n"
            "      'evidence': '조정한도: 액면가(500원)까지...'\n"
            "    }\n"
            "  ]\n"
            "}"
        ),
        "schema_hint": {
            "summary": {"verdict":"toxic|mixed|neutral|good", "risk_score":"0-100"},
            "findings": [{"category":"CategoryName","insight":"Impact analysis (2-3 sentences)","evidence":"Verbatim quote (Max 3 sentences)"}]
        },
        "doc": {
            "company_name": company_name, 
            "ticker": ticker, 
            "title": title,
            "full_text": full_text[:10000] 
        },
        "evidence_hints": [{"category": e["category"], "sentence": e["sentence"]} for e in evidence],
    }

# --- DART Helper Functions ---

# --- DART Helper Functions ---

import xml.etree.ElementTree as ET
import os

CORP_CODE_FILE = "corp_codes.json"
CORP_CODE_MAP = {}

def load_corp_codes():
    """Loads corp_code mapping, fetching from DART if missing."""
    global CORP_CODE_MAP
    if os.path.exists(CORP_CODE_FILE):
        try:
            with open(CORP_CODE_FILE, "r", encoding="utf-8") as f:
                CORP_CODE_MAP = json.load(f)
            print(f"✅ Loaded {len(CORP_CODE_MAP)} corp codes from cache.")
            return
        except:
             pass
    
    print("⏳ Fetching corp_code.xml from DART...")
    url = "https://opendart.fss.or.kr/api/corpCode.xml"
    params = {"crtfc_key": API_KEY}
    try:
        resp = requests.get(url, params=params)
        with zipfile.ZipFile(io.BytesIO(resp.content)) as z:
            xml_data = z.read("CORPCODE.xml")
            root = ET.fromstring(xml_data)
            for child in root.findall("list"):
                nm = child.find("corp_name").text.strip()
                code = child.find("corp_code").text.strip()
                CORP_CODE_MAP[nm] = code
        
        with open(CORP_CODE_FILE, "w", encoding="utf-8") as f:
            json.dump(CORP_CODE_MAP, f, ensure_ascii=False)
        print(f"✅ Fetched and cached {len(CORP_CODE_MAP)} corp codes.")
    except Exception as e:
        print(f"❌ Failed to load corp codes: {e}")

def get_recent_disclosures(corp_code: str):
    """Finds recent disclosures for a specific corp_code."""
    url = "https://opendart.fss.or.kr/api/list.json"
    end_dt = datetime.datetime.now()
    start_dt = end_dt - datetime.timedelta(days=365) # Extended to 1 Year to ensure results
    
    params = {
        "crtfc_key": API_KEY,
        "corp_code": corp_code,
        "bgn_de": start_dt.strftime("%Y%m%d"),
        "end_de": end_dt.strftime("%Y%m%d"),
        "page_count": 50, # Get more candidates
        # "pblntf_detail_ty": "B001" # REMOVED strict filter to get all reports
    }
    
    try:
        resp = requests.get(url, params=params).json()
        if resp.get('status') == '000' and 'list' in resp:
            return resp['list']
    except:
        pass
    return []

def get_document_text(rcept_no: str):
    """Downloads and extracts text from DART document."""
    url = "https://opendart.fss.or.kr/api/document.xml"
    params = {"crtfc_key": API_KEY, "rcept_no": rcept_no}
    
    try:
        resp = requests.get(url, params=params)
        with zipfile.ZipFile(io.BytesIO(resp.content)) as z:
            # Usually contains one or more xml files. We take the largest one or list them.
            # Simple approach: Read all xmls and concat
            full_text = ""
            for name in z.namelist():
                if name.endswith(".xml"):
                    content = z.read(name).decode("utf-8", errors="ignore")
                    # Simple strip tags
                    text = re.sub(r'<[^>]+>', '\n', content)
                    full_text += text + "\n"
            return full_text
    except Exception as e:
        print(f"Failed to fetch doc {rcept_no}: {e}")
        return ""

# --- Search Endpoint ---

class CompanySearchReq(BaseModel):
    company_name: str

@app.post("/analyze/company")
def analyze_company(req: CompanySearchReq):
    # 1. Init Corp Code
    if not CORP_CODE_MAP:
        load_corp_codes()
        
    # 2. Find Code
    corp_code = CORP_CODE_MAP.get(req.company_name)
    if not corp_code:
        # Fuzzy search?
        for name, code in CORP_CODE_MAP.items():
             if name.replace(" ", "") == req.company_name.replace(" ", ""):
                 corp_code = code
                 break
    
    if not corp_code:
        return {"status": "error", "message": "Company not found in DART registry."}
        
    # 3. Get Recent Reports
    raw_list = get_recent_disclosures(corp_code)
    
    # 4. Dedup by Title (Take distinct, max 5)
    # FILTER: Exclude "소유상황보고서" (Shareholder updates are usually noise for toxic clause analysis)
    seen_titles = set()
    targets = []
    
    for item in raw_list:
        # FILTER: Exclude noise reports
        if "소유상황보고서" in item['report_nm'] or "주주명부폐쇄" in item['report_nm']:
            continue
            
        clean_title = item['report_nm'].replace(" ", "")
        if clean_title not in seen_titles:
            seen_titles.add(clean_title)
            targets.append(item)
        if len(targets) >= 5:
             break
            
    # 5. Analyze Each
    results = []
    total_score = 0
    worst_insight = None
    
    for item in targets:
        text = get_document_text(item['rcept_no'])
        if len(text) < 100:
            continue
            
        evidence = extract_evidence(text)
        risk_score_rule = rough_risk_score(evidence)
        llm_input = build_llm_input(item['corp_name'], "", item['report_nm'], evidence, full_text=text)
        
        llm_result = None
        if client:
             llm_result = call_finetuned_model(llm_input)
        
        analysis_summary = {
            "title": item['report_nm'],
            "date": item['rcept_dt'],
            "risk_score": risk_score_rule, 
            "insights": [],
            "verdict": "neutral"
        }
        
        if llm_result:
             summary = llm_result.get('summary', {})
             analysis_summary['risk_score'] = summary.get('risk_score', risk_score_rule)
             analysis_summary['verdict'] = summary.get('verdict', 'neutral')
             
             findings = llm_result.get('findings') or llm_result.get('details') or []
             if isinstance(findings, list):
                 for f in findings:
                     insight_data = {
                         "category": f.get('category'),
                         "insight": f.get('insight') or f.get('reason'),
                         "evidence": f.get('evidence') or f.get('quote'),
                         "severity": f.get('severity', 'medium')
                     }
                     analysis_summary['insights'].append(insight_data)
                     
                     # Check for worst finding
                     is_critical = insight_data['severity'].lower() in ['critical', 'high']
                     current_worst_score = 0 if not worst_insight else (2 if worst_insight['severity'] == 'critical' else 1)
                     this_score = 2 if insight_data['severity'].lower() == 'critical' else (1 if insight_data['severity'].lower() == 'high' else 0)
                     
                     if this_score > current_worst_score:
                         worst_insight = {
                             "report_title": item['report_nm'],
                             "insight": insight_data['insight'],
                             "severity": insight_data['severity']
                         }
                         
        else:
             # Fallback
             analysis_summary['verdict'] = "Rule-based"
             for e in evidence:
                 analysis_summary['insights'].append({
                     "category": e['category'],
                     "insight": "Keyword matched (Rule-based)",
                     "evidence": e['sentence'],
                     "severity": "medium"
                 })
                 
        total_score += int(analysis_summary['risk_score'])
        results.append(analysis_summary)
    
    # Calculate Stats
    avg_score = round(total_score / len(results)) if results else 0
    
    return {
        "company": req.company_name,
        "summary_stats": {
            "total_reports": len(results),
            "average_risk": avg_score,
            "worst_clause": worst_insight 
        },
        "reports": results
    }

# --- API Endpoints ---

from openai import OpenAI

# -----------------------------------------------------------------------------
# 🤖 AI Model Configuration
# -----------------------------------------------------------------------------
# User provided Fine-tuning Job IDs. 
# NOTE: Replace with actual Model Names (e.g., "ft:gpt-3.5-turbo:...") if these are just Job IDs.
PRIMARY_FT_MODEL = "ft:gpt-4o-mini-2024-07-18:personal::CsN89D5n"
SECONDARY_FT_MODEL = "ft:gpt-4o-mini-2024-07-18:personal::CsN7xFW4"

# Try to get API Key from environment
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

def call_finetuned_model(llm_input):
    """
    Calls the Fine-tuned LLM to get expert analysis.
    Returns parsed JSON dictionary or None if failed.
    """
    if not client:
        return None

    try:
        # Construct messages based on input
        system_msg = llm_input['instruction'] + "\nOutput valid JSON only."
        user_msg = json.dumps({
            "doc": llm_input['doc'],
            "evidence_hints": llm_input.get('evidence_hints', [])
        }, ensure_ascii=False)

        response = client.chat.completions.create(
            model=PRIMARY_FT_MODEL,
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_msg}
            ],
            temperature=0.1, # Low temperature for consistent JSON
            response_format={"type": "json_object"}
        )
        
        content = response.choices[0].message.content
        print(f"\n🤖 [AI RAW OUTPUT]: {content[:200]}...") # Log first 200 chars
        return json.loads(content)
    except Exception as e:
        print(f"\n⚠️ [AI FAILURE]: {e}")
        return None

# --- API Endpoints ---

@app.post("/analyze")
def analyze(req: AnalyzeReq):
    evidence = extract_evidence(req.text)
    risk_score_rule = rough_risk_score(evidence)
    llm_input = build_llm_input(req.company_name or "", req.ticker or "", req.title or "", evidence, full_text=req.text)
    
    # 1. API Key Check
    if not client:
        return {
            "evidence": [],
            "draft_summary": {"verdict": "unknown", "risk_score": 0, "risk_level": "Unknown", "source": "System_Error"},
            "details": [{
                "type": "SYSTEM_ERROR",
                "keyword": "API_KEY_MISSING",
                "context": "OpenAI API Key가 설정되지 않았습니다! 환경변수 'OPENAI_API_KEY'를 설정하거나 main.py에 직접 입력해주세요. (현재 Rule-based 분석만 표시됩니다)",
                "risk_level": "Critical"
            }] + [
                {"type": e['category'], "keyword": e['matched'], "context": e['sentence'], "risk_level": "High"} 
                for e in evidence
            ]
        }

    # 2. Try LLM
    llm_result = call_finetuned_model(llm_input)
    
    # 3. Merge Results
    formatted_details = []
    
    if llm_result:
        # Flexible Parsing Logic
        findings = []
        summary = {}
        
        # 1. Try standard keys
        if isinstance(llm_result, dict):
            summary = llm_result.get('summary', {})
            findings = (
                llm_result.get('findings') or 
                llm_result.get('details') or 
                llm_result.get('clauses') or 
                llm_result.get('issues') or 
                llm_result.get('result') or
                ([llm_result.get('Finding')] if llm_result.get('Finding') else []) or 
                []
            )
            # If still empty, maybe the dict itself items?
            if not findings and any(k in llm_result for k in ['category', 'title']):
                 findings = [llm_result]
                 
        elif isinstance(llm_result, list):
            # The model returned a direct list of findings
            findings = llm_result
            summary = {"verdict": "AI_Analysis", "risk_score": 50} # Default since summary is missing

        # 2. Extract Data
        final_risk = summary.get('risk_score', risk_score_rule)
        final_verdict = summary.get('verdict', "AI_Analysis")
        
        if findings:
            ai_contexts = []
            for f in findings:
                # Flexible field mapping
                f_cat = f.get('category') or f.get('type') or 'AI_Item'
                f_insight = f.get('insight') or f.get('reason') or f.get('description') or "No Insight"
                f_evidence = f.get('evidence') or f.get('quote') or "No Evidence"
                f_severity = f.get('severity') or f.get('risk_level') or 'Medium'
                
                # Combine for Dedup check
                ai_contexts.append(f_evidence) 

                formatted_details.append({
                    "type": f_cat,
                    "keyword": "📌 Insight", # Label for Title
                    "context": f"{f_insight}\n\n[Evidence]: \"{f_evidence}\"", # Combine for display
                    "risk_level": str(f_severity).capitalize()
                })
            
            # Aggressive Dedup Policy:
            # If AI found ANYTHING, we trust AI fully and discard ALL rule-based keyword matches.
            # This prevents the "Keyword detected..." spam that annoys the user.
            pass 
            
            # The previous logic of adding rule-based evidence is REMOVED here.
            # We ONLY add rule-based evidence if AI completely failed (in the else block below).

        else:
            # AI responded but found nothing or format error
            print(f"⚠️ AI Data Structure Unknown: {llm_result}") # Debug log
            formatted_details.append({
                "type": "AI_Warning",
                "keyword": "📌 Insight",
                "context": f"AI 응답 해석 실패.\n\n[Evidence]: \"Raw: {str(llm_result)[:100]}...\"",
                "risk_level": "Medium"
            })
            # Add ALL evidence since AI failed to parse
            for e in evidence:
                formatted_details.append({
                    "type": e['category'],
                    "keyword": "📌 Insight",
                    "context": f"'{e['matched']}' 키워드가 감지되었습니다.\n\n[Evidence]: \"{e['sentence']}\"",
                    "risk_level": "Medium"
                })
    else:
        # LLM Failed -> Show Error + Rule Based
        final_risk = risk_score_rule
        final_verdict = "Rule-based (AI Failed)"
        formatted_details.append({
            "type": "AI_ERROR",
            "keyword": "Connection_Failed",
            "context": "AI 모델 호출에 실패했습니다. (모델 ID 확인, 토큰 부족, 또는 네트워크 오류)",
            "risk_level": "High"
        })
        # Add Rule-based evidence as fallback
        for e in evidence:
            formatted_details.append({
                "type": e['category'],
                "keyword": e['matched'],
                "context": e['sentence'],
                "risk_level": "Medium"
            })

    return {
        "evidence": evidence,
        "draft_summary": {
            "verdict": final_verdict,
            "risk_score": final_risk,
            "risk_level": "High" if int(final_risk) >= 50 else "Medium",
            "source": "AI_FineTuned" if llm_result else "Rule_Based"
        },
        "details": formatted_details,
        "llm_result": llm_result
    }

@app.get("/analyze/recent")
def analyze_recent_cb():
    # 1. Find Target
    target = search_recent_cb_report()
    if not target:
        return {"found": False, "message": "No CB report found in last 30 days."}
    
    # 2. Download & Parse
    download_url = "https://opendart.fss.or.kr/api/document.xml"
    params = {"crtfc_key": API_KEY, "rcept_no": target['rcept_no']}
    
    try:
        resp = requests.get(download_url, params=params)
        with zipfile.ZipFile(io.BytesIO(resp.content)) as z:
            target_filename = next((f for f in z.namelist() if f.endswith('.xml') or f.endswith('.html')), None)
            
            if not target_filename:
                raise HTTPException(status_code=500, detail="No parseable file in DART Document")
            
            content = z.read(target_filename)
            soup = BeautifulSoup(content, 'html.parser')
            text_content = soup.get_text('\n')
            
            # 3. Analyze
            evidence = extract_evidence(text_content)
            risk_rule = rough_risk_score(evidence)
            
            # Prepare LLM Input
            llm_input = build_llm_input(target['corp_name'], target['stock_code'], target['report_nm'], evidence, full_text=text_content)
            
            # Call LLM
            llm_result = call_finetuned_model(llm_input)
            
            # Decide final display data
            formatted_details = []
            
            if llm_result:
                summary = llm_result.get('summary', {})
                final_risk = summary.get('risk_score', risk_rule)
                final_verdict = summary.get('verdict', "Rule-based")
                
                # Use LLM findings if available
                findings = llm_result.get('findings', [])
                if findings:
                    for f in findings:
                        formatted_details.append({
                            "type": f.get('category', 'AI_Item'),
                            "keyword": f.get('title', 'Detected'),
                            "context": f.get('reason') or f.get('quote') or "No details",
                            "risk_level": f.get('severity', 'Medium').capitalize()
                        })
                else:
                    # Fallback to evidence if findings missing
                    for e in evidence:
                        formatted_details.append({
                            "type": e['category'],
                            "keyword": e['matched'],
                            "context": e['sentence'],
                            "risk_level": "Medium"
                        })
            else:
                final_risk = risk_rule
                final_verdict = "Rule-based"
                for e in evidence:
                    formatted_details.append({
                        "type": e['category'],
                        "keyword": e['matched'],
                        "context": e['sentence'],
                        "risk_level": "High" if int(final_risk) >= 40 else "Medium"
                    })

            return {
                "found": True,
                "target_corp": target['corp_name'],
                "report_name": target['report_nm'],
                "rcept_no": target['rcept_no'],
                "date": target['rcept_dt'],
                "analysis_count": len(formatted_details),
                "risk_score": final_risk,
                "ai_verdict": final_verdict,
                "details": formatted_details,
                "llm_input_preview": llm_input
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)

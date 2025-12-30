import React, { useState } from 'react';
import axios from 'axios';
import { AlertCircle, FileSearch, ShieldCheck, ShieldAlert, ChevronDown, ChevronUp, Loader, Search, Building2, FileText, BarChart3, TrendingUp, AlertTriangle, Terminal } from "lucide-react";
import { motion, AnimatePresence } from 'framer-motion';

const CATEGORY_MAP = {
  "MA_CONDITIONAL": "🔒 경영권/옵션",
  "FIN_DILUTION": "📉 지분희석",
  "FIN_COVENANT": "⚠️ 재무약정",
  "FIN_CONTINGENT": "💸 우발채무",
  "RELATED_PARTY": "🤝 특수관계",
  "DISCLOSURE_QUALITY": "📢 공시품질",
  "Price/Amount": "💰 금액/단가",
  "Option": "🔄 옵션상세",
  "Quantity": "📦 수량/지분",
  "Etc": "📝 기타"
};

function App() {
  const [mode, setMode] = useState('company'); // Default: Company Search
  const [inputText, setInputText] = useState('');
  const [companyName, setCompanyName] = useState('');

  const [manualData, setManualData] = useState(null);
  const [companyData, setCompanyData] = useState(null);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Manual Analysis
  const analyzeManual = async () => {
    if (!inputText.trim()) return;
    setLoading(true); setError(null); setManualData(null);
    try {
      const response = await axios.post("http://127.0.0.1:8000/analyze", { text: inputText });
      setManualData(response.data);
    } catch (err) {
      setError("서버 연결 실패. Backend 상태를 확인하세요.");
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  // Company Analysis
  const searchCompany = async () => {
    if (!companyName.trim()) return;
    setLoading(true); setError(null); setCompanyData(null);
    try {
      const response = await axios.post("http://127.0.0.1:8000/analyze/company", { company_name: companyName });
      if (response.data.status === 'error') {
        setError(response.data.message);
      } else {
        setCompanyData(response.data);
      }
    } catch (err) {
      setError("서버 연결 실패. DART API 상태를 확인하세요.");
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#0f111a] text-gray-100 flex flex-col items-center p-8 font-sans selection:bg-purple-500 selection:text-white">

      {/* Header */}
      <motion.div initial={{ opacity: 0, y: -20 }} animate={{ opacity: 1, y: 0 }} className="mb-12 text-center max-w-3xl">

        <h1 className="text-7xl font-black mb-6 tracking-tight text-transparent bg-clip-text bg-gradient-to-r from-purple-400 via-pink-500 to-orange-500 drop-shadow-2xl">
          Unitox
        </h1>

        <div className="relative group cursor-default">
          <div className="absolute inset-0 bg-gradient-to-r from-purple-600 to-blue-600 rounded-xl blur opacity-20 group-hover:opacity-30 transition duration-500"></div>
          <div className="relative bg-[#1a1d2d] border border-gray-700/50 p-6 rounded-xl flex items-center justify-center space-x-4">
            <ShieldAlert className="w-10 h-10 text-orange-500 flex-shrink-0" />
            <div className="text-left">
              <p className="text-lg font-medium text-gray-200">
                독소조항 전문 <span className="text-white font-bold underline decoration-purple-500 decoration-2 underline-offset-4">Fine-tuned AI</span>가 공시의 숨겨진 위험을 찾아냅니다.
              </p>
              <p className="text-sm text-gray-500 mt-1">
                전환사채(CB), 신주인수권부사채(BW) 등 복잡한 전자공시의 리스크를 단 3초 만에 분석하세요.
              </p>
            </div>
          </div>
        </div>
      </motion.div>

      {/* Mode Switcher */}
      <div className="flex bg-[#1a1d2d] p-1.5 rounded-2xl mb-8 border border-gray-800 shadow-xl">
        <button
          onClick={() => setMode('company')}
          className={`px-8 py-3 rounded-xl text-sm font-bold transition-all flex items-center space-x-2 ${mode === 'company' ? 'bg-purple-600 text-white shadow-lg shadow-purple-900/50' : 'text-gray-400 hover:text-gray-200 hover:bg-gray-800'
            }`}
        >
          <Building2 className="w-4 h-4" /> <span>기업 검색 분석</span>
        </button>
        <button
          onClick={() => setMode('manual')}
          className={`px-8 py-3 rounded-xl text-sm font-bold transition-all flex items-center space-x-2 ${mode === 'manual' ? 'bg-purple-600 text-white shadow-lg shadow-purple-900/50' : 'text-gray-400 hover:text-gray-200 hover:bg-gray-800'
            }`}
        >
          <FileText className="w-4 h-4" /> <span>직접 입력 분석</span>
        </button>
      </div>

      {/* Input Area */}
      <div className="w-full max-w-5xl bg-[#1a1d2d] rounded-2xl p-8 border border-gray-800 shadow-2xl mb-12 relative overflow-hidden">
        {/* Background Accents */}
        <div className="absolute top-0 right-0 w-64 h-64 bg-purple-500/5 rounded-full blur-3xl -mr-32 -mt-32 pointer-events-none"></div>

        {mode === 'manual' ? (
          <>
            <textarea
              className="w-full h-48 bg-[#0f111a] text-gray-200 p-6 rounded-xl border border-gray-700/50 focus:border-purple-500 focus:ring-1 focus:ring-purple-500 outline-none transition-all resize-none font-mono text-sm leading-relaxed placeholder-gray-600"
              placeholder="분석하고 싶은 계약서, 뉴스 기사, 또는 공시 원문을 붙여넣으세요..."
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
            />
            <div className="flex justify-end mt-6">
              <button
                onClick={analyzeManual}
                disabled={loading || !inputText.trim()}
                className={`px-8 py-4 rounded-xl font-bold text-lg flex items-center space-x-2 transition-all ${loading || !inputText.trim() ? 'bg-gray-800 text-gray-500 cursor-not-allowed' : 'bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white shadow-lg shadow-purple-900/30 transform active:scale-95'}`}
              >
                {loading ? <><Loader className="animate-spin w-5 h-5" /> <span>Deep Analysis...</span></> : <><Search className="w-5 h-5" /> <span>위험 탐지 시작</span></>}
              </button>
            </div>
          </>
        ) : (
          <div className="flex flex-col md:flex-row space-y-4 md:space-y-0 md:space-x-4">
            <div className="relative flex-1">
              <Search className="absolute left-4 top-1/2 transform -translate-y-1/2 text-gray-500 w-5 h-5" />
              <input
                type="text"
                className="w-full bg-[#0f111a] text-gray-100 pl-12 pr-6 py-5 rounded-xl border border-gray-700/50 focus:border-purple-500 focus:ring-1 focus:ring-purple-500 outline-none text-xl font-bold placeholder-gray-600 transition-all"
                placeholder="기업명 입력 (예: 삼성전자, 유니트론텍...)"
                value={companyName}
                onChange={(e) => setCompanyName(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && searchCompany()}
              />
            </div>
            <button
              onClick={searchCompany}
              disabled={loading || !companyName.trim()}
              className={`px-10 py-5 rounded-xl font-bold text-lg flex items-center justify-center space-x-2 transition-all whitespace-nowrap ${loading || !companyName.trim() ? 'bg-gray-800 text-gray-500 cursor-not-allowed' : 'bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white shadow-lg shadow-purple-900/30 transform active:scale-95'}`}
            >
              {loading ? <><Loader className="animate-spin w-5 h-5" /> <span>DART Scanning...</span></> : <><span>공시 조회 및 분석</span></>}
            </button>
          </div>
        )}

        {/* 🚀 Animated Loading Bar */}
        {loading && (
          <div className="absolute bottom-0 left-0 w-full h-1 bg-gray-800 overflow-hidden rounded-b-2xl">
            <motion.div
              initial={{ x: '-100%' }}
              animate={{ x: '100%' }}
              transition={{ repeat: Infinity, duration: 1.5, ease: "linear" }}
              className="w-1/2 h-full bg-gradient-to-r from-transparent via-purple-500 to-transparent"
            />
          </div>
        )}

        {error && (
          <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }} className="mt-6 p-4 bg-red-500/10 border border-red-500/20 rounded-xl flex items-center text-red-400">
            <AlertCircle className="w-5 h-5 mr-3 flex-shrink-0" />
            <span className="font-medium">{error}</span>
          </motion.div>
        )}
      </div>

      {/* Result Display Area */}
      <AnimatePresence>
        {/* MANUAL RESULT */}
        {mode === 'manual' && manualData && (
          <ResultDashboard data={manualData} isManual={true} />
        )}

        {/* COMPANY RESULT */}
        {mode === 'company' && companyData && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="w-full max-w-7xl space-y-10 mb-20">

            {/* 1. Company Summary Dashboard */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {/* Total Reports */}
              <div className="bg-[#1a1d2d] rounded-2xl p-8 border border-gray-800 shadow-xl flex flex-col justify-center items-center group hover:border-gray-700 transition-colors">
                <BarChart3 className="w-12 h-12 text-purple-500 mb-4 group-hover:scale-110 transition-transform" />
                <div className="text-gray-400 text-lg font-extrabold uppercase tracking-widest">분석 건수</div>
                <div className="text-6xl font-black text-white mt-2">{companyData.summary_stats?.total_reports || 0}<span className="text-2xl text-gray-600 ml-2 font-light">건</span></div>
              </div>

              {/* Average Risk */}
              <div className="bg-[#1a1d2d] rounded-2xl p-8 border border-gray-800 shadow-xl flex flex-col justify-center items-center relative overflow-hidden group">
                <div className={`absolute inset-0 opacity-5 group-hover:opacity-10 transition-opacity ${companyData.summary_stats?.average_risk >= 50 ? 'bg-orange-500' : 'bg-emerald-500'}`}></div>
                <TrendingUp className={`w-12 h-12 mb-4 ${companyData.summary_stats?.average_risk >= 50 ? 'text-orange-500' : 'text-emerald-500'}`} />
                <div className="text-gray-400 text-lg font-extrabold uppercase tracking-widest">평균 위험도</div>
                <div className={`text-7xl font-black mt-2 tracking-tighter ${companyData.summary_stats?.average_risk >= 50 ? 'text-orange-500' : 'text-emerald-500'}`}>
                  {companyData.summary_stats?.average_risk || 0}
                </div>
              </div>

              {/* Worst Clause */}
              <div className="bg-[#1a1d2d] rounded-2xl p-8 border border-gray-800 shadow-xl flex flex-col justify-center relative md:col-span-1 col-span-1 group hover:border-red-500/30 transition-colors">
                <div className="flex items-center space-x-3 mb-4">
                  <div className="p-2 bg-red-500/10 rounded-lg">
                    <AlertTriangle className="w-6 h-6 text-red-500" />
                  </div>
                  <div className="text-gray-400 text-lg font-extrabold uppercase tracking-widest">긴급 독소조항</div>
                </div>
                {companyData.summary_stats?.worst_clause ? (
                  <div className="bg-red-500/5 border border-red-500/20 rounded-xl p-4">
                    <div className="text-xs text-red-400 font-bold mb-2 flex justify-between">
                      <span>{companyData.summary_stats.worst_clause.report_title}</span>
                      <span className="bg-red-500 text-white px-1.5 py-0.5 rounded text-[10px]">CRITICAL</span>
                    </div>
                    <p className="text-sm text-gray-300 font-medium line-clamp-3 leading-relaxed">
                      "{companyData.summary_stats.worst_clause.insight}"
                    </p>
                  </div>
                ) : (
                  <div className="text-gray-600 text-center text-sm py-4 italic">탐지된 치명적 위험이 없습니다.</div>
                )}
              </div>
            </div>

            <div className="flex items-center space-x-4 border-b border-gray-800 pb-6 pt-6">
              <Building2 className="w-8 h-8 text-purple-500" />
              <h2 className="text-3xl font-bold text-white">{companyData.company} <span className="text-xl text-gray-500 font-light px-2">Analysis Report</span></h2>
            </div>

            <div className="grid grid-cols-1 gap-8">
              {companyData.reports.map((report, idx) => (
                <div key={idx} className="bg-[#1a1d2d] rounded-3xl border border-gray-800 overflow-hidden shadow-xl hover:shadow-2xl hover:border-gray-700 transition-all duration-300">
                  {/* Report Header */}
                  <div className="px-8 py-6 bg-[#23273a] border-b border-gray-800 flex justify-between items-center group">
                    <div>
                      <div className="text-xs text-gray-500 mb-1 font-mono">{report.date}</div>
                      <h3 className="text-2xl font-bold text-gray-100 group-hover:text-white transition-colors">{report.title}</h3>
                    </div>
                    <div className={`px-6 py-3 rounded-2xl text-center min-w-[140px] ${report.risk_score >= 50 ? 'bg-orange-500/10 text-orange-500 border border-orange-500/20' : report.risk_score > 0 ? 'bg-yellow-500/10 text-yellow-400 border border-yellow-500/20' : 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'}`}>
                      <div className="text-[10px] font-bold opacity-60 mb-1 tracking-widest">RISK SCORE</div>
                      <div className="text-5xl font-black tracking-tighter">{report.risk_score}</div>
                    </div>
                  </div>

                  {/* Report Content */}
                  <div className="p-8 grid grid-cols-1 md:grid-cols-2 gap-10">
                    {/* Insight Column */}
                    <div>
                      <h4 className="flex items-center text-sm font-bold text-gray-400 mb-5 uppercase tracking-widest"><span className="text-lg mr-2">💡</span> Analysis</h4>
                      <div className="space-y-5">
                        {report.insights.length > 0 ? report.insights.map((ins, i) => (
                          <div key={i} className="pl-5 border-l-2 border-purple-500 relative">
                            <div className="absolute -left-[9px] top-0 w-4 h-4 rounded-full bg-purple-500/20 border-2 border-purple-500"></div>
                            <span className="text-[10px] font-bold text-purple-300 bg-purple-900/30 px-2 py-0.5 rounded mb-2 inline-block border border-purple-500/20 uppercase tracking-wide">
                              {CATEGORY_MAP[ins.category] || ins.category}
                            </span>
                            <p className="text-base text-gray-200 leading-relaxed font-medium">{ins.insight}</p>
                          </div>
                        )) : <p className="text-sm text-gray-600 italic pl-2">특이사항 없음</p>}
                      </div>
                    </div>

                    {/* Evidence Column */}
                    <div>
                      <h4 className="flex items-center text-sm font-bold text-gray-400 mb-5 uppercase tracking-widest"><span className="text-lg mr-2">📜</span> Evidence</h4>
                      <div className="space-y-4">
                        {report.insights.length > 0 ? report.insights.map((ins, i) => (
                          <div key={i} className="bg-[#0f111a] p-5 rounded-2xl border border-gray-800 hover:border-gray-700 transition-colors group">
                            <p className="text-sm text-gray-400 font-mono italic break-all line-clamp-4 leading-relaxed group-hover:text-gray-300">
                              "{ins.evidence || "No Quote"}"
                            </p>
                          </div>
                        )) : <p className="text-sm text-gray-600 italic">근거 문장 없음</p>}
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

// Re-usable Component for Manual Analysis Result
function ResultDashboard({ data }) {
  if (!data) return null;
  return (
    <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="w-full max-w-6xl mb-20">
      <div className={`card mb-8 overflow-hidden border rounded-3xl shadow-2xl ${(data.draft_summary?.risk_score ?? data.risk_score) >= 50 ? 'border-orange-500/30 bg-[#1a1d2d]' :
        (data.draft_summary?.risk_score ?? data.risk_score) > 0 ? 'border-yellow-500/30 bg-[#1a1d2d]' : 'border-emerald-500/30 bg-[#1a1d2d]'
        }`}>
        <div className="p-10 flex items-center justify-between bg-gradient-to-r from-gray-800/50 to-transparent">
          <div>
            <span className="text-sm font-bold tracking-widest text-gray-500 uppercase">Analysis Verdict</span>
            <h2 className={`text-5xl font-black mt-2 mb-2 tracking-tight ${(data.draft_summary?.risk_score ?? data.risk_score) >= 50 ? 'text-orange-500' : (data.draft_summary?.risk_score ?? data.risk_score) > 0 ? 'text-yellow-400' : 'text-emerald-500'}`}>
              {(data.draft_summary?.verdict ?? data.ai_verdict ?? "Unknown").toUpperCase()}
            </h2>
          </div>
          <div className="text-right">
            <div className="text-xs font-bold text-gray-500 uppercase tracking-wider mb-2">RISK SCORE</div>
            <div className={`text-9xl font-black tracking-tighter leading-none ${(data.draft_summary?.risk_score ?? data.risk_score) >= 50 ? 'text-orange-500' : (data.draft_summary?.risk_score ?? data.risk_score) > 0 ? 'text-yellow-400' : 'text-emerald-500'}`}>
              {data.draft_summary?.risk_score ?? data.risk_score}
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 items-start">
        <div className="bg-[#1a1d2d] rounded-3xl border border-gray-800 p-8 shadow-xl h-full">
          <div className="flex items-center space-x-3 mb-8 border-b border-gray-800 pb-5">
            <span className="text-3xl">💡</span>
            <h3 className="text-2xl font-bold text-white">Full Insights</h3>
          </div>
          <div className="space-y-8">
            {((data.details || []).filter(item => item.keyword === '📌 Insight').map((item, idx) => (
              <div key={idx} className="relative pl-6 border-l-4 border-purple-600">
                <h4 className="font-bold text-purple-400 text-sm mb-2 uppercase tracking-wide">{CATEGORY_MAP[item.type] || item.type}</h4>
                <p className="text-gray-200 leading-relaxed text-lg font-medium">{item.context.split('\n\n[Evidence]')[0]}</p>
              </div>
            )))}
          </div>
        </div>

        <div className="bg-[#1a1d2d] rounded-3xl border border-gray-800 p-8 shadow-xl h-full">
          <div className="flex items-center space-x-3 mb-8 border-b border-gray-800 pb-5">
            <span className="text-3xl">📜</span>
            <h3 className="text-2xl font-bold text-white">Verbatim Evidence</h3>
          </div>
          <div className="space-y-6 max-h-[800px] overflow-y-auto pr-2 custom-scrollbar">
            {((data.details || []).map((item, idx) => {
              const evidencePart = item.context.includes('[Evidence]:') ? item.context.split('[Evidence]:')[1] : item.context;
              if (item.keyword === '📌 Insight' && (!evidencePart || evidencePart.includes('No Evidence'))) return null;
              return (
                <div key={idx} className="bg-[#0f111a] p-6 rounded-2xl border border-gray-800 hover:border-gray-600 transition-colors">
                  <p className="text-gray-400 font-mono text-sm leading-relaxed italic">"{evidencePart.replace(/"/g, '').trim()}"</p>
                </div>
              );
            }))}
          </div>
        </div>
      </div>
    </motion.div>
  );
}

export default App;

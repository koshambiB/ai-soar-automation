import { useState, useEffect, useCallback } from "react";
import axios from "axios";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell,
  PieChart, Pie, Legend
} from "recharts";
import {
  Shield, AlertTriangle, Activity, Eye, CheckCircle,
  RefreshCw, ChevronRight, Zap, Brain, TrendingUp, X
} from "lucide-react";

const API = "http://localhost:8000/api/v1";

// ── Colour tokens ─────────────────────────────────────────────────────────────
const RISK_COLOR = {
  critical: "#ff2d55",
  high: "#ff9f0a",
  medium: "#ffd60a",
  low: "#30d158",
  info: "#636366",
};
const RISK_BG = {
  critical: "rgba(255,45,85,.15)",
  high: "rgba(255,159,10,.15)",
  medium: "rgba(255,214,10,.15)",
  low: "rgba(48,209,88,.15)",
  info: "rgba(99,99,102,.15)",
};

// ── Tiny helpers ──────────────────────────────────────────────────────────────
const RiskBadge = ({ level }) => (
  <span style={{
    background: RISK_BG[level] || RISK_BG.info,
    color: RISK_COLOR[level] || RISK_COLOR.info,
    border: `1px solid ${RISK_COLOR[level] || RISK_COLOR.info}44`,
    padding: "2px 10px",
    borderRadius: 99,
    fontSize: 11,
    fontWeight: 700,
    letterSpacing: ".06em",
    textTransform: "uppercase",
  }}>{level || "info"}</span>
);

const SevBadge = ({ sev }) => {
  const c = { critical: "#ff2d55", high: "#ff9f0a", medium: "#ffd60a", low: "#30d158", info: "#636366" };
  return (
    <span style={{
      color: c[sev] || c.info, fontSize: 11, fontWeight: 600,
      textTransform: "uppercase", letterSpacing: ".06em"
    }}>{sev}</span>
  );
};

const fmt = ts => {
  if (!ts) return "—";
  const d = new Date(ts);
  return d.toLocaleString("en-IN", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" });
};

// ── Stat card ─────────────────────────────────────────────────────────────────
const StatCard = ({ label, value, color, icon: Icon, sub }) => (
  <div style={{
    background: "rgba(255,255,255,.04)", border: "1px solid rgba(255,255,255,.08)",
    borderRadius: 16, padding: "20px 24px", flex: 1, minWidth: 140,
    display: "flex", flexDirection: "column", gap: 6,
    borderTop: `3px solid ${color}`,
  }}>
    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
      <span style={{ color: "#8e8e93", fontSize: 12, fontWeight: 600, textTransform: "uppercase", letterSpacing: ".08em" }}>{label}</span>
      {Icon && <Icon size={16} color={color} />}
    </div>
    <div style={{ fontSize: 32, fontWeight: 800, color, fontVariantNumeric: "tabular-nums" }}>{value ?? "—"}</div>
    {sub && <div style={{ fontSize: 11, color: "#636366" }}>{sub}</div>}
  </div>
);

// ── Alert detail modal ────────────────────────────────────────────────────────
const AlertModal = ({ alert, onClose }) => {
  const [analysis, setAnalysis] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!alert) return;
    setLoading(true);
    axios.get(`${API}/analysis/${alert.alert_id}`)
      .then(r => setAnalysis(r.data))
      .catch(() => setAnalysis(null))
      .finally(() => setLoading(false));
  }, [alert]);

  if (!alert) return null;

  return (
    <div style={{
      position: "fixed", inset: 0, background: "rgba(0,0,0,.75)", backdropFilter: "blur(6px)",
      display: "flex", alignItems: "center", justifyContent: "center", zIndex: 9999, padding: 24
    }} onClick={onClose}>
      <div style={{
        background: "#1c1c1e", border: "1px solid rgba(255,255,255,.12)", borderRadius: 20,
        width: "100%", maxWidth: 760, maxHeight: "90vh", overflowY: "auto", padding: 32,
      }} onClick={e => e.stopPropagation()}>

        {/* Header */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 24 }}>
          <div>
            <div style={{ fontFamily: "'DM Mono',monospace", fontSize: 13, color: "#636366", marginBottom: 4 }}>
              {alert.alert_id}
            </div>
            <h2 style={{ margin: 0, fontSize: 22, fontWeight: 800, color: "#f5f5f7" }}>
              {alert.alert_type?.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase())}
            </h2>
            <div style={{ marginTop: 8, display: "flex", gap: 8, alignItems: "center" }}>
              <RiskBadge level={alert.risk_level} />
              <SevBadge sev={alert.severity} />
              <span style={{ fontSize: 12, color: "#636366" }}>{fmt(alert.alert_timestamp)}</span>
            </div>
          </div>
          <button onClick={onClose} style={{
            background: "rgba(255,255,255,.08)", border: "none", borderRadius: 99,
            color: "#f5f5f7", cursor: "pointer", padding: "6px 10px"
          }}><X size={16} /></button>
        </div>

        {/* Source */}
        <div style={{ background: "rgba(255,255,255,.04)", borderRadius: 12, padding: "12px 16px", marginBottom: 16 }}>
          <div style={{ fontSize: 11, color: "#636366", fontWeight: 600, textTransform: "uppercase", letterSpacing: ".08em", marginBottom: 4 }}>Source</div>
          <div style={{ color: "#f5f5f7", fontSize: 14 }}>{alert.source}</div>
        </div>

        {/* ML Analysis */}
        {loading && (
          <div style={{ textAlign: "center", padding: 32, color: "#636366" }}>
            <RefreshCw size={20} style={{ animation: "spin 1s linear infinite" }} />
            <div style={{ marginTop: 8, fontSize: 13 }}>Running ML analysis…</div>
          </div>
        )}

        {analysis && !loading && (
          <>
            {/* Risk scores row */}
            <div style={{ display: "flex", gap: 12, marginBottom: 16 }}>
              <div style={{ flex: 1, background: "rgba(255,255,255,.04)", borderRadius: 12, padding: "14px 16px" }}>
                <div style={{ fontSize: 11, color: "#636366", fontWeight: 600, textTransform: "uppercase", letterSpacing: ".08em", marginBottom: 6 }}>Rule Score</div>
                <div style={{ fontSize: 28, fontWeight: 800, color: RISK_COLOR[analysis.rule_risk_level] || "#f5f5f7" }}>
                  {analysis.rule_score}<span style={{ fontSize: 14, color: "#636366" }}>/100</span>
                </div>
                <RiskBadge level={analysis.rule_risk_level} />
              </div>
              <div style={{ flex: 1, background: "rgba(255,255,255,.04)", borderRadius: 12, padding: "14px 16px" }}>
                <div style={{ fontSize: 11, color: "#636366", fontWeight: 600, textTransform: "uppercase", letterSpacing: ".08em", marginBottom: 6 }}>ML Prediction</div>
                <div style={{ fontSize: 28, fontWeight: 800, color: RISK_COLOR[analysis.ml_risk_level] || "#636366" }}>
                  {analysis.ml_confidence != null ? `${(analysis.ml_confidence * 100).toFixed(0)}%` : "N/A"}
                </div>
                {analysis.ml_risk_level
                  ? <RiskBadge level={analysis.ml_risk_level} />
                  : <span style={{ fontSize: 12, color: "#636366" }}>Model not available</span>}
              </div>
            </div>

            {/* SHAP top features */}
            {analysis.top_features?.length > 0 && (
              <div style={{ background: "rgba(255,255,255,.04)", borderRadius: 12, padding: "14px 16px", marginBottom: 16 }}>
                <div style={{ fontSize: 11, color: "#636366", fontWeight: 600, textTransform: "uppercase", letterSpacing: ".08em", marginBottom: 12, display: "flex", alignItems: "center", gap: 6 }}>
                  <Brain size={12} /> SHAP Feature Importance
                </div>
                {analysis.top_features.map((f, i) => (
                  <div key={i} style={{ marginBottom: 8 }}>
                    <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 3 }}>
                      <span style={{ fontSize: 12, color: "#f5f5f7", fontFamily: "'DM Mono',monospace" }}>{f.feature}</span>
                      <span style={{ fontSize: 12, color: "#636366" }}>val={f.value} · impact={f.impact}</span>
                    </div>
                    <div style={{ height: 4, background: "rgba(255,255,255,.08)", borderRadius: 99 }}>
                      <div style={{
                        height: 4, borderRadius: 99,
                        width: `${Math.min(100, f.impact * 500)}%`,
                        background: f.impact > 0.1 ? "#ff9f0a" : "#30d158",
                        transition: "width .4s ease"
                      }} />
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* Explanation text */}
            {analysis.explanation_text && (
              <div style={{ background: "rgba(48,209,88,.08)", border: "1px solid rgba(48,209,88,.2)", borderRadius: 12, padding: "12px 16px" }}>
                <div style={{ fontSize: 11, color: "#30d158", fontWeight: 600, textTransform: "uppercase", letterSpacing: ".08em", marginBottom: 4 }}>AI Explanation</div>
                <div style={{ fontSize: 13, color: "#aeaeb2", lineHeight: 1.6 }}>{analysis.explanation_text}</div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
};

// ── Main App ──────────────────────────────────────────────────────────────────
export default function App() {
  const [stats, setStats] = useState(null);
  const [alerts, setAlerts] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pages, setPages] = useState(1);
  const [filter, setFilter] = useState({ risk_level: "", severity: "", status: "" });
  const [selected, setSelected] = useState(null);
  const [loading, setLoading] = useState(false);
  const [modelInfo, setModelInfo] = useState(null);
  const [lastRefresh, setLastRefresh] = useState(null);

  const fetchStats = useCallback(async () => {
    try {
      const r = await axios.get(`${API}/alerts/stats/summary`);
      setStats(r.data);
    } catch { }
  }, []);

  const fetchAlerts = useCallback(async (p = 1, f = filter) => {
    setLoading(true);
    try {
      const params = { page: p, page_size: 15, ...Object.fromEntries(Object.entries(f).filter(([, v]) => v)) };
      const r = await axios.get(`${API}/alerts`, { params });
      setAlerts(r.data.alerts);
      setTotal(r.data.total);
      setPages(r.data.pages);
      setPage(p);
    } catch { }
    setLoading(false);
  }, [filter]);

  const fetchModel = useCallback(async () => {
    try {
      const r = await axios.get(`${API}/analysis/model/info`);
      setModelInfo(r.data);
    } catch { }
  }, []);

  const refresh = useCallback(() => {
    fetchStats();
    fetchAlerts(1, filter);
    fetchModel();
    setLastRefresh(new Date());
  }, [fetchStats, fetchAlerts, fetchModel, filter]);

  useEffect(() => { refresh(); }, []);

  const s = stats?.summary;

  // Pie data
  const pieData = s ? [
    { name: "Critical", value: s.critical, color: RISK_COLOR.critical },
    { name: "High", value: s.high, color: RISK_COLOR.high },
    { name: "Medium", value: s.medium, color: RISK_COLOR.medium },
    { name: "Low", value: s.low, color: RISK_COLOR.low },
    { name: "Info", value: s.info, color: RISK_COLOR.info },
  ].filter(d => d.value > 0) : [];

  // Trend bar data
  const trendData = (() => {
    if (!stats?.trend?.length) return [];
    const buckets = {};
    stats.trend.forEach(t => {
      const h = new Date(t.hour).getHours();
      const key = `${h}:00`;
      if (!buckets[key]) buckets[key] = { hour: key };
      buckets[key][t.risk_level] = (buckets[key][t.risk_level] || 0) + Number(t.count);
    });
    return Object.values(buckets).slice(-12);
  })();

  return (
    <div style={{
      minHeight: "100vh",
      background: "#000",
      color: "#f5f5f7",
      fontFamily: "'SF Pro Display',-apple-system,BlinkMacSystemFont,sans-serif",
    }}>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&display=swap');
        * { box-sizing: border-box; margin:0; padding:0; }
        ::-webkit-scrollbar { width:6px; } ::-webkit-scrollbar-track { background:#1c1c1e; }
        ::-webkit-scrollbar-thumb { background:#3a3a3c; border-radius:99px; }
        @keyframes spin { to { transform: rotate(360deg); } }
        @keyframes fadeIn { from { opacity:0; transform:translateY(8px); } to { opacity:1; transform:translateY(0); } }
        .alert-row { transition: background .15s; cursor:pointer; }
        .alert-row:hover { background: rgba(255,255,255,.05) !important; }
        .page-btn { background:rgba(255,255,255,.06); border:1px solid rgba(255,255,255,.1); color:#f5f5f7; border-radius:8px; padding:6px 14px; cursor:pointer; font-size:13px; transition:background .15s; }
        .page-btn:hover { background:rgba(255,255,255,.12); }
        .page-btn:disabled { opacity:.3; cursor:default; }
        .filter-select { background:#1c1c1e; border:1px solid rgba(255,255,255,.1); color:#f5f5f7; border-radius:8px; padding:6px 12px; font-size:13px; outline:none; cursor:pointer; }
      `}</style>

      {/* ── Nav ── */}
      <nav style={{
        borderBottom: "1px solid rgba(255,255,255,.08)",
        padding: "0 32px",
        display: "flex", alignItems: "center", justifyContent: "space-between",
        height: 56, position: "sticky", top: 0, background: "rgba(0,0,0,.85)",
        backdropFilter: "blur(20px)", zIndex: 100,
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <Shield size={20} color="#ff2d55" />
          <span style={{ fontWeight: 800, fontSize: 16, letterSpacing: "-.02em" }}>AI-SOAR</span>
          <span style={{ fontSize: 12, color: "#636366", marginLeft: 4 }}>Analyst Dashboard</span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
          {modelInfo?.ml_available && (
            <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12, color: "#30d158" }}>
              <Brain size={12} /> ML Active
            </div>
          )}
          <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12, color: "#636366" }}>
            <Activity size={12} /> API Connected
          </div>
          <button onClick={refresh} style={{
            background: "rgba(255,255,255,.06)", border: "1px solid rgba(255,255,255,.1)",
            color: "#f5f5f7", borderRadius: 8, padding: "6px 12px", cursor: "pointer",
            display: "flex", alignItems: "center", gap: 6, fontSize: 12,
          }}>
            <RefreshCw size={12} /> Refresh
          </button>
        </div>
      </nav>

      <div style={{ padding: "28px 32px", maxWidth: 1400, margin: "0 auto" }}>

        {/* ── Stat cards ── */}
        {s && (
          <div style={{ display: "flex", gap: 12, marginBottom: 28, flexWrap: "wrap", animation: "fadeIn .4s ease" }}>
            <StatCard label="Total Alerts" value={s.total} color="#636366" icon={Activity} sub={`${s.new_alerts} new`} />
            <StatCard label="Critical" value={s.critical} color={RISK_COLOR.critical} icon={AlertTriangle} sub="Immediate action" />
            <StatCard label="High" value={s.high} color={RISK_COLOR.high} icon={Zap} sub="Needs attention" />
            <StatCard label="Medium" value={s.medium} color={RISK_COLOR.medium} icon={Eye} sub="Monitor closely" />
            <StatCard label="Low / Info" value={(s.low || 0) + (s.info || 0)} color={RISK_COLOR.low} icon={CheckCircle} sub="Background noise" />
          </div>
        )}

        {/* ── Charts row ── */}
        <div style={{ display: "flex", gap: 16, marginBottom: 28 }}>
          {/* Pie */}
          <div style={{
            background: "rgba(255,255,255,.04)", border: "1px solid rgba(255,255,255,.08)",
            borderRadius: 16, padding: 20, width: 280, flexShrink: 0,
          }}>
            <div style={{ fontSize: 12, color: "#8e8e93", fontWeight: 600, textTransform: "uppercase", letterSpacing: ".08em", marginBottom: 12 }}>Risk Distribution</div>
            {pieData.length > 0
              ? <ResponsiveContainer width="100%" height={200}>
                <PieChart>
                  <Pie data={pieData} dataKey="value" cx="50%" cy="50%" innerRadius={50} outerRadius={80} paddingAngle={3}>
                    {pieData.map((d, i) => <Cell key={i} fill={d.color} />)}
                  </Pie>
                  <Tooltip contentStyle={{ background: "#1c1c1e", border: "1px solid rgba(255,255,255,.1)", borderRadius: 8, fontSize: 12 }} />
                  <Legend iconType="circle" iconSize={8} wrapperStyle={{ fontSize: 11 }} />
                </PieChart>
              </ResponsiveContainer>
              : <div style={{ color: "#636366", fontSize: 13, textAlign: "center", paddingTop: 60 }}>No data</div>
            }
          </div>

          {/* Bar trend */}
          <div style={{
            background: "rgba(255,255,255,.04)", border: "1px solid rgba(255,255,255,.08)",
            borderRadius: 16, padding: 20, flex: 1,
          }}>
            <div style={{ fontSize: 12, color: "#8e8e93", fontWeight: 600, textTransform: "uppercase", letterSpacing: ".08em", marginBottom: 12 }}>
              Alert Trend (last 24h)
            </div>
            {trendData.length > 0
              ? <ResponsiveContainer width="100%" height={200}>
                <BarChart data={trendData} barSize={14}>
                  <XAxis dataKey="hour" tick={{ fontSize: 11, fill: "#636366" }} axisLine={false} tickLine={false} />
                  <YAxis tick={{ fontSize: 11, fill: "#636366" }} axisLine={false} tickLine={false} />
                  <Tooltip contentStyle={{ background: "#1c1c1e", border: "1px solid rgba(255,255,255,.1)", borderRadius: 8, fontSize: 12 }} />
                  {["critical", "high", "medium", "low", "info"].map(r => (
                    <Bar key={r} dataKey={r} stackId="a" fill={RISK_COLOR[r]} radius={r === "info" ? [4, 4, 0, 0] : [0, 0, 0, 0]} />
                  ))}
                </BarChart>
              </ResponsiveContainer>
              : <div style={{ color: "#636366", fontSize: 13, textAlign: "center", paddingTop: 60 }}>No trend data in last 24h</div>
            }
          </div>

          {/* ML card */}
          {modelInfo?.metadata && (
            <div style={{
              background: "rgba(255,255,255,.04)", border: "1px solid rgba(255,255,255,.08)",
              borderRadius: 16, padding: 20, width: 220, flexShrink: 0,
            }}>
              <div style={{ fontSize: 12, color: "#8e8e93", fontWeight: 600, textTransform: "uppercase", letterSpacing: ".08em", marginBottom: 12, display: "flex", alignItems: "center", gap: 6 }}>
                <Brain size={12} /> ML Model
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                <div>
                  <div style={{ fontSize: 11, color: "#636366" }}>Accuracy</div>
                  <div style={{ fontSize: 28, fontWeight: 800, color: "#30d158" }}>
                    {((modelInfo.metadata.accuracy || 0) * 100).toFixed(0)}%
                  </div>
                </div>
                <div>
                  <div style={{ fontSize: 11, color: "#636366" }}>Algorithm</div>
                  <div style={{ fontSize: 13, color: "#f5f5f7", fontFamily: "'DM Mono',monospace" }}>RandomForest</div>
                </div>
                <div>
                  <div style={{ fontSize: 11, color: "#636366" }}>Samples</div>
                  <div style={{ fontSize: 13, color: "#f5f5f7" }}>{modelInfo.metadata.n_samples}</div>
                </div>
                <div>
                  <div style={{ fontSize: 11, color: "#636366" }}>Features</div>
                  <div style={{ fontSize: 13, color: "#f5f5f7" }}>{modelInfo.metadata.n_features}</div>
                </div>
                <div>
                  <div style={{ fontSize: 11, color: "#636366" }}>Trained</div>
                  <div style={{ fontSize: 11, color: "#aeaeb2", fontFamily: "'DM Mono',monospace" }}>
                    {modelInfo.metadata.trained_at?.slice(0, 10)}
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* ── Alerts table ── */}
        <div style={{
          background: "rgba(255,255,255,.04)", border: "1px solid rgba(255,255,255,.08)",
          borderRadius: 16, overflow: "hidden",
        }}>
          {/* Table header */}
          <div style={{
            padding: "16px 20px", borderBottom: "1px solid rgba(255,255,255,.08)",
            display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 12,
          }}>
            <div>
              <span style={{ fontWeight: 700, fontSize: 15 }}>Security Alerts</span>
              <span style={{ fontSize: 12, color: "#636366", marginLeft: 8 }}>{total} total</span>
            </div>
            {/* Filters */}
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
              {[
                { key: "risk_level", opts: ["", "critical", "high", "medium", "low", "info"], label: "Risk" },
                { key: "severity", opts: ["", "critical", "high", "medium", "low", "info"], label: "Severity" },
              ].map(({ key, opts, label }) => (
                <select key={key} className="filter-select"
                  value={filter[key]}
                  onChange={e => {
                    const nf = { ...filter, [key]: e.target.value };
                    setFilter(nf);
                    fetchAlerts(1, nf);
                  }}>
                  <option value="">{label}: All</option>
                  {opts.filter(Boolean).map(o => <option key={o} value={o}>{o}</option>)}
                </select>
              ))}
            </div>
          </div>

          {/* Column headers */}
          <div style={{
            display: "grid",
            gridTemplateColumns: "2fr 1fr 1fr 1fr 1fr 80px",
            padding: "10px 20px",
            borderBottom: "1px solid rgba(255,255,255,.06)",
            fontSize: 11, color: "#636366", fontWeight: 600, textTransform: "uppercase", letterSpacing: ".08em",
          }}>
            <span>Alert</span><span>Type</span><span>Severity</span><span>Risk Level</span><span>Time</span><span></span>
          </div>

          {/* Rows */}
          {loading
            ? <div style={{ textAlign: "center", padding: 48, color: "#636366" }}>
              <RefreshCw size={20} style={{ animation: "spin 1s linear infinite" }} />
              <div style={{ marginTop: 8, fontSize: 13 }}>Loading alerts…</div>
            </div>
            : alerts.length === 0
              ? <div style={{ textAlign: "center", padding: 48, color: "#636366", fontSize: 13 }}>No alerts found</div>
              : alerts.map((a, i) => (
                <div key={a.alert_id} className="alert-row"
                  style={{
                    display: "grid", gridTemplateColumns: "2fr 1fr 1fr 1fr 1fr 80px",
                    padding: "14px 20px",
                    borderBottom: i < alerts.length - 1 ? "1px solid rgba(255,255,255,.04)" : "none",
                    animation: `fadeIn .3s ease ${i * 0.03}s both`,
                    alignItems: "center",
                  }}
                  onClick={() => setSelected(a)}
                >
                  <div>
                    <div style={{ fontSize: 13, fontWeight: 600, color: "#f5f5f7", marginBottom: 2 }}>
                      {a.alert_type?.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase())}
                    </div>
                    <div style={{ fontSize: 11, color: "#636366", fontFamily: "'DM Mono',monospace" }}>{a.alert_id}</div>
                  </div>
                  <div style={{ fontSize: 12, color: "#aeaeb2" }}>{a.source}</div>
                  <div><SevBadge sev={a.severity} /></div>
                  <div><RiskBadge level={a.risk_level} /></div>
                  <div style={{ fontSize: 12, color: "#636366" }}>{fmt(a.alert_timestamp)}</div>
                  <div style={{ display: "flex", justifyContent: "flex-end" }}>
                    <ChevronRight size={16} color="#636366" />
                  </div>
                </div>
              ))
          }

          {/* Pagination */}
          {pages > 1 && (
            <div style={{
              padding: "14px 20px", borderTop: "1px solid rgba(255,255,255,.06)",
              display: "flex", justifyContent: "space-between", alignItems: "center",
            }}>
              <span style={{ fontSize: 12, color: "#636366" }}>Page {page} of {pages}</span>
              <div style={{ display: "flex", gap: 8 }}>
                <button className="page-btn" disabled={page <= 1} onClick={() => fetchAlerts(page - 1)}>← Prev</button>
                <button className="page-btn" disabled={page >= pages} onClick={() => fetchAlerts(page + 1)}>Next →</button>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div style={{ marginTop: 20, textAlign: "center", fontSize: 11, color: "#3a3a3c" }}>
          AI-SOAR · Powered by RandomForest + SHAP · FastAPI + Kafka + PostgreSQL
          {lastRefresh && ` · Last refresh ${lastRefresh.toLocaleTimeString()}`}
        </div>
      </div>

      {/* Modal */}
      <AlertModal alert={selected} onClose={() => setSelected(null)} />
    </div>
  );
}
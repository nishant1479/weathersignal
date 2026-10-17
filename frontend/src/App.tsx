import React, { useState, useEffect } from "react";
import {
  fetchReports,
  fetchProviders,
  fetchReviewQueue,
  submitReport,
  startInvestigation,
  fetchInvestigation,
  fetchEvidence,
  submitReview,
} from "./api";
import type {
  Report,
  ProviderStatus,
  ReviewQueueItem,
  InvestigationDetail,
  EvidenceItem,
} from "./types";

export function App() {
  const [tab, setTab] = useState<"overview" | "submit" | "investigation" | "review" | "providers">("overview");
  const [reports, setReports] = useState<Report[]>([]);
  const [providers, setProviders] = useState<ProviderStatus[]>([]);
  const [reviewQueue, setReviewQueue] = useState<ReviewQueueItem[]>([]);
  const [selectedInvId, setSelectedInvId] = useState<string | null>(null);
  const [invDetail, setInvDetail] = useState<InvestigationDetail | null>(null);
  const [evidenceList, setEvidenceList] = useState<EvidenceItem[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Submit form state
  const [reportText, setReportText] = useState("");
  const [placeText, setPlaceText] = useState("");
  const [latitude, setLatitude] = useState("");
  const [longitude, setLongitude] = useState("");

  // Review form state
  const [reviewDecision, setReviewDecision] = useState("CORROBORATED");
  const [reviewReason, setReviewReason] = useState("");

  const loadOverview = async () => {
    try {
      setLoading(true);
      setErrorMsg(null);
      const [reps, provs] = await Promise.all([fetchReports(), fetchProviders()]);
      setReports(reps);
      setProviders(provs);
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to load dashboard data");
    } finally {
      setLoading(false);
    }
  };

  const loadReviewQueue = async () => {
    try {
      setLoading(true);
      const queue = await fetchReviewQueue();
      setReviewQueue(queue);
    } catch (err: any) {
      setErrorMsg(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (tab === "overview") loadOverview();
    if (tab === "review") loadReviewQueue();
    if (tab === "providers") fetchProviders().then(setProviders);
  }, [tab]);

  const handleOpenInvestigation = async (invId: string) => {
    try {
      setLoading(true);
      setSelectedInvId(invId);
      const [detail, ev] = await Promise.all([
        fetchInvestigation(invId),
        fetchEvidence(invId),
      ]);
      setInvDetail(detail);
      setEvidenceList(ev.evidence_items || []);
      setTab("investigation");
    } catch (err: any) {
      setErrorMsg(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmitReport = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setLoading(true);
      setErrorMsg(null);
      const created = await submitReport({
        original_text: reportText,
        place_text: placeText || undefined,
        latitude: latitude ? parseFloat(latitude) : undefined,
        longitude: longitude ? parseFloat(longitude) : undefined,
      });

      // Automatically trigger LangGraph investigation
      const inv = await startInvestigation(created.id);
      await handleOpenInvestigation(inv.investigation_id);
    } catch (err: any) {
      setErrorMsg(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleManualReview = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedInvId) return;
    try {
      setLoading(true);
      await submitReview(selectedInvId, {
        decision: reviewDecision,
        reason: reviewReason,
        reviewer_id: "duty_analyst",
      });
      await handleOpenInvestigation(selectedInvId);
      setReviewReason("");
    } catch (err: any) {
      setErrorMsg(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="app-container">
      <header className="app-header">
        <div className="brand">
          <h1>WeatherSignal</h1>
          <span>Empirical Agentic Weather Verification System</span>
        </div>
      </header>

      <nav className="nav-tabs">
        <button className={tab === "overview" ? "active" : ""} onClick={() => setTab("overview")}>
          Overview
        </button>
        <button className={tab === "submit" ? "active" : ""} onClick={() => setTab("submit")}>
          Submit Report
        </button>
        {selectedInvId && (
          <button className={tab === "investigation" ? "active" : ""} onClick={() => setTab("investigation")}>
            Investigation Detail
          </button>
        )}
        <button className={tab === "review" ? "active" : ""} onClick={() => setTab("review")}>
          Review Queue
        </button>
        <button className={tab === "providers" ? "active" : ""} onClick={() => setTab("providers")}>
          Provider Status
        </button>
      </nav>

      {errorMsg && (
        <div style={{ background: "#7f1d1d", padding: "12px", borderRadius: "6px", marginBottom: "16px" }}>
          <strong>Error:</strong> {errorMsg}
        </div>
      )}

      {loading && <p style={{ color: "#38bdf8", marginBottom: "16px" }}>Loading data from server...</p>}

      {/* OVERVIEW TAB */}
      {tab === "overview" && (
        <div>
          <div className="card">
            <h3>Recent Weather Reports & Investigations</h3>
            <p style={{ color: "#94a3b8", fontSize: "0.85rem", marginBottom: "16px" }}>
              Citizen and social claims queued or processed by the LangGraph verification engine.
            </p>
            {reports.length === 0 ? (
              <p>No reports submitted yet. Use "Submit Report" to investigate a weather event.</p>
            ) : (
              <table className="table">
                <thead>
                  <tr>
                    <th>Report Text</th>
                    <th>Location</th>
                    <th>Submitted</th>
                    <th>Status</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {reports.map((r) => (
                    <tr key={r.id}>
                      <td>{r.original_text}</td>
                      <td>{r.place_text || "Unspecified"}</td>
                      <td>{new Date(r.submitted_at).toLocaleString()}</td>
                      <td>
                        <span className={`badge badge-${r.status}`}>{r.status}</span>
                      </td>
                      <td>
                        <button
                          className="btn-secondary"
                          onClick={async () => {
                            const inv = await startInvestigation(r.id);
                            handleOpenInvestigation(inv.investigation_id);
                          }}
                        >
                          Investigate
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      )}

      {/* SUBMIT TAB */}
      {tab === "submit" && (
        <div className="card" style={{ maxWidth: "700px" }}>
          <h3>Submit a Weather Claim for Verification</h3>
          <p style={{ color: "#94a3b8", fontSize: "0.85rem", marginBottom: "20px" }}>
            Submit an unverified claim. The verification engine will decompose it into testable subclaims,
            resolve coordinates, and query real station observations and bulletins.
          </p>
          <form onSubmit={handleSubmitReport}>
            <div className="form-group">
              <label>Weather Report Text *</label>
              <textarea
                rows={3}
                required
                value={reportText}
                onChange={(e) => setReportText(e.target.value)}
                placeholder="e.g. Heavy rain is flooding roads near the central market at 4:30 PM."
              />
            </div>
            <div className="form-group">
              <label>Place / City Name (Optional)</label>
              <input
                type="text"
                value={placeText}
                onChange={(e) => setPlaceText(e.target.value)}
                placeholder="e.g. Connaught Place, New Delhi or Adilabad"
              />
            </div>
            <div className="grid-2">
              <div className="form-group">
                <label>Latitude (Optional)</label>
                <input
                  type="number"
                  step="any"
                  value={latitude}
                  onChange={(e) => setLatitude(e.target.value)}
                  placeholder="28.6139"
                />
              </div>
              <div className="form-group">
                <label>Longitude (Optional)</label>
                <input
                  type="number"
                  step="any"
                  value={longitude}
                  onChange={(e) => setLongitude(e.target.value)}
                  placeholder="77.2090"
                />
              </div>
            </div>
            <button type="submit" className="btn-primary" disabled={loading}>
              Submit & Investigate
            </button>
          </form>
        </div>
      )}

      {/* INVESTIGATION DETAIL TAB */}
      {tab === "investigation" && invDetail && (
        <div>
          <div className="card">
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
              <div>
                <h2>Investigation Summary</h2>
                <p style={{ color: "#94a3b8", fontSize: "0.9rem" }}>
                  Original Claim: "{invDetail.report?.original_text}"
                </p>
                <p style={{ color: "#94a3b8", fontSize: "0.85rem" }}>
                  Location: {invDetail.report?.place_text || "Unresolved"} | ID: {invDetail.id}
                </p>
              </div>
              <div>
                {invDetail.decision?.overall_status && (
                  <span className={`badge badge-${invDetail.decision.overall_status}`} style={{ fontSize: "1rem", padding: "8px 16px" }}>
                    {invDetail.decision.overall_status}
                  </span>
                )}
              </div>
            </div>

            {invDetail.decision && (
              <div style={{ marginTop: "20px", padding: "16px", background: "#0f172a", borderRadius: "6px" }}>
                <h4 style={{ color: "#38bdf8", marginBottom: "6px" }}>Deterministic Rationale</h4>
                <p>{invDetail.decision.rationale}</p>
                {invDetail.decision.unresolved_questions.length > 0 && (
                  <div style={{ marginTop: "12px" }}>
                    <strong style={{ color: "#fbbf24" }}>Unresolved / Ambiguities:</strong>
                    <ul style={{ marginLeft: "20px", marginTop: "4px" }}>
                      {invDetail.decision.unresolved_questions.map((q, idx) => (
                        <li key={idx} style={{ color: "#cbd5e1" }}>{q}</li>
                      ))}
                    </ul>
                  </div>
                )}
                {invDetail.decision.limitations.length > 0 && (
                  <div style={{ marginTop: "12px" }}>
                    <strong style={{ color: "#94a3b8" }}>Source Limitations:</strong>
                    <ul style={{ marginLeft: "20px", marginTop: "4px" }}>
                      {invDetail.decision.limitations.map((l, idx) => (
                        <li key={idx} style={{ color: "#94a3b8", fontSize: "0.85rem" }}>{l}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}
          </div>

          <div className="grid-2">
            {/* CLAIMS BREAKDOWN */}
            <div className="card">
              <h3>Decomposed Claims</h3>
              <p style={{ color: "#94a3b8", fontSize: "0.85rem", marginBottom: "14px" }}>
                Separately verifiable subclaims extracted from report wording.
              </p>
              {invDetail.claims.map((c) => {
                const claimStatus = invDetail.decision?.per_claim_status?.[c.id] || "UNVERIFIED";
                return (
                  <div key={c.id} style={{ borderBottom: "1px solid #334155", paddingBottom: "12px", marginBottom: "12px" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                      <strong>{c.claim_text}</strong>
                      <span className={`badge badge-${claimStatus}`}>{claimStatus}</span>
                    </div>
                    <div style={{ fontSize: "0.8rem", color: "#94a3b8", marginTop: "4px" }}>
                      Type: {c.event_type} | Severity: {c.severity || "Standard"}
                    </div>
                  </div>
                );
              })}
            </div>

            {/* EVIDENCE ITEMS */}
            <div className="card">
              <h3>Retrieved Evidence ({evidenceList.length})</h3>
              <p style={{ color: "#94a3b8", fontSize: "0.85rem", marginBottom: "14px" }}>
                Empirical observations and bulletins collected from providers.
              </p>
              {evidenceList.map((ev) => (
                <div key={ev.id} style={{ borderBottom: "1px solid #334155", paddingBottom: "12px", marginBottom: "12px" }}>
                  <div style={{ display: "flex", justifyContent: "space-between" }}>
                    <strong style={{ color: "#38bdf8" }}>{ev.provider_name}</strong>
                    <span className="badge" style={{ background: "#334155" }}>{ev.evidence_type}</span>
                  </div>
                  <p style={{ fontSize: "0.85rem", marginTop: "4px" }}>{ev.summary}</p>
                  <div style={{ fontSize: "0.75rem", color: "#64748b", marginTop: "4px" }}>
                    Status: {ev.retrieval_status} | Quality: {ev.data_quality_notes}
                  </div>
                  {ev.assessments && ev.assessments.length > 0 && (
                    <div style={{ marginTop: "6px", fontSize: "0.8rem", color: "#cbd5e1" }}>
                      <em>Assessment: {ev.assessments[0].reason}</em>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* HUMAN REVIEW FORM */}
          <div className="card" style={{ maxWidth: "700px" }}>
            <h3>Human Analyst Review & Override</h3>
            <p style={{ color: "#94a3b8", fontSize: "0.85rem", marginBottom: "14px" }}>
              Authorized analysts can record an official override or approval with auditable rationale.
            </p>
            {invDetail.decision?.reviewer_decision ? (
              <div style={{ background: "#064e3b", padding: "14px", borderRadius: "6px" }}>
                <strong>Reviewed by {invDetail.decision.reviewer_id}:</strong>{" "}
                <span className={`badge badge-${invDetail.decision.reviewer_decision}`}>{invDetail.decision.reviewer_decision}</span>
                <p style={{ marginTop: "6px" }}>Reason: "{invDetail.decision.reviewer_reason}"</p>
                <small style={{ color: "#94a3b8" }}>Timestamp: {new Date(invDetail.decision.reviewed_at!).toLocaleString()}</small>
              </div>
            ) : (
              <form onSubmit={handleManualReview}>
                <div className="form-group">
                  <label>Decision</label>
                  <select value={reviewDecision} onChange={(e) => setReviewDecision(e.target.value)}>
                    <option value="CORROBORATED">CORROBORATED</option>
                    <option value="CONTRADICTED">CONTRADICTED</option>
                    <option value="UNVERIFIED">UNVERIFIED</option>
                    <option value="PARTIALLY_CORROBORATED">PARTIALLY_CORROBORATED</option>
                  </select>
                </div>
                <div className="form-group">
                  <label>Mandatory Reviewer Rationale *</label>
                  <textarea
                    rows={2}
                    required
                    value={reviewReason}
                    onChange={(e) => setReviewReason(e.target.value)}
                    placeholder="Provide explicit operational explanation for the human decision..."
                  />
                </div>
                <button type="submit" className="btn-primary" disabled={loading}>
                  Submit Review Decision
                </button>
              </form>
            )}
          </div>
        </div>
      )}

      {/* REVIEW QUEUE TAB */}
      {tab === "review" && (
        <div className="card">
          <h3>Review Queue</h3>
          <p style={{ color: "#94a3b8", fontSize: "0.85rem", marginBottom: "16px" }}>
            Cases flagged with conflicting evidence, severe claims, or high ambiguity requiring manual review.
          </p>
          {reviewQueue.length === 0 ? (
            <p>Review queue is clear. No investigations currently require human escalation.</p>
          ) : (
            <table className="table">
              <thead>
                <tr>
                  <th>Investigation ID</th>
                  <th>Report Claim</th>
                  <th>Flagged Status</th>
                  <th>Rationale</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {reviewQueue.map((item) => (
                  <tr key={item.investigation_id}>
                    <td>{item.investigation_id.slice(0, 8)}...</td>
                    <td>{item.report_text}</td>
                    <td><span className={`badge badge-${item.overall_status}`}>{item.overall_status}</span></td>
                    <td>{item.rationale}</td>
                    <td>
                      <button
                        className="btn-secondary"
                        onClick={() => handleOpenInvestigation(item.investigation_id)}
                      >
                        Review
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {/* PROVIDERS TAB */}
      {tab === "providers" && (
        <div className="card">
          <h3>Data Provider Health & Connectivity</h3>
          <p style={{ color: "#94a3b8", fontSize: "0.85rem", marginBottom: "16px" }}>
            Real-time status of configured weather observation sources and geocoding services.
          </p>
          <table className="table">
            <thead>
              <tr>
                <th>Provider Name</th>
                <th>Configured</th>
                <th>Status</th>
                <th>Operational Notes</th>
                <th>Last Checked</th>
              </tr>
            </thead>
            <tbody>
              {providers.map((p) => (
                <tr key={p.provider_name}>
                  <td><strong>{p.provider_name}</strong></td>
                  <td>{p.configured ? "Yes" : "No"}</td>
                  <td>
                    <span className="badge" style={{ background: p.status === "HEALTHY" ? "#064e3b" : "#78350f" }}>
                      {p.status}
                    </span>
                  </td>
                  <td>{p.message}</td>
                  <td>{new Date(p.last_checked_at).toLocaleTimeString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

export default App;

const API_BASE = "http://localhost:8000";

export async function fetchHealth() {
  const res = await fetch(`${API_BASE}/health`);
  return res.json();
}

export async function fetchProviders() {
  const res = await fetch(`${API_BASE}/api/v1/providers/status`);
  return res.json();
}

export async function fetchReports() {
  const res = await fetch(`${API_BASE}/api/v1/reports`);
  return res.json();
}

export async function submitReport(payload: {
  original_text: string;
  place_text?: string;
  latitude?: number;
  longitude?: number;
}) {
  const res = await fetch(`${API_BASE}/api/v1/reports`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Submission failed");
  }
  return res.json();
}

export async function startInvestigation(reportId: string) {
  const res = await fetch(`${API_BASE}/api/v1/reports/${reportId}/investigate`, {
    method: "POST",
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Investigation failed");
  }
  return res.json();
}

export async function fetchInvestigation(investigationId: string) {
  const res = await fetch(`${API_BASE}/api/v1/investigations/${investigationId}`);
  if (!res.ok) throw new Error("Failed to load investigation");
  return res.json();
}

export async function fetchEvidence(investigationId: string) {
  const res = await fetch(`${API_BASE}/api/v1/investigations/${investigationId}/evidence`);
  if (!res.ok) throw new Error("Failed to load evidence");
  return res.json();
}

export async function fetchReviewQueue() {
  const res = await fetch(`${API_BASE}/api/v1/review-queue`);
  return res.json();
}

export async function submitReview(
  investigationId: string,
  payload: { decision: string; reason: string; reviewer_id?: string }
) {
  const res = await fetch(`${API_BASE}/api/v1/investigations/${investigationId}/review`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Failed to submit review");
  }
  return res.json();
}

"""Admin API: list quotation requests, submit quote, set urgent, set exception."""

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from src.registry import (
    get_quotation_by_id,
    list_quotation_requests,
    set_quotation_urgent,
    update_quotation_exception,
    update_quotation_quote,
)

router = APIRouter(prefix="/admin", tags=["admin"])


class QuoteBody(BaseModel):
    amount: float
    max_discount_pct: float


class ExceptionBody(BaseModel):
    exception_amount: float


class UrgentBody(BaseModel):
    urgent: bool = True


ADMIN_DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Admin — Quotations</title>
  <style>
    * { box-sizing: border-box; }
    body { font-family: system-ui, sans-serif; margin: 0; padding: 1rem; background: #1a1a2e; color: #eee; }
    h1 { margin-top: 0; }
    a { color: #7eb8da; }
    table { width: 100%; border-collapse: collapse; margin-top: 1rem; font-size: 0.9rem; }
    th, td { border: 1px solid #2f3336; padding: 0.5rem 0.75rem; text-align: left; }
    th { background: #16213e; }
    tr.urgent { background: #2d1f1f; }
    .badge { display: inline-block; padding: 0.15em 0.5em; border-radius: 4px; font-size: 0.75rem; }
    .badge.pending { background: #d35400; }
    .badge.ready { background: #3498db; }
    .badge.sent { background: #2ecc71; }
    .badge.negotiating { background: #f39c12; }
    .badge.agreed { background: #27ae60; }
    .badge.rejected { background: #c0392b; }
    .actions { display: flex; flex-wrap: wrap; gap: 0.5rem; align-items: center; }
    .actions input { width: 6rem; padding: 0.25rem; }
    .actions button { padding: 0.25rem 0.5rem; cursor: pointer; border-radius: 4px; border: none; background: #3498db; color: #fff; }
    .actions button.urgent { background: #c0392b; }
    .rejection { color: #e74c3c; font-size: 0.85rem; }
    #filter { margin-bottom: 1rem; }
  </style>
</head>
<body>
  <h1>Admin — Quotation requests</h1>
  <p><a href="/">User chat</a> | <a href="/dashboard">Company dashboard</a></p>
  <div id="filter"><label><input type="checkbox" id="urgentOnly"> Urgent only</label></div>
  <div id="loading">Loading…</div>
  <table id="table" style="display:none">
    <thead>
      <tr>
        <th>ID</th>
        <th>Session</th>
        <th>Status</th>
        <th>Created</th>
        <th>Quoted (Rs)</th>
        <th>Max discount %</th>
        <th>Offered %</th>
        <th>User asked (Rs)</th>
        <th>Exception (Rs)</th>
        <th>Urgent</th>
        <th>Rejection reason</th>
        <th>Actions</th>
      </tr>
    </thead>
    <tbody id="tbody"></tbody>
  </table>
  <script>
    const API = '/admin';
    async function load(urgentOnly) {
      const url = urgentOnly ? API + '/quotations?urgent=1' : API + '/quotations';
      const r = await fetch(url);
      const d = await r.json();
      return d.quotations || [];
    }
    function render(rows) {
      const tbody = document.getElementById('tbody');
      document.getElementById('loading').style.display = 'none';
      document.getElementById('table').style.display = 'table';
      tbody.innerHTML = rows.map(q => {
        const status = (q.status || '').replace(/_/g, ' ');
        const rowClass = q.is_urgent ? 'urgent' : '';
        let actions = '';
        if (q.status === 'pending_quote') {
          actions = `<div class="actions">
            <input type="number" placeholder="Amount" id="amt-${q.id}" step="100">
            <input type="number" placeholder="Max disc %" id="disc-${q.id}" min="0" max="100" step="0.5">
            <button onclick="submitQuote(${q.id})">Submit quote</button>
            <button class="urgent" onclick="setUrgent(${q.id})">Mark urgent</button>
          </div>`;
        } else if ((q.status === 'sent_to_user' || q.status === 'negotiating') && q.user_counter_price != null) {
          actions = `<div class="actions">
            <span>User asked: Rs ${Number(q.user_counter_price).toLocaleString()}</span>
            <input type="number" placeholder="Exception Rs" id="exc-${q.id}" step="100">
            <button onclick="setException(${q.id})">Set exception</button>
          </div>`;
        } else if (q.status === 'negotiating' || q.status === 'sent_to_user') {
          actions = '<span>Waiting for user or set exception</span>';
        }
        return `<tr class="${rowClass}">
          <td>${q.id}</td>
          <td>${q.session_id}</td>
          <td><span class="badge ${q.status}">${status}</span></td>
          <td>${(q.created_at || '').slice(0, 19)}</td>
          <td>${q.admin_quoted_amount != null ? Number(q.admin_quoted_amount).toLocaleString() : '—'}</td>
          <td>${q.admin_max_discount_pct != null ? q.admin_max_discount_pct : '—'}</td>
          <td>${q.discount_offered_to_user_pct != null ? q.discount_offered_to_user_pct : '—'}</td>
          <td>${q.user_counter_price != null ? Number(q.user_counter_price).toLocaleString() : '—'}</td>
          <td>${q.admin_exception_amount != null ? Number(q.admin_exception_amount).toLocaleString() : '—'}</td>
          <td>${q.is_urgent ? 'Yes' : 'No'}</td>
          <td class="rejection">${q.rejection_reason || '—'}</td>
          <td>${actions}</td>
        </tr>`;
      }).join('');
    }
    async function submitQuote(id) {
      const amt = document.getElementById('amt-' + id);
      const disc = document.getElementById('disc-' + id);
      const amount = parseFloat(amt && amt.value);
      const max_discount_pct = parseFloat(disc && disc.value);
      if (isNaN(amount) || isNaN(max_discount_pct)) { alert('Enter amount and max discount %'); return; }
      const r = await fetch(API + '/quotations/' + id + '/quote', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ amount, max_discount_pct })
      });
      if (!r.ok) { const e = await r.json(); alert(e.detail || 'Failed'); return; }
      refresh();
    }
    async function setUrgent(id) {
      const r = await fetch(API + '/quotations/' + id + '/urgent', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ urgent: true })
      });
      if (!r.ok) { alert('Failed'); return; }
      refresh();
    }
    async function setException(id) {
      const el = document.getElementById('exc-' + id);
      const v = parseFloat(el && el.value);
      if (isNaN(v)) { alert('Enter exception amount'); return; }
      const r = await fetch(API + '/quotations/' + id + '/exception', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ exception_amount: v })
      });
      if (!r.ok) { const e = await r.json(); alert(e.detail || 'Failed'); return; }
      refresh();
    }
    function refresh() {
      const urgentOnly = document.getElementById('urgentOnly').checked;
      load(urgentOnly).then(render);
    }
    document.getElementById('urgentOnly').addEventListener('change', refresh);
    refresh();
  </script>
</body>
</html>
"""


@router.get("/", response_class=HTMLResponse)
def admin_dashboard_page():
    """Admin dashboard: quotation requests table, enter quote, urgent, exception, rejection reason."""
    return ADMIN_DASHBOARD_HTML


@router.get("/quotations")
def admin_list_quotations(urgent: bool | None = None):
    """List all quotation requests. ?urgent=1 for urgent only."""
    items = list_quotation_requests(urgent_only=bool(urgent))
    return {"quotations": items}


@router.get("/quotations/{qid}")
def admin_get_quotation(qid: int):
    """Get one quotation request (for detail / enter quote / set exception)."""
    row = get_quotation_by_id(qid)
    if not row:
        raise HTTPException(status_code=404, detail="Quotation not found")
    return row


@router.post("/quotations/{qid}/quote")
def admin_submit_quote(qid: int, body: QuoteBody):
    """Admin enters quoted amount and max discount %."""
    amount = body.amount
    max_discount_pct = body.max_discount_pct
    row = get_quotation_by_id(qid)
    if not row:
        raise HTTPException(status_code=404, detail="Quotation not found")
    if row["status"] != "pending_quote":
        raise HTTPException(
            status_code=400,
            detail=f"Quotation status is {row['status']}, cannot set quote",
        )
    ok = update_quotation_quote(qid, amount, max_discount_pct)
    if not ok:
        raise HTTPException(status_code=500, detail="Update failed")
    return {"ok": True, "quotation": get_quotation_by_id(qid)}


@router.post("/quotations/{qid}/urgent")
def admin_set_urgent(qid: int, body: UrgentBody | None = None):
    """Mark quotation as urgent."""
    urgent = body.urgent if body else True
    row = get_quotation_by_id(qid)
    if not row:
        raise HTTPException(status_code=404, detail="Quotation not found")
    ok = set_quotation_urgent(qid, is_urgent=urgent)
    if not ok:
        raise HTTPException(status_code=500, detail="Update failed")
    return {"ok": True, "is_urgent": urgent}


@router.post("/quotations/{qid}/exception")
def admin_set_exception(qid: int, body: ExceptionBody):
    """Admin sets exception price (user asked for lower; admin approves one-time)."""
    exception_amount = body.exception_amount
    row = get_quotation_by_id(qid)
    if not row:
        raise HTTPException(status_code=404, detail="Quotation not found")
    ok = update_quotation_exception(qid, exception_amount)
    if not ok:
        raise HTTPException(status_code=500, detail="Update failed")
    return {"ok": True, "quotation": get_quotation_by_id(qid)}
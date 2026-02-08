"""Phase 7: Simple dashboard HTML (loads first: today, hot leads, estimates, complaints)."""

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Conversation Intelligence Dashboard</title>
  <style>
    * { box-sizing: border-box; }
    body { font-family: system-ui, sans-serif; margin: 0; padding: 1rem; background: #1a1a2e; color: #eee; }
    h1 { margin-top: 0; }
    .section { margin-bottom: 2rem; }
    .section h2 { font-size: 1rem; text-transform: uppercase; letter-spacing: .05em; color: #a0a0a0; margin-bottom: .5rem; }
    .card { background: #16213e; border-radius: 8px; padding: 1rem; margin-bottom: .5rem; }
    .card a { color: #7eb8da; text-decoration: none; }
    .card a:hover { text-decoration: underline; }
    .meta { font-size: 0.85rem; color: #888; margin-top: .25rem; }
    .badge { display: inline-block; padding: .15em .5em; border-radius: 4px; font-size: 0.75rem; margin-right: .25rem; }
    .badge.hot { background: #c0392b; }
    .badge.warm { background: #d35400; }
    .badge.cold { background: #7f8c8d; }
    #drill { margin-top: 2rem; padding: 1rem; background: #0f0f1a; border-radius: 8px; display: none; }
    #drill.visible { display: block; }
    #drill pre { white-space: pre-wrap; font-size: 0.85rem; }
    .needs-human { background: #d35400; color: #fff; padding: .25rem .5rem; border-radius: 4px; font-size: 0.85rem; }
  </style>
</head>
<body>
  <h1>Conversation Intelligence</h1>
  <div id="loading">Loading…</div>
  <div id="home" style="display:none;">
    <div class="section">
      <h2>Today's conversations</h2>
      <div id="todays"></div>
    </div>
    <div class="section">
      <h2>Hot leads</h2>
      <div id="hot"></div>
    </div>
    <div class="section">
      <h2>Estimation requests</h2>
      <div id="estimates"></div>
    </div>
    <div class="section">
      <h2>Complaints</h2>
      <div id="complaints"></div>
    </div>
  </div>
  <div id="drill">
    <h2>Conversation detail</h2>
    <div id="drill-content"></div>
  </div>
  <script>
    const API = '';
    async function loadHome() {
      const r = await fetch(API + '/dashboard/home');
      const d = await r.json();
      document.getElementById('loading').style.display = 'none';
      document.getElementById('home').style.display = 'block';
      renderList('todays', d.todays_conversations);
      renderList('hot', d.hot_leads);
      renderList('estimates', d.estimation_requests);
      renderList('complaints', d.complaints);
    }
    function renderList(id, items) {
      const el = document.getElementById(id);
      if (!items || items.length === 0) { el.innerHTML = '<div class="card">None</div>'; return; }
      el.innerHTML = items.map(c => `
        <div class="card">
          <a href="#" data-id="${c.conversation_id}" class="drill-link">${c.conversation_id}</a>
          <span class="meta">${c.primary_intent || '—'} · ${c.lead_band || ''} · ${c.lead_score != null ? c.lead_score + ' pts' : ''}</span>
        </div>
      `).join('');
      el.querySelectorAll('.drill-link').forEach(a => {
        a.addEventListener('click', e => { e.preventDefault(); drillDown(a.dataset.id); });
      });
    }
    async function drillDown(id) {
      const r = await fetch(API + '/dashboard/conversations/' + encodeURIComponent(id));
      const d = await r.json();
      const dc = document.getElementById('drill-content');
      dc.innerHTML = `
        <p><strong>Intent:</strong> ${d.intent || '—'} ${d.needs_human ? '<span class="needs-human">Needs human</span>' : ''}</p>
        <p><strong>Tags:</strong> ${(d.tags || []).join(', ') || '—'}</p>
        <p><strong>Missing fields:</strong> ${(d.missing_fields || []).join(', ') || 'None'}</p>
        <p><strong>Extracted:</strong></p>
        <pre>${JSON.stringify(d.extracted_details || {}, null, 2)}</pre>
        <p><strong>Summary:</strong> ${d.summary || '—'}</p>
        <details><summary>Full transcript</summary><pre>${(d.full_transcript || '').replace(/</g, '&lt;')}</pre></details>
      `;
      document.getElementById('drill').classList.add('visible');
    }
    loadHome();
  </script>
</body>
</html>
"""

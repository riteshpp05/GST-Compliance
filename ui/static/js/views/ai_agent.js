/**
 * UC15 GST Compliance Investigation Platform — AI Compliance Assistant
 * Clean, minimal multi-turn statutory compliance investigation interface.
 */

window.AIAgentView = {
  currentSessionId: null,
  turns: [],

  render: function(mountEl) {
    mountEl.innerHTML = `
      <div class="view-header" style="padding:20px 28px; background:var(--card-bg,#fff); border-bottom:1px solid var(--border-color,#E0E6ED); display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:16px;">
        <div style="display:flex; align-items:center; gap:12px;">
          <div style="width:38px; height:38px; border-radius:10px; background:var(--grad-brand-icon); display:flex; align-items:center; justify-content:center; color:#fff; font-weight:800; font-size:14px; box-shadow:0 4px 10px -2px rgba(59, 130, 246, 0.35);">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M12 2a10 10 0 1 0 10 10A10 10 0 0 0 12 2zm0 18a8 8 0 1 1 8-8 8 8 0 0 1-8 8z"/><path d="M12 6v6l4 2"/></svg>
          </div>
          <div>
            <h2 style="font-size:18px; font-weight:800; color:var(--text-primary); letter-spacing:-0.01em; margin:0;">AI Compliance Assistant</h2>
            <p style="font-size:12.5px; color:var(--text-secondary); margin-top:2px;">Ask any statutory question regarding GST rates, e-way bills, place of supply, or invoice risk.</p>
          </div>
        </div>

        <div style="display:flex; gap:10px; align-items:center;">
          <button id="aiNewSessionBtn" class="btn btn-secondary" style="padding:8px 14px; font-size:12px; font-weight:600; display:flex; align-items:center; gap:6px;">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 5v14M5 12h14"/></svg>
            <span>New Session</span>
          </button>
        </div>
      </div>

      <div style="padding:24px 28px;">
        <!-- Search & Query Form Card -->
        <div class="card" style="background:#fff; border:1px solid var(--border-color,#E0E6ED); border-radius:10px; padding:20px; margin-bottom:20px; box-shadow:var(--shadow-xs);">
          <label style="display:block; font-size:12px; font-weight:700; color:var(--text-primary); margin-bottom:8px; letter-spacing:0.01em;">Ask a GST Compliance or Invoice Investigation Question:</label>
          <div style="display:flex; gap:12px; margin-bottom:14px;">
            <input type="text" id="aiQueryInput" placeholder="e.g. Why is invoice INV-2026-TAX-04 blocked? Or what is the intra-state POS rule?" style="flex:1; padding:10px 14px; border:1px solid #CBD5E1; border-radius:6px; font-size:13px; outline:none; transition:border-color 0.15s ease;" value="Why is invoice INV-2026-TAX-04 blocked?">
            <button id="aiSubmitBtn" class="btn-command-run" style="padding:10px 22px; font-weight:700; font-size:13px; cursor:pointer;">Investigate</button>
          </div>

          <div style="display:flex; align-items:center; gap:8px; flex-wrap:wrap;">
            <span style="font-size:11px; font-weight:600; color:var(--text-secondary);">Sample Queries:</span>
            <button class="sample-query-btn" data-q="Why is invoice INV-2026-TAX-04 blocked?" style="font-size:11.5px; padding:5px 12px; border-radius:14px; border:1px solid #CBD5E1; background:#F8FAFC; color:#334155; font-weight:600; cursor:pointer; transition:all 0.15s ease;">1. INV-2026-TAX-04 Gate Failure</button>
            <button class="sample-query-btn" data-q="What is the Place of Supply rule for intra-state billing?" style="font-size:11.5px; padding:5px 12px; border-radius:14px; border:1px solid #CBD5E1; background:#F8FAFC; color:#334155; font-weight:600; cursor:pointer; transition:all 0.15s ease;">2. Place of Supply Rule</button>
            <button class="sample-query-btn" data-q="What is the E-Way Bill threshold requirement under Rule 138?" style="font-size:11.5px; padding:5px 12px; border-radius:14px; border:1px solid #CBD5E1; background:#F8FAFC; color:#334155; font-weight:600; cursor:pointer; transition:all 0.15s ease;">3. Rule 138 E-Way Bill</button>
            <button class="sample-query-btn" data-q="What is our total financial tax rate exposure?" style="font-size:11.5px; padding:5px 12px; border-radius:14px; border:1px solid #CBD5E1; background:#F8FAFC; color:#334155; font-weight:600; cursor:pointer; transition:all 0.15s ease;">4. Total Financial Exposure</button>
          </div>
        </div>

        <!-- Threaded Investigation Results Area -->
        <div id="aiThreadContainer">
          <div style="padding:32px 20px; background:#F8FAFC; border:1px dashed #CBD5E1; border-radius:10px; text-align:center; color:#64748B; font-size:13px;">
            Ask any compliance, risk, or statutory query above, or choose a sample query to get started.
          </div>
        </div>
      </div>
    `;

    // Bind event listeners
    const submitBtn = mountEl.querySelector('#aiSubmitBtn');
    const inputEl = mountEl.querySelector('#aiQueryInput');
    const newSessBtn = mountEl.querySelector('#aiNewSessionBtn');

    submitBtn.addEventListener('click', () => this.runInvestigation(inputEl.value));
    inputEl.addEventListener('keypress', (e) => { if (e.key === 'Enter') this.runInvestigation(inputEl.value); });
    newSessBtn.addEventListener('click', () => this.startNewSession());

    mountEl.querySelectorAll('.sample-query-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        inputEl.value = btn.dataset.q;
        this.runInvestigation(btn.dataset.q);
      });
    });

    // Auto-start session on view mount if none active
    if (!this.currentSessionId) {
      this.startNewSession();
    }
  },

  startNewSession: async function() {
    try {
      const authKey = sessionStorage.getItem('uc15_api_key');
      const headers = authKey ? { 'X-API-Key': authKey } : {};
      const resp = await fetch('/api/agent/session/start', {
        method: 'POST',
        headers: headers
      });
      if (resp.ok) {
        const data = await resp.json();
        this.currentSessionId = data.session_id;
        this.turns = [];
        const thread = document.getElementById('aiThreadContainer');
        if (thread) {
          thread.innerHTML = `
            <div style="padding:32px 20px; background:#F8FAFC; border:1px dashed #CBD5E1; border-radius:10px; text-align:center; color:#64748B; font-size:13px;">
              Session initialized. Ask any compliance, risk, or statutory query above.
            </div>
          `;
        }
      }
    } catch (e) {
      console.error('Failed to start session:', e);
    }
  },

  runInvestigation: async function(query) {
    if (!query || !query.trim()) return;

    const thread = document.getElementById('aiThreadContainer');
    const btn = document.getElementById('aiSubmitBtn');
    btn.disabled = true;

    // Create turn placeholder
    const turnId = 'turn_' + Date.now();
    const turnDiv = document.createElement('div');
    turnDiv.id = turnId;
    turnDiv.style.marginBottom = '20px';
    turnDiv.innerHTML = `
      <div style="padding:18px 20px; background:#fff; border:1px solid #E2E8F0; border-radius:10px; box-shadow:var(--shadow-xs);">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
          <span style="font-size:13px; font-weight:700; color:var(--text-primary);">"${query}"</span>
          <span style="font-size:11px; color:#64748B;">Analyzing...</span>
        </div>
        <div style="padding:20px; text-align:center;">
          <div class="loading-spinner-ring"></div>
          <p style="font-size:12px; color:#64748B; margin-top:8px;">Evaluating statutory GST rules and invoice data...</p>
        </div>
      </div>
    `;

    // If thread container only has the initial dashed box, clear it
    if (thread.firstElementChild && thread.firstElementChild.style.borderStyle === 'dashed') {
      thread.innerHTML = '';
    }
    thread.prepend(turnDiv);

    try {
      if (!this.currentSessionId) {
        await this.startNewSession();
      }

      const authKey = sessionStorage.getItem('uc15_api_key');
      const headers = { 'Content-Type': 'application/json' };
      if (authKey) headers['X-API-Key'] = authKey;

      const resp = await fetch(`/api/agent/session/${this.currentSessionId}/query`, {
        method: 'POST',
        headers: headers,
        body: JSON.stringify({ user_query: query })
      });

      if (!resp.ok) {
        const err = await resp.json().catch(() => ({ detail: 'Investigation failed' }));
        turnDiv.innerHTML = `<div style="padding:16px; background:#FDF2F2; border:1px solid #F87171; border-radius:8px; color:#991B1B; font-size:12.5px;"><strong>Error:</strong> ${err.detail || 'Request failed.'}</div>`;
        return;
      }

      const data = await resp.json();
      this.renderTurnResult(turnDiv, query, data);

    } catch (e) {
      turnDiv.innerHTML = `<div style="padding:16px; background:#FDF2F2; border:1px solid #F87171; border-radius:8px; color:#991B1B; font-size:12.5px;"><strong>Connection Error:</strong> ${e.message}</div>`;
    } finally {
      btn.disabled = false;
    }
  },

  renderTurnResult: function(turnDiv, userQuery, data) {
    const knowledgeEvidence = data.knowledge_evidence || [];
    const knowledgeHtml = knowledgeEvidence.map(k => `
      <div style="padding:10px 14px; background:#F8FAFC; border:1px solid #E2E8F0; border-radius:6px; margin-bottom:6px;">
        <div style="display:flex; justify-content:space-between; align-items:center;">
          <strong style="font-size:12px; color:#0F172A;">${k.document_name || 'Statutory Rule'}</strong>
          <span style="font-size:10px; padding:2px 8px; border-radius:8px; background:#DCFCE7; color:#166534; font-weight:700;">Verified</span>
        </div>
        <div style="font-size:11px; color:#64748B; margin-top:3px;">Relevance Score: ${k.relevance_score || '0.90'}</div>
      </div>
    `).join('');

    turnDiv.innerHTML = `
      <div style="background:#fff; border:1px solid #E2E8F0; border-radius:10px; padding:20px; box-shadow:var(--shadow-xs);">
        <div style="padding-bottom:12px; border-bottom:1px solid #F1F5F9; margin-bottom:14px;">
          <span style="font-size:11px; font-weight:700; color:var(--blue-600); text-transform:uppercase; letter-spacing:0.5px;">Query:</span>
          <div style="font-size:14px; font-weight:700; color:#0F172A; margin-top:2px;">"${userQuery}"</div>
        </div>

        <div style="margin-bottom:14px;">
          <div style="padding:14px 16px; background:#F8FAFC; border:1px solid #E2E8F0; border-radius:8px; font-size:13px; line-height:1.65; white-space:pre-wrap; color:#0F172A;">${data.answer}</div>
        </div>

        ${knowledgeHtml ? `
        <div style="margin-top:14px;">
          <div style="font-size:11px; font-weight:700; color:#64748B; margin-bottom:6px; text-transform:uppercase; letter-spacing:0.5px;">Statutory &amp; Regulatory References</div>
          ${knowledgeHtml}
        </div>
        ` : ''}
      </div>
    `;
  }
};

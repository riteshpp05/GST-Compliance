/**
 * UC15 GST Compliance Investigation Platform — Case Management & Human Approval View
 * Clean, structured human decision & sign-off portal for tax managers.
 */

window.CaseManagementView = {
  cases: [],
  activeFilter: 'ALL',
  selectedCaseId: null,

  render: function(mountEl) {
    mountEl.innerHTML = `
      <div class="view-header" style="padding:20px 28px; background:var(--card-bg,#fff); border-bottom:1px solid var(--border-color,#E0E6ED); display:flex; justify-content:space-between; align-items:center;">
        <div style="display:flex; align-items:center; gap:12px;">
          <div style="width:36px; height:36px; border-radius:8px; background:linear-gradient(135deg, #1E293B, #2563EB); display:flex; align-items:center; justify-content:center; color:#fff; font-weight:800; font-size:16px;">TA</div>
          <div>
            <h2 style="font-size:18px; font-weight:700; color:var(--text-primary);">Tax Approval Center &amp; Human Sign-off</h2>
            <p style="font-size:12px; color:var(--text-secondary); margin-top:2px;">Review non-compliant &amp; blocked invoices, authorize tax approvals, or reject from GSTR filing.</p>
          </div>
        </div>

        <div style="display:flex; gap:10px;">
          <button id="cmRefreshBtn" style="background:#F1F5F9; color:#334155; border:1px solid #CBD5E1; border-radius:6px; padding:8px 14px; font-weight:600; font-size:12px; cursor:pointer;">Refresh Queue</button>
        </div>
      </div>

      <div style="padding:24px 28px;">
        <!-- Top Summary Cards -->
        <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(180px, 1fr)); gap:14px; margin-bottom:24px;" id="cmSummaryCards">
          <div style="background:#fff; border:1px solid var(--border); border-radius:10px; padding:16px 18px; box-shadow:var(--shadow-xs);">
            <div style="font-size:11px; font-weight:700; color:var(--text-muted); text-transform:uppercase; letter-spacing:0.5px;">Total Cases</div>
            <div id="cmStatTotal" style="font-size:22px; font-weight:800; color:var(--text-primary); margin-top:4px; font-family:var(--font-mono);">0</div>
            <div style="font-size:11px; color:var(--text-secondary); margin-top:2px;">All statutory items</div>
          </div>
          <div style="background:var(--grad-blocked); border:1px solid #FECACA; border-radius:10px; padding:16px 18px; box-shadow:var(--shadow-xs);">
            <div style="font-size:11px; font-weight:700; color:var(--rose-700); text-transform:uppercase; letter-spacing:0.5px;">Blocked</div>
            <div id="cmStatBlocked" style="font-size:22px; font-weight:800; color:var(--rose-700); margin-top:4px; font-family:var(--font-mono);">0</div>
            <div style="font-size:11px; color:var(--rose-600); margin-top:2px;">Hard GSTR hold</div>
          </div>
          <div style="background:var(--grad-review); border:1px solid #FDE68A; border-radius:10px; padding:16px 18px; box-shadow:var(--shadow-xs);">
            <div style="font-size:11px; font-weight:700; color:var(--amber-700); text-transform:uppercase; letter-spacing:0.5px;">Needs Review</div>
            <div id="cmStatReview" style="font-size:22px; font-weight:800; color:var(--amber-700); margin-top:4px; font-family:var(--font-mono);">0</div>
            <div style="font-size:11px; color:var(--amber-600); margin-top:2px;">Single gate SLA</div>
          </div>
          <div style="background:var(--grad-compliant); border:1px solid #A7F3D0; border-radius:10px; padding:16px 18px; box-shadow:var(--shadow-xs);">
            <div style="font-size:11px; font-weight:700; color:#047857; text-transform:uppercase; letter-spacing:0.5px;">Approved</div>
            <div id="cmStatApproved" style="font-size:22px; font-weight:800; color:#047857; margin-top:4px; font-family:var(--font-mono);">0</div>
            <div style="font-size:11px; color:#059669; margin-top:2px;">Authorized for filing</div>
          </div>
          <div style="background:#FFF1F2; border:1px solid #FECDD3; border-radius:10px; padding:16px 18px; box-shadow:var(--shadow-xs);">
            <div style="font-size:11px; font-weight:700; color:#B91C1C; text-transform:uppercase; letter-spacing:0.5px;">Rejected</div>
            <div id="cmStatRejected" style="font-size:22px; font-weight:800; color:#B91C1C; margin-top:4px; font-family:var(--font-mono);">0</div>
            <div style="font-size:11px; color:#DC2626; margin-top:2px;">Held from filing</div>
          </div>
        </div>

        <!-- Filter Toolbar -->
        <div style="display:flex; gap:8px; margin-bottom:20px; flex-wrap:wrap;" id="cmFilterToolbar">
          <div class="filter-chip cm-chip on" data-status="ALL" style="cursor:pointer; padding:7px 16px; border-radius:20px; border:1px solid transparent; background:var(--grad-primary); color:#fff; font-size:12px; font-weight:700; box-shadow:0 2px 6px -1px rgba(37, 99, 235, 0.3); transition:all 0.15s ease;">All Cases</div>
          <div class="filter-chip cm-chip" data-status="BLOCKED" style="cursor:pointer; padding:7px 16px; border-radius:20px; border:1px solid #FCA5A5; background:#fff; color:#991B1B; font-size:12px; font-weight:700; transition:all 0.15s ease;">Blocked / Non-Compliant</div>
          <div class="filter-chip cm-chip" data-status="NEEDS_REVIEW" style="cursor:pointer; padding:7px 16px; border-radius:20px; border:1px solid #FDE68A; background:#fff; color:#B45309; font-size:12px; font-weight:700; transition:all 0.15s ease;">Needs Review</div>
          <div class="filter-chip cm-chip" data-status="APPROVED" style="cursor:pointer; padding:7px 16px; border-radius:20px; border:1px solid #A7F3D0; background:#fff; color:#047857; font-size:12px; font-weight:700; transition:all 0.15s ease;">Approved</div>
          <div class="filter-chip cm-chip" data-status="REJECTED" style="cursor:pointer; padding:7px 16px; border-radius:20px; border:1px solid #FECDD3; background:#fff; color:#B91C1C; font-size:12px; font-weight:700; transition:all 0.15s ease;">Rejected</div>
        </div>

        <!-- Case List Container -->
        <div id="cmCaseList" style="display:grid; grid-template-columns:1fr; gap:14px;">
          <div style="padding:30px; text-align:center; color:#64748B; background:#fff; border-radius:8px; border:1px solid #E2E8F0;">
            Loading Tax Approval Cases...
          </div>
        </div>
      </div>

      <!-- Single-Screen Case Review Modal -->
      <div id="cmReviewModal" style="display:none; position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(15,23,42,0.6); backdrop-filter:blur(8px); -webkit-backdrop-filter:blur(8px); z-index:1000; align-items:center; justify-content:center; padding:20px;">
        <div style="background:#fff; width:100%; max-width:640px; border-radius:12px; display:flex; flex-direction:column; overflow:hidden; box-shadow:0 25px 50px -12px rgba(0,0,0,0.35);">
          
          <!-- Header -->
          <div style="padding:16px 20px; background:#0F172A; color:#fff; display:flex; justify-content:space-between; align-items:center;">
            <div>
              <span id="cmModalCaseId" style="font-family:var(--font-mono); font-size:12px; font-weight:700; color:#38BDF8;">CASE-00000000</span>
              <h3 id="cmModalTitle" style="font-size:15px; font-weight:700; margin-top:2px; color:#F8FAFC; letter-spacing:-0.01em;">GST Statutory Decision Review</h3>
            </div>
            <button id="cmCloseModalBtn" style="background:transparent; border:none; color:#94A3B8; font-size:22px; cursor:pointer; line-height:1;">&times;</button>
          </div>

          <div style="padding:20px; display:flex; flex-direction:column; gap:16px; overflow-y:auto; max-height:80vh;">
            
            <!-- Metadata Summary Strip -->
            <div style="display:flex; justify-content:space-between; align-items:center; padding:10px 14px; background:#F8FAFC; border:1px solid #E2E8F0; border-radius:8px; font-size:12px;">
              <div><strong>Invoice:</strong> <span id="cmModalInvoice" style="font-family:var(--font-mono); font-weight:700; color:#0F172A;">-</span></div>
              <div><strong>Exposure:</strong> <span id="cmModalExposure" style="font-weight:700; color:var(--rose-600); font-family:var(--font-mono);">₹0.00</span></div>
              <div><strong>Status:</strong> <span id="cmModalStatus" style="font-weight:700; color:#D97706;">REVIEW_REQUIRED</span></div>
            </div>

            <!-- Single High-Visibility Reason Box -->
            <div style="border:1px solid #FCA5A5; background:#FEF2F2; border-radius:8px; padding:14px 16px;">
              <div style="display:flex; align-items:center; gap:6px; font-size:11.5px; font-weight:800; color:#991B1B; text-transform:uppercase; letter-spacing:0.5px; margin-bottom:6px;">
                <span>Gate Failure / Statutory Issue Reason</span>
              </div>
              <div id="cmModalIssueText" style="font-size:13px; color:#7F1D1D; font-weight:600; line-height:1.45;">
                Loading gate failure rationale...
              </div>
            </div>

            <!-- Decision & Comment Section -->
            <div style="border:1px solid #E2E8F0; border-radius:8px; padding:16px; background:#FAFAFA; display:flex; flex-direction:column; gap:14px;">
              
              <div style="display:grid; grid-template-columns:1fr 1fr; gap:10px;">
                <div>
                  <label style="display:block; font-size:11px; font-weight:700; color:#334155; margin-bottom:4px;">Reviewer Designation *</label>
                  <select id="cmReviewerInput" style="width:100%; padding:8px 10px; border:1px solid #CBD5E1; border-radius:6px; font-size:12px; background:#fff; font-weight:600; color:#0F172A;">
                    <option value="Senior Tax Auditor" data-role="Tax Auditor">Senior Tax Auditor</option>
                    <option value="Tax Manager" data-role="Tax Manager">Tax Manager</option>
                    <option value="Lead GST Controller" data-role="GST Controller">Lead GST Controller</option>
                    <option value="Tax Governance Director" data-role="Governance Director">Tax Governance Director</option>
                    <option value="Chief Financial Officer (CFO)" data-role="CFO">Chief Financial Officer (CFO)</option>
                  </select>
                </div>
                <div>
                  <label style="display:block; font-size:11px; font-weight:700; color:#334155; margin-bottom:4px;">Approval Tier / Role *</label>
                  <select id="cmRoleInput" style="width:100%; padding:8px 10px; border:1px solid #CBD5E1; border-radius:6px; font-size:12px; background:#fff; font-weight:600; color:#0F172A;">
                    <option value="Tax Auditor">L1 — Tax Auditor</option>
                    <option value="Tax Manager">L2 — Tax Manager</option>
                    <option value="GST Controller">L3 — GST Controller</option>
                    <option value="Governance Director">L4 — Governance Director</option>
                    <option value="CFO">L5 — Executive Officer (CFO)</option>
                  </select>
                </div>
              </div>

              <div>
                <label style="display:block; font-size:11px; font-weight:700; color:#334155; margin-bottom:6px;">Tax Action &amp; Filing Authorization *</label>
                <div style="display:flex; gap:12px;">
                  <button type="button" id="cmBtnApprove" class="cm-decision-btn" data-dec="APPROVE" style="flex:1; padding:10px; border:2px solid #10B981; background:#ECFDF5; color:#047857; font-weight:800; font-size:12px; border-radius:6px; cursor:pointer;">
                    Authorize for GSTR Filing
                  </button>
                  <button type="button" id="cmBtnReject" class="cm-decision-btn" data-dec="REJECT" style="flex:1; padding:10px; border:1px solid #CBD5E1; background:#fff; color:#334155; font-weight:800; font-size:12px; border-radius:6px; cursor:pointer;">
                    Hold / Block from Filing
                  </button>
                </div>
              </div>

              <div>
                <label style="display:block; font-size:11px; font-weight:700; color:#334155; margin-bottom:4px;">Remarks / Reason *</label>
                <textarea id="cmCommentInput" rows="2" placeholder="Enter notes or justification for your decision..." style="width:100%; padding:8px 10px; border:1px solid #CBD5E1; border-radius:6px; font-size:12px; font-family:sans-serif; resize:vertical;"></textarea>
              </div>

              <button id="cmSubmitReviewBtn" class="btn-command-run" style="width:100%; padding:11px; font-size:13px; font-weight:700; cursor:pointer;">
                Submit Tax Decision
              </button>

            </div>

          </div>

        </div>
      </div>
    `;

    this.bindEvents();
    this.fetchCases();
  },

  bindEvents: function() {
    const self = this;
    document.getElementById('cmRefreshBtn')?.addEventListener('click', () => self.fetchCases());

    document.querySelectorAll('.cm-chip').forEach(chip => {
      chip.addEventListener('click', () => {
        document.querySelectorAll('.cm-chip').forEach(c => {
          c.style.background = '#fff';
          c.style.color = '#334155';
          c.classList.remove('on');
        });
        chip.classList.add('on');
        chip.style.background = '#1E293B';
        chip.style.color = '#fff';
        self.activeFilter = chip.dataset.status;
        self.renderCaseList();
      });
    });

    document.getElementById('cmCloseModalBtn')?.addEventListener('click', () => {
      document.getElementById('cmReviewModal').style.display = 'none';
    });

    document.getElementById('cmReviewerInput')?.addEventListener('change', (e) => {
      const selectedOpt = e.target.options[e.target.selectedIndex];
      const role = selectedOpt.getAttribute('data-role');
      if (role) {
        const roleSelect = document.getElementById('cmRoleInput');
        if (roleSelect) roleSelect.value = role;
      }
    });

    this.selectedDecision = 'APPROVE';
    const approveBtn = document.getElementById('cmBtnApprove');
    const rejectBtn = document.getElementById('cmBtnReject');

    if (approveBtn && rejectBtn) {
      approveBtn.addEventListener('click', () => {
        self.selectedDecision = 'APPROVE';
        approveBtn.style.background = '#ECFDF5'; approveBtn.style.color = '#047857'; approveBtn.style.border = '2px solid #10B981';
        rejectBtn.style.background = '#fff'; rejectBtn.style.color = '#334155'; rejectBtn.style.border = '1px solid #CBD5E1';
      });

      rejectBtn.addEventListener('click', () => {
        self.selectedDecision = 'REJECT';
        rejectBtn.style.background = '#FEF2F2'; rejectBtn.style.color = '#B91C1C'; rejectBtn.style.border = '2px solid #EF4444';
        approveBtn.style.background = '#fff'; approveBtn.style.color = '#334155'; approveBtn.style.border = '1px solid #CBD5E1';
      });
    }

    document.getElementById('cmSubmitReviewBtn')?.addEventListener('click', async () => {
      const reviewer = (document.getElementById('cmReviewerInput').value || '').trim();
      const role = (document.getElementById('cmRoleInput').value || '').trim();
      const comment = (document.getElementById('cmCommentInput').value || '').trim();

      if (!reviewer) { alert('Reviewer identity is mandatory.'); return; }
      if (!comment) { alert('Review comment is mandatory.'); return; }

      const confirmMsg = `Confirm Human Decision: ${self.selectedDecision} for Case ${self.selectedCaseId}?`;
      if (!confirm(confirmMsg)) return;

      const btn = document.getElementById('cmSubmitReviewBtn');
      btn.disabled = true; btn.textContent = 'Submitting Decision...';

      try {
        const authKey = sessionStorage.getItem('uc15_api_key');
        const headers = { 'Content-Type': 'application/json' };
        if (authKey) headers['X-API-Key'] = authKey;
        const resp = await fetch(`/api/cases/${self.selectedCaseId}/review`, {
          method: 'POST',
          headers: headers,
          body: JSON.stringify({
            reviewer: reviewer,
            reviewer_role: role,
            decision: self.selectedDecision,
            comment: comment
          })
        });

        if (!resp.ok) {
          const err = await resp.json();
          alert(`Review failed: ${err.detail || 'Invalid transition'}`);
          return;
        }

        alert('Human decision submitted successfully!');
        document.getElementById('cmReviewModal').style.display = 'none';
        self.fetchCases();
      } catch (e) {
        alert('Could not submit review decision to server.');
      } finally {
        btn.disabled = false; btn.textContent = 'Submit Human Decision';
      }
    });
  },

  fetchCases: async function() {
    try {
      const authKey = sessionStorage.getItem('uc15_api_key');
      const headers = authKey ? { 'X-API-Key': authKey } : {};
      const r = await fetch('/api/cases', { headers });
      if (r.ok) {
        this.cases = await r.json();
        this.updateStats();
        this.renderCaseList();
      } else {
        const listEl = document.getElementById('cmCaseList');
        listEl.innerHTML = `
          <div style="padding:40px; text-align:center; color:#EF4444; background:#fff; border-radius:8px; border:1px solid #FCA5A5;">
            Failed to load cases (${r.status} ${r.statusText}). Please check backend status.
          </div>`;
      }
    } catch(e) {
      console.error('Error fetching cases:', e);
      const listEl = document.getElementById('cmCaseList');
      listEl.innerHTML = `
        <div style="padding:40px; text-align:center; color:#EF4444; background:#fff; border-radius:8px; border:1px solid #FCA5A5;">
          Could not connect to server. Please try refreshing.
        </div>`;
    }
  },

  isApproved: function(c) {
    return c.status === 'APPROVED' || c.status === 'READY_FOR_RESOLUTION' || (c.decisions && c.decisions.length > 0 && c.decisions[c.decisions.length - 1].decision === 'APPROVE');
  },

  isRejected: function(c) {
    return c.status === 'REJECTED' || (c.decisions && c.decisions.length > 0 && c.decisions[c.decisions.length - 1].decision === 'REJECT');
  },

  isBlocked: function(c) {
    if (this.isApproved(c) || this.isRejected(c)) return false;
    if (c.metadata && c.metadata.compliance_status === 'NON_COMPLIANT') return true;
    if (c.title && (c.title.includes('BLOCKED') || c.title.includes('NON_COMPLIANT'))) return true;
    if (c.priority === 'P1' || c.risk_level === 'CRITICAL') return true;
    return false;
  },

  isNeedsReview: function(c) {
    if (this.isApproved(c) || this.isRejected(c)) return false;
    if (this.isBlocked(c)) return false;
    return true;
  },

  updateStats: function() {
    const total = this.cases.length;
    const blocked = this.cases.filter(c => this.isBlocked(c)).length;
    const needsReview = this.cases.filter(c => this.isNeedsReview(c)).length;
    const approved = this.cases.filter(c => this.isApproved(c)).length;
    const rejected = this.cases.filter(c => this.isRejected(c)).length;

    const elTotal = document.getElementById('cmStatTotal');
    const elBlocked = document.getElementById('cmStatBlocked');
    const elReview = document.getElementById('cmStatReview');
    const elApproved = document.getElementById('cmStatApproved');
    const elRejected = document.getElementById('cmStatRejected');

    if (elTotal) elTotal.textContent = total;
    if (elBlocked) elBlocked.textContent = blocked;
    if (elReview) elReview.textContent = needsReview;
    if (elApproved) elApproved.textContent = approved;
    if (elRejected) elRejected.textContent = rejected;
  },

  getFilteredCases: function() {
    if (this.activeFilter === 'ALL') return this.cases;
    if (this.activeFilter === 'BLOCKED') {
      return this.cases.filter(c => this.isBlocked(c));
    }
    if (this.activeFilter === 'NEEDS_REVIEW') {
      return this.cases.filter(c => this.isNeedsReview(c));
    }
    if (this.activeFilter === 'APPROVED') {
      return this.cases.filter(c => this.isApproved(c));
    }
    if (this.activeFilter === 'REJECTED') {
      return this.cases.filter(c => this.isRejected(c));
    }
    return this.cases.filter(c => c.status === this.activeFilter);
  },

  renderCaseList: function() {
    const listEl = document.getElementById('cmCaseList');
    const filtered = this.getFilteredCases();

    if (!filtered || filtered.length === 0) {
      listEl.innerHTML = `
        <div style="padding:40px; text-align:center; color:#64748B; background:#fff; border-radius:8px; border:1px solid #E2E8F0;">
          No investigation cases found for filter '${this.activeFilter}'.
        </div>`;
      return;
    }

    listEl.innerHTML = filtered.map(c => {
      const isApp = this.isApproved(c);
      const isRej = this.isRejected(c);
      const isBlocked = this.isBlocked(c);

      const statusBadgeBg = isApp ? '#ECFDF5' : isRej ? '#FEF2F2' : isBlocked ? '#FEF2F2' : '#FFFBEB';
      const statusBadgeFg = isApp ? '#047857' : isRej ? '#B91C1C' : isBlocked ? '#991B1B' : '#B45309';
      const statusLabel = isApp ? 'AUTHORIZED FOR FILING' : isRej ? 'HELD / BLOCKED FROM FILING' : isBlocked ? 'BLOCKED (HARD HOLD)' : 'NEEDS REVIEW';



      // Extract failed gate details preview
      let gateSnippet = '';
      if (c.metadata && c.metadata.failed_gate_details && c.metadata.failed_gate_details.length > 0) {
        gateSnippet = c.metadata.failed_gate_details[0];
      } else if (c.description) {
        gateSnippet = c.description;
      }

      let decisionSnippet = '';
      if (c.decisions && c.decisions.length > 0) {
        const lastDec = c.decisions[c.decisions.length - 1];
        const isDecApp = lastDec.decision === 'APPROVE';
        const decBg = isDecApp ? '#F0FDF4' : '#FEF2F2';
        const decBorder = isDecApp ? '#BBF7D0' : '#FECDD3';
        const decFg = isDecApp ? '#166534' : '#991B1B';
        const decTag = isDecApp ? 'Authorized for Filing' : 'Blocked from Filing';
        decisionSnippet = `<div style="margin-top:8px; padding:8px 12px; background:${decBg}; border:1px solid ${decBorder}; border-radius:6px; font-size:11.5px; color:${decFg}; font-weight:500; line-height:1.4;">
          <strong>${decTag}</strong> by <strong>${lastDec.reviewer || 'Tax Reviewer'}</strong> (${lastDec.reviewer_role || 'Tax Auditor'}): &ldquo;${lastDec.comment}&rdquo;
        </div>`;
      }

      return `
        <div style="background:#fff; border:1px solid #E2E8F0; border-left:4px solid ${statusBadgeFg}; border-radius:10px; padding:18px 22px; display:flex; justify-content:space-between; align-items:center; box-shadow:var(--shadow-xs); transition:all 0.15s ease;">
          <div style="flex:1; padding-right:20px;">
            <div style="display:flex; align-items:center; gap:8px; flex-wrap:wrap;">
              <span style="font-family:var(--font-mono); font-size:12px; font-weight:700; color:var(--blue-600);">${c.case_id}</span>
              <span style="padding:3px 10px; border-radius:12px; font-size:11px; font-weight:800; background:${statusBadgeBg}; color:${statusBadgeFg};">${statusLabel}</span>
              <span style="padding:2px 8px; border-radius:12px; font-size:10.5px; font-weight:700; background:#F1F5F9; color:#334155;">Priority: ${c.priority}</span>
              <span style="padding:2px 8px; border-radius:12px; font-size:10.5px; font-weight:700; background:#FEF2F2; color:#991B1B;">Risk: ${c.risk_level}</span>
            </div>
            <h4 style="font-size:14.5px; font-weight:700; color:#0F172A; margin-top:6px; letter-spacing:-0.01em;">${c.title}</h4>
            <p style="font-size:12px; color:#64748B; margin-top:2px;">Invoice: <strong style="color:#0F172A; font-family:var(--font-mono);">${c.invoice_id || 'N/A'}</strong> &middot; Exposure: <strong style="color:var(--rose-600); font-family:var(--font-mono);">₹${c.financial_exposure ? c.financial_exposure.toLocaleString() : '0.00'}</strong> &middot; Assignee: <span style="color:#0F172A; font-weight:600;">${c.assigned_to || 'Unassigned'}</span></p>
            ${gateSnippet ? `<div style="margin-top:8px; padding:8px 12px; background:#F8FAFC; border:1px solid #E2E8F0; border-radius:6px; font-size:11.5px; color:#334155; font-weight:500; line-height:1.4;">${gateSnippet}</div>` : ''}
            ${decisionSnippet}
          </div>

          <div>
            <button class="open-case-btn btn-inspect" data-cid="${c.case_id}" style="padding:8px 16px; font-size:12px; font-weight:700; cursor:pointer;">
              <span>Review Case</span>
              <span class="inspect-arrow">&rarr;</span>
            </button>
          </div>
        </div>
      `;
    }).join('');

    const self = this;
    listEl.querySelectorAll('.open-case-btn').forEach(btn => {
      btn.addEventListener('click', () => self.openCaseModal(btn.dataset.cid));
    });
  },

  openCaseModal: async function(caseId) {
    this.selectedCaseId = caseId;
    try {
      const authKey = sessionStorage.getItem('uc15_api_key');
      const headers = authKey ? { 'X-API-Key': authKey } : {};
      const r = await fetch(`/api/cases/${caseId}`, { headers });
      if (!r.ok) return;
      const c = await r.json();

      document.getElementById('cmModalCaseId').textContent = c.case_id;
      document.getElementById('cmModalTitle').textContent = c.title;
      document.getElementById('cmModalStatus').textContent = c.status;
      document.getElementById('cmModalStatus').style.color = this.statusFg(c.status);
      document.getElementById('cmModalInvoice').textContent = c.invoice_id || 'N/A';
      document.getElementById('cmModalExposure').textContent = `INR ${c.financial_exposure ? c.financial_exposure.toLocaleString() : '0.00'}`;

      this.selectedDecision = 'APPROVE';
      const approveBtn = document.getElementById('cmBtnApprove');
      const rejectBtn = document.getElementById('cmBtnReject');
      if (approveBtn && rejectBtn) {
        approveBtn.style.background = '#ECFDF5'; approveBtn.style.color = '#047857'; approveBtn.style.border = '2px solid #10B981';
        rejectBtn.style.background = '#fff'; rejectBtn.style.color = '#334155'; rejectBtn.style.border = '1px solid #CBD5E1';
      }
      document.getElementById('cmCommentInput').value = '';

      let issueText = '';
      if (c.metadata && c.metadata.failed_gate_details && c.metadata.failed_gate_details.length > 0) {
        issueText = c.metadata.failed_gate_details.join(' | ');
      } else if (c.evidence_references && c.evidence_references.length > 0) {
        issueText = c.evidence_references.map(e => e.summary).join(' | ');
      }

      if (!issueText && c.invoice_id && window.gstApi && window.gstApi.getInvoiceDossier) {
        try {
          const invDossier = await window.gstApi.getInvoiceDossier(c.invoice_id);
          const gates = (invDossier.decision && invDossier.decision.gates) || [];
          const failedGates = gates.filter(g => g.status === 'FAIL' || g.status === 'NEEDS_REVIEW');
          if (failedGates.length > 0) {
            issueText = failedGates.map(g => `Gate ${g.gate_no} (${g.name}): ${g.detail || g.message}`).join(' | ');
          }
        } catch(err) {
          console.warn('Could not fetch invoice dossier:', err);
        }
      }

      if (!issueText) {
        issueText = c.description || c.recommendation || `Statutory review required for Invoice ${c.invoice_id || c.case_id}.`;
      }

      document.getElementById('cmModalIssueText').textContent = issueText;
      document.getElementById('cmReviewModal').style.display = 'flex';
    } catch(e) {
      alert('Could not load case details.');
    }
  },

  statusBg: function(s) {
    return {
      OPEN: '#F1F5F9', INVESTIGATING: '#EFF6FF', REVIEW_REQUIRED: '#FFFBEB',
      APPROVED: '#ECFDF5', REJECTED: '#FEF2F2', MORE_EVIDENCE_REQUIRED: '#EFF6FF',
      READY_FOR_RESOLUTION: '#F5F3FF'
    }[s] || '#F1F5F9';
  },

  statusFg: function(s) {
    return {
      OPEN: '#475569', INVESTIGATING: '#1D4ED8', REVIEW_REQUIRED: '#D97706',
      APPROVED: '#047857', REJECTED: '#B91C1C', MORE_EVIDENCE_REQUIRED: '#1D4ED8',
      READY_FOR_RESOLUTION: '#6D28D9'
    }[s] || '#475569';
  }
};


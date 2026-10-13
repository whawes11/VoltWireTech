// VoltWire Client Application - Enterprise Field Service & Subcontracting Engine

let currentUser = {
  id: 1,
  name: "OmniTech Managed IT",
  role: "business",
  email: "dispatch@omnitech.com"
};

let currentJobs = [];
let currentCategory = "";
let selectedJobForBid = null;

document.addEventListener("DOMContentLoaded", () => {
  initTabs();
  initCategoryPills();
  initSearch();
  initForms();
  updateUserUI();
  initDispatchMap();

  loadDashboardData();
});

// User State & Auth
function updateUserUI() {
  const roleTag = document.getElementById("userRoleTag");
  const nameDisplay = document.getElementById("userNameDisplay");

  roleTag.textContent = currentUser.role.toUpperCase();
  roleTag.style.background = currentUser.role === "business" ? "#ffffff" : "#27272a";
  roleTag.style.color = currentUser.role === "business" ? "#000000" : "#ffffff";
  nameDisplay.textContent = currentUser.name;
}

function openAuthModal() {
  openModal("authModal");
}

function loginAs(id, name, role, email) {
  currentUser = { id, name, role, email };
  updateUserUI();
  initDispatchMap();
  closeModal("authModal");
  alert(`Active profile switched to: ${name} (${role.toUpperCase()})`);
  loadDashboardData();
}

function toggleContractorPayoutFields() {
  const method = document.getElementById("conPayoutMethod").value;
  const ach = document.getElementById("conAchFields");
  const debit = document.getElementById("conDebitFields");

  if (method === "ach") {
    ach.style.display = "flex";
    debit.style.display = "none";
  } else {
    ach.style.display = "none";
    debit.style.display = "block";
  }
}

// Tab Navigation
function initTabs() {
  document.querySelectorAll(".nav-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      const tabId = btn.getAttribute("data-tab");
      switchTab(tabId);
    });
  });
}

function switchTab(tabId) {
  document.querySelectorAll(".nav-btn").forEach(btn => {
    btn.classList.toggle("active", btn.getAttribute("data-tab") === tabId);
  });
  document.querySelectorAll(".tab-view").forEach(view => {
    view.classList.toggle("active", view.id === tabId);
  });

  if (tabId === "jobs-tab") {
    loadJobs();
    if (dispatchMap) setTimeout(() => dispatchMap.invalidateSize(), 200);
  }
  if (tabId === "my-jobs-tab") loadMyJobs();
  if (tabId === "contractors-tab") loadContractors();
}

// Category Filtering
function initCategoryPills() {
  document.querySelectorAll("#categoryPills .pill").forEach(pill => {
    pill.addEventListener("click", () => {
      document.querySelectorAll("#categoryPills .pill").forEach(p => p.classList.remove("active"));
      pill.classList.add("active");
      currentCategory = pill.getAttribute("data-cat");
      loadJobs();
    });
  });
}

// Search
function initSearch() {
  const searchInput = document.getElementById("jobSearchInput");
  const searchBtn = document.getElementById("jobSearchBtn");

  searchBtn.addEventListener("click", () => loadJobs());
  searchInput.addEventListener("keypress", (e) => {
    if (e.key === "Enter") loadJobs();
  });
}

// Dashboard Data
function loadDashboardData() {
  loadStats();
  loadJobs();
  loadMyJobs();
}

async function loadStats() {
  try {
    const res = await fetch("/api/stats");
    const stats = await res.json();

    document.getElementById("statOpenJobs").textContent = stats.open_jobs;
    document.getElementById("statContractors").textContent = stats.contractors_count;
    document.getElementById("statTotalBids").textContent = stats.total_bids;
    document.getElementById("statPlatformFees").textContent = `$${stats.platform_earnings.toFixed(2)}`;
  } catch (err) {
    console.error("Failed to load stats", err);
  }
}

// Jobs Grid
async function loadJobs() {
  const grid = document.getElementById("jobsGrid");
  grid.innerHTML = '<div class="loading-state">Loading active work orders...</div>';

  const searchQuery = document.getElementById("jobSearchInput").value.trim();
  let url = "/api/jobs?status=published&";
  if (currentCategory) url += `category=${encodeURIComponent(currentCategory)}&`;
  if (searchQuery) url += `search=${encodeURIComponent(searchQuery)}&`;

  try {
    const res = await fetch(url);
    const data = await res.json();
    currentJobs = data.jobs;

    if (currentJobs.length === 0) {
      grid.innerHTML = '<div class="loading-state">No open work orders found. Post one in the Client Portal to begin!</div>';
      renderMapMarkers([]);
      return;
    }

    grid.innerHTML = currentJobs.map(job => renderJobCard(job)).join("");
    renderMapMarkers(currentJobs);
  } catch (err) {
    grid.innerHTML = '<div class="loading-state">Error loading work orders.</div>';
    console.error(err);
  }
}

function getCategoryClass(cat) {
  switch (cat) {
    case "CCTV & IP Surveillance": return "cat-cctv";
    case "Network Device Installation": return "cat-network";
    case "Structured Cabling": return "cat-cabling";
    case "Fiber Optics": return "cat-fiber";
    case "Access Control": return "cat-access";
    default: return "cat-cabling";
  }
}

function renderJobCard(job) {
  const catClass = getCategoryClass(job.category);
  const dropText = job.drop_count > 0 ? `⚡ ${job.drop_count} Devices/Drops` : "⚡ Commercial Installation";
  const deadlineText = job.deadline ? `📅 Target: ${job.deadline}` : "⚡ Immediate Dispatch";

  return `
    <div class="job-card">
      <div>
        <div class="job-header">
          <span class="category-tag ${catClass}">${escapeHtml(job.category)}</span>
          <h3 class="job-title">${escapeHtml(job.title)}</h3>
          <div class="job-company">🏢 ${escapeHtml(job.company_name)} &bull; 📍 ${escapeHtml(job.location)}</div>
        </div>

        <div class="job-meta-row">
          <div class="job-meta-item">${dropText}</div>
          <div class="job-meta-item">${deadlineText}</div>
        </div>

        <div class="job-budget">$${job.budget_min.toLocaleString()} - $${job.budget_max.toLocaleString()}</div>
        <p class="job-desc">${escapeHtml(job.description)}</p>
      </div>

      <div class="job-footer">
        <span class="bid-count-badge">🏷️ ${job.bid_count} Submitted Bid${job.bid_count === 1 ? '' : 's'}</span>
        <div class="card-actions">
          <button class="secondary-btn btn-sm" onclick="viewJobDetails(${job.id})">Review & Bids</button>
          <button class="primary-btn btn-sm" onclick="openBidModal(${job.id})">Bid on Job</button>
        </div>
      </div>
    </div>
  `;
}

// Work Order Detail & Bids Modal
async function viewJobDetails(jobId) {
  try {
    const res = await fetch(`/api/jobs/${jobId}`);
    const data = await res.json();
    const job = data.job;

    document.getElementById("modalJobTitle").textContent = job.title;

    let bidsHtml = "";
    if (job.bids && job.bids.length > 0) {
      bidsHtml = `
        <h4 style="margin: 1.5rem 0 0.75rem 0; color: #ffffff;">Submitted Proposals & Bids (${job.bids.length})</h4>
        <div style="display: flex; flex-direction: column; gap: 0.75rem;">
          ${job.bids.map(b => `
            <div style="background: #000000; border: 1px solid var(--border); border-radius: 8px; padding: 1.15rem;">
              <div style="display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 0.35rem;">
                <strong style="color: #ffffff; font-size: 1.05rem;">${escapeHtml(b.contractor_name)}</strong>
                <span style="font-family: 'JetBrains Mono', monospace; font-weight: 800; color: #ffffff; font-size: 1.25rem;">
                  $${b.amount.toLocaleString()}
                </span>
              </div>
              <div style="font-size: 0.8rem; color: #e4e4e7; background: #181818; border: 1px solid var(--border); padding: 0.25rem 0.6rem; border-radius: 4px; display: inline-block; margin-bottom: 0.6rem;">
                ⚡ Client Total: $${b.amount.toLocaleString()} &bull; 10% Platform Fee: $${(b.amount * 0.10).toFixed(2)} &bull; Net Contractor: $${(b.amount * 0.90).toFixed(2)}
              </div>
              
              ${b.counter_offer_amount > 0 ? `
                <div style="background: #181818; border: 1px solid #ffffff; padding: 0.6rem; border-radius: 6px; font-size: 0.85rem; color: #ffffff; margin-bottom: 0.6rem;">
                  🔄 <strong>Client Counter-Offer:</strong> $${b.counter_offer_amount.toLocaleString()} &bull; <em>"${escapeHtml(b.counter_offer_notes)}"</em>
                </div>
              ` : ''}

              <div style="font-size: 0.85rem; color: #a1a1aa; margin-bottom: 0.5rem;">
                Labor: $${b.labor_cost.toLocaleString()} &bull; Materials: $${b.material_cost.toLocaleString()} &bull; Est: ${b.estimated_days} Days
              </div>
              <p style="font-size: 0.88rem; color: #cbd5e1; line-height: 1.4; margin-bottom: 0.85rem;">${escapeHtml(b.proposal_notes)}</p>

              <div style="display: flex; gap: 0.5rem; flex-wrap: wrap;">
                ${currentUser.role === 'business' && (job.status === 'published' || job.status === 'negotiating') ? `
                  <button class="primary-btn btn-sm btn-success" onclick="assignContractor(${job.id}, ${b.id})">
                    ✓ Accept Bid & Assign
                  </button>
                  <button class="secondary-btn btn-sm btn-counter" onclick="openCounterModal(${job.id}, ${b.id}, ${b.amount})">
                    🔄 Send Counter-Offer
                  </button>
                ` : ''}

                ${currentUser.role === 'contractor' && b.status === 'countered' ? `
                  <button class="primary-btn btn-sm btn-success" onclick="acceptCounterOffer(${b.id})">
                    ✓ Accept Proposed $${b.counter_offer_amount} Offer
                  </button>
                ` : ''}
              </div>
            </div>
          `).join("")}
        </div>
      `;
    } else {
      bidsHtml = `
        <div style="background: #000000; border: 1px dashed var(--border); padding: 1.25rem; border-radius: 8px; text-align: center; margin-top: 1.25rem;">
          <p style="color: #71717a; font-size: 0.9rem;">No bids submitted yet for this project.</p>
        </div>
      `;
    }

    document.getElementById("modalJobBody").innerHTML = `
      <div style="margin-bottom: 1.25rem;">
        <div style="display: flex; gap: 0.5rem; margin-bottom: 0.75rem; align-items: center;">
          <span class="category-tag ${getCategoryClass(job.category)}">${escapeHtml(job.category)}</span>
          <span class="status-badge status-${job.status}">${job.status.toUpperCase()}</span>
          <span style="font-size: 0.85rem; color: #a1a1aa; font-weight: 600;">📍 ${escapeHtml(job.location)}</span>
        </div>
        <div style="font-size: 1.45rem; font-weight: 800; color: #ffffff; font-family: 'JetBrains Mono', monospace; margin-bottom: 0.75rem;">
          Target Budget: $${job.budget_min.toLocaleString()} - $${job.budget_max.toLocaleString()}
        </div>
        <div style="font-size: 0.9rem; color: #a1a1aa; margin-bottom: 0.75rem;">
          <strong>Posted By:</strong> ${escapeHtml(job.company_name)} ${job.drop_count ? `&bull; <strong>Device Count:</strong> ${job.drop_count}` : ""}
        </div>
        <h4>Scope of Work</h4>
        <p style="font-size: 0.92rem; color: #e4e4e7; line-height: 1.5; margin: 0.5rem 0 1rem 0;">${escapeHtml(job.description)}</p>

        ${job.requirements ? `
          <h4>Insurance & Certification Criteria</h4>
          <p style="font-size: 0.88rem; color: #ffffff; background: #181818; border-left: 3px solid #ffffff; padding: 0.75rem; border-radius: 4px; margin-top: 0.5rem;">
            ${escapeHtml(job.requirements)}
          </p>
        ` : ""}
      </div>

      <hr style="border: 0; border-top: 1px solid var(--border);">

      ${bidsHtml}

      <div style="margin-top: 1.5rem; display: flex; gap: 0.75rem;">
        ${job.status === 'published' ? `
          <button class="primary-btn" onclick="closeModal('jobDetailModal'); openBidModal(${job.id});">Submit a Bid</button>
        ` : ''}
        <button class="secondary-btn" onclick="closeModal('jobDetailModal')">Close</button>
      </div>
    `;

    openModal("jobDetailModal");
  } catch (err) {
    alert("Could not load job details.");
    console.error(err);
  }
}

// Bidding Modal
function openBidModal(jobId) {
  const job = currentJobs.find(j => j.id === jobId);
  if (!job) return;
  selectedJobForBid = job;

  document.getElementById("bidJobId").value = job.id;
  document.getElementById("bidJobHeader").innerHTML = `
    <div style="font-size: 0.85rem; color: #a1a1aa; font-weight: 600;">Work Order:</div>
    <div style="font-weight: 700; color: #ffffff; font-size: 1.05rem;">${escapeHtml(job.title)}</div>
    <div style="font-size: 0.85rem; color: #ffffff; font-weight: 700; font-family: 'JetBrains Mono', monospace;">
      Target: $${job.budget_min.toLocaleString()} - $${job.budget_max.toLocaleString()} (${job.drop_count || 'N/A'} Devices/Drops)
    </div>
  `;

  calculateBidFeeBreakdown();
  openModal("submitBidModal");
}

function calculateBidFeeBreakdown() {
  const amt = parseFloat(document.getElementById("bidAmount").value) || 0;
  const fee = amt * 0.10;
  const payout = amt - fee;

  document.getElementById("modalBidFee").textContent = `$${fee.toFixed(2)}`;
  document.getElementById("modalBidPayout").textContent = `$${payout.toFixed(2)}`;
}

// Counter-Offer Modal
function openCounterModal(jobId, bidId, currentAmount) {
  document.getElementById("counterJobId").value = jobId;
  document.getElementById("counterBidId").value = bidId;
  document.getElementById("counterAmount").value = Math.round(currentAmount * 0.92);
  document.getElementById("counterSummary").innerHTML = `
    <div style="font-size: 0.85rem; color: #a1a1aa;">Original Proposal: $${currentAmount.toLocaleString()}</div>
    <div style="font-size: 0.88rem; color: #ffffff; font-weight: 600;">Enter your proposed counter-offer budget and terms below:</div>
  `;
  closeModal("jobDetailModal");
  openModal("counterModal");
}

async function acceptCounterOffer(bidId) {
  if (!confirm("Accept client counter-offer? The project will be locked in and assigned to you under these agreed terms.")) return;

  try {
    const res = await fetch(`/api/bids/${bidId}/accept-counter`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({})
    });
    const data = await res.json();
    if (res.ok) {
      alert("✓ Counter-offer accepted! Work order assigned.");
      closeModal("jobDetailModal");
      loadDashboardData();
      switchTab("my-jobs-tab");
    } else {
      alert("Error: " + data.error);
    }
  } catch (err) {
    alert("Network error.");
  }
}

// Work Order Dispatch Operations
async function assignContractor(jobId, bidId) {
  if (!confirm("Accept this bid? The contractor will be assigned to this work order under the 10% platform fee terms.")) return;

  try {
    const res = await fetch(`/api/jobs/${jobId}/assign`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ bid_id: bidId })
    });
    const data = await res.json();
    if (res.ok) {
      alert(data.message);
      closeModal("jobDetailModal");
      loadDashboardData();
      switchTab("my-jobs-tab");
    } else {
      alert("Error: " + data.error);
    }
  } catch (err) {
    alert("Network error assigning contractor.");
  }
}

async function checkInTechnician(jobId) {
  try {
    const res = await fetch(`/api/jobs/${jobId}/check-in`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({})
    });
    const data = await res.json();
    if (res.ok) {
      alert("✓ On-Site Check-In Confirmed! Time recorded: " + data.check_in_time);
      loadMyJobs();
    }
  } catch (err) {
    alert("Check-in error.");
  }
}

async function completeWorkOrder(jobId) {
  const notes = prompt("Enter completion notes and verification reports:", "All devices installed, mounted, labeled, and verified operational with test reports.");
  if (!notes) return;

  try {
    const res = await fetch(`/api/jobs/${jobId}/complete`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ completion_notes: notes })
    });
    const data = await res.json();
    if (res.ok) {
      alert("✓ Deliverables submitted! Work order is now waiting for client sign-off and payout release.");
      loadMyJobs();
    }
  } catch (err) {
    alert("Completion error.");
  }
}

async function approveWorkOrder(jobId) {
  if (!confirm("Approve deliverables and release payout? 10% platform fee will be deducted and technician payout dispatched.")) return;

  try {
    const res = await fetch(`/api/jobs/${jobId}/approve`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({})
    });
    const data = await res.json();
    if (res.ok) {
      if (data.insurance_held) {
        alert("⚠️ WARNING: " + data.message);
      } else {
        alert("✓ " + data.message);
      }
      loadDashboardData();
      loadMyJobs();
      openReviewModal(jobId, 2);
    }
  } catch (err) {
    alert("Approval error.");
  }
}

// "My Work Orders" View
async function loadMyJobs() {
  const container = document.getElementById("myJobsContainer");
  container.innerHTML = '<div class="loading-state">Loading your work order pipeline...</div>';

  try {
    const res = await fetch(`/api/my-jobs?user_id=${currentUser.id}&role=${currentUser.role}`);
    const data = await res.json();
    const jobs = data.jobs;

    if (jobs.length === 0) {
      container.innerHTML = `
        <div style="background: var(--card-bg); padding: 2.5rem; border-radius: 12px; border: 1px dashed var(--border); text-align: center;">
          <p style="color: #71717a;">No active work orders in your dispatch pipeline. ${currentUser.role === 'business' ? 'Post a new job in the Client Portal to start!' : 'Browse and bid on open jobs!'}</p>
        </div>
      `;
      return;
    }

    container.innerHTML = jobs.map(j => {
      let actionButtons = "";
      if (currentUser.role === "contractor") {
        if (j.status === "assigned") {
          actionButtons = `<button class="primary-btn btn-sm" onclick="checkInTechnician(${j.id})">📍 Check-In On-Site</button>`;
        } else if (j.status === "in_progress") {
          actionButtons = `<button class="primary-btn btn-sm btn-success" onclick="completeWorkOrder(${j.id})">✓ Submit Deliverables</button>`;
        } else if (j.my_bid_status === "countered") {
          actionButtons = `<button class="primary-btn btn-sm btn-counter" onclick="acceptCounterOffer(${j.my_bid_id})">Accept Counter-Offer ($${j.counter_offer_amount})</button>`;
        }
      } else {
        if (j.status === "completed") {
          actionButtons = `<button class="primary-btn btn-sm btn-success" onclick="approveWorkOrder(${j.id})">💰 Approve & Release Payout</button>`;
        } else if (j.status === "approved") {
          actionButtons = `<button class="secondary-btn btn-sm" onclick="openReviewModal(${j.id}, ${j.assigned_contractor_id || 2})">⭐ Review Tech</button>`;
        }
      }

      return `
        <div class="pipeline-card">
          <div style="flex: 2; min-width: 280px;">
            <div style="display: flex; gap: 0.5rem; align-items: center; margin-bottom: 0.4rem;">
              <span class="status-badge status-${j.status}">${j.status.replace('_', ' ').toUpperCase()}</span>
              <span class="category-tag ${getCategoryClass(j.category)}">${escapeHtml(j.category)}</span>
            </div>
            <h3 style="font-size: 1.15rem; color: #ffffff; margin-bottom: 0.25rem;">${escapeHtml(j.title)}</h3>
            <div style="font-size: 0.85rem; color: #a1a1aa;">
              📍 ${escapeHtml(j.location)} &bull; Devices: ${j.drop_count || 'N/A'} &bull; Assigned: <strong style="color: #ffffff;">${escapeHtml(j.assigned_contractor_name || 'Open for Bids')}</strong>
            </div>

            ${j.insurance_verified ? `
              <div style="margin-top: 0.4rem;">
                <span class="insurance-verified-tag">🛡️ $1M+ General Liability Policy Verified</span>
              </div>
            ` : (j.assigned_contractor_id ? `
              <div style="margin-top: 0.4rem;">
                <span style="color: #ef4444; font-size: 0.78rem; font-weight: 700;">⚠️ Insurance Verification Pending</span>
              </div>
            ` : '')}

            ${j.completion_notes ? `
              <div style="background: #000000; border: 1px solid var(--border); padding: 0.6rem 0.85rem; border-radius: 6px; font-size: 0.85rem; margin-top: 0.6rem; color: #e4e4e7;">
                📝 <strong>Tech Deliverables:</strong> ${escapeHtml(j.completion_notes)}
              </div>
            ` : ''}
          </div>

          <div style="flex: 1; min-width: 180px; text-align: right;">
            <div style="font-size: 1.35rem; font-weight: 800; font-family: 'JetBrains Mono', monospace; color: #ffffff;">
              $${(j.agreed_amount || j.budget_max).toLocaleString()}
            </div>
            <div style="font-size: 0.78rem; color: #a1a1aa;">
              10% Fee: $${((j.agreed_amount || j.budget_max) * 0.10).toFixed(2)} | Net: $${((j.agreed_amount || j.budget_max) * 0.90).toFixed(2)}
            </div>
            <div style="margin-top: 0.85rem; display: flex; justify-content: flex-end; gap: 0.5rem; flex-wrap: wrap;">
              <button class="secondary-btn btn-sm" onclick="viewJobDetails(${j.id})">Details</button>
              ${actionButtons}
            </div>
          </div>
        </div>
      `;
    }).join("");
  } catch (err) {
    container.innerHTML = '<div class="loading-state">Error loading work orders.</div>';
    console.error(err);
  }
}

// Review Modal
function openReviewModal(jobId, contractorId) {
  document.getElementById("revJobId").value = jobId;
  document.getElementById("revContractorId").value = contractorId;
  openModal("reviewModal");
}

// Contractor Directory with Scoring & Compliance
async function loadContractors() {
  const grid = document.getElementById("contractorsGrid");
  grid.innerHTML = '<div class="loading-state">Loading verified technicians...</div>';

  try {
    const res = await fetch("/api/contractors");
    const data = await res.json();
    const contractors = data.contractors;

    grid.innerHTML = contractors.map(c => `
      <div class="contractor-card">
        <div class="contractor-head">
          <div>
            <h3 class="contractor-name">${escapeHtml(c.name)}</h3>
            <div style="font-size: 0.85rem; color: #a1a1aa;">👤 ${escapeHtml(c.contact_person)} &bull; 📍 ${escapeHtml(c.location)}</div>
          </div>
          <span style="font-weight: 800; color: #ffffff; font-size: 1.15rem; font-family: 'JetBrains Mono', monospace;">$${c.hourly_rate}/hr</span>
        </div>

        <div class="scores-strip">
          <div>
            <div class="score-item-val">${c.quality_score.toFixed(1)}</div>
            <div class="score-item-lbl">Quality Score</div>
          </div>
          <div>
            <div class="score-item-val">${c.on_time_rate.toFixed(0)}%</div>
            <div class="score-item-lbl">On-Time Arrival</div>
          </div>
          <div>
            <div class="score-item-val">⭐ ${c.rating.toFixed(2)}</div>
            <div class="score-item-lbl">Client Rating</div>
          </div>
        </div>

        <div class="badge-pill-list">
          <span class="insurance-verified-tag">🛡️ $1M+ GL Insured (${escapeHtml(c.insurance_carrier || 'Active')})</span>
          ${c.is_pro_member ? '<span class="badge-pill" style="border-color: #ffffff; color: #ffffff; font-weight: 700;">⚡ Pro Member (0-Day Payout)</span>' : ''}
          <span class="badge-pill">🏆 ${c.completed_jobs} Jobs Completed</span>
        </div>

        <div style="font-size: 0.88rem; color: #e4e4e7; margin-bottom: 0.5rem;">
          <strong>Disciplines:</strong> ${escapeHtml(c.specialties)}
        </div>

        ${c.certifications ? `
          <div style="font-size: 0.82rem; background: #181818; border-left: 3px solid #ffffff; padding: 0.5rem 0.75rem; border-radius: 0 4px 4px 0; margin-bottom: 0.75rem;">
            <strong>Certifications:</strong> ${escapeHtml(c.certifications)}
          </div>
        ` : ""}

        <div style="margin-top: 0.85rem; display: flex; justify-content: space-between; align-items: center; border-top: 1px solid var(--border); padding-top: 0.75rem; font-size: 0.82rem; color: #a1a1aa;">
          <span>Payout: <strong>${c.payout_method === 'debit' ? 'Instant Debit Card' : 'Standard Bank ACH'}</strong></span>
          <a href="mailto:${encodeURIComponent(c.email)}" class="secondary-btn btn-sm">Contact Tech</a>
        </div>
      </div>
    `).join("");
  } catch (err) {
    grid.innerHTML = '<div class="loading-state">Error loading technicians.</div>';
    console.error(err);
  }
}

// Form Handlers
function initForms() {
  // 1. Dedicated Client Sign-Up Form
  document.getElementById("clientSignUpForm").addEventListener("submit", async (e) => {
    e.preventDefault();

    const payload = {
      company_name: document.getElementById("cliCompany").value,
      contact_name: document.getElementById("cliContact").value,
      email: document.getElementById("cliEmail").value,
      phone: document.getElementById("cliPhone").value,
      website: document.getElementById("cliWebsite").value,
      industry_type: document.getElementById("cliIndustry").value,
      billing_method: document.getElementById("cliBilling").value,
      monthly_volume: document.getElementById("cliVolume").value,
      location: document.getElementById("cliLocation").value,
      password: document.getElementById("cliPassword").value
    };

    try {
      const res = await fetch("/api/auth/register-client", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      if (res.ok) {
        alert("✓ " + data.message);
        currentUser = {
          id: data.user.id,
          name: data.user.company_name,
          role: "business",
          email: data.user.email
        };
        updateUserUI();
  initDispatchMap();
        document.getElementById("clientSignUpForm").reset();
        loadDashboardData();
        switchTab("jobs-tab");
      } else {
        alert("Client Registration Error: " + (data.error || "Failed to register."));
      }
    } catch (err) {
      alert("Network error creating client account.");
    }
  });

  // 2. Dedicated Contractor Sign-Up Form
  document.getElementById("contractorSignUpForm").addEventListener("submit", async (e) => {
    e.preventDefault();

    const payload = {
      name: document.getElementById("conName").value,
      contact_person: document.getElementById("conContact").value,
      email: document.getElementById("conEmail").value,
      phone: document.getElementById("conPhone").value,
      legal_entity_type: document.getElementById("conEntity").value,
      tax_id_type: document.getElementById("conTaxType").value,
      tax_id: document.getElementById("conTaxId").value,
      license: document.getElementById("conLicense").value,
      hourly_rate: parseFloat(document.getElementById("conRate").value || 75),
      insurance_carrier: document.getElementById("conInsCarrier").value,
      insurance_policy_number: document.getElementById("conInsPolicy").value,
      insurance_coverage_amount: parseFloat(document.getElementById("conInsAmount").value),
      insurance_expiration: document.getElementById("conInsExp").value,
      payout_method: document.getElementById("conPayoutMethod").value,
      bank_name: document.getElementById("conBankName").value,
      bank_routing: document.getElementById("conRouting").value,
      bank_account: document.getElementById("conAccount").value,
      debit_card: document.getElementById("conDebit").value,
      pro_membership: document.getElementById("conProMember").checked,
      password: document.getElementById("conPassword").value
    };

    try {
      const res = await fetch("/api/auth/register-contractor", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      if (res.ok) {
        alert("✓ " + data.message);
        currentUser = {
          id: data.user.id,
          name: data.user.company_name || data.user.full_name,
          role: "contractor",
          email: data.user.email
        };
        updateUserUI();
  initDispatchMap();
        document.getElementById("contractorSignUpForm").reset();
        loadContractors();
        loadDashboardData();
        switchTab("jobs-tab");
      } else {
        alert("Contractor Registration Error: " + (data.error || "Failed to register."));
      }
    } catch (err) {
      alert("Network error creating contractor account.");
    }
  });

  // 3. Post Job Form
  document.getElementById("createJobForm").addEventListener("submit", async (e) => {
    e.preventDefault();

    const payload = {
      client_id: currentUser.id,
      title: document.getElementById("jobTitle").value,
      category: document.getElementById("jobCategory").value,
      company_name: document.getElementById("jobCompany").value,
      location: document.getElementById("jobLocation").value,
      drop_count: parseInt(document.getElementById("jobDropCount").value || 0),
      budget_min: parseFloat(document.getElementById("budgetMin").value),
      budget_max: parseFloat(document.getElementById("budgetMax").value),
      description: document.getElementById("jobDescription").value,
      requirements: document.getElementById("jobRequirements").value
    };

    try {
      const res = await fetch("/api/jobs", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      const data = await res.json();

      if (res.ok) {
        alert("✓ Work Order published successfully to the marketplace!");
        document.getElementById("createJobForm").reset();
        loadDashboardData();
        switchTab("jobs-tab");
      } else {
        alert("Error: " + (data.error || "Failed to post job"));
      }
    } catch (err) {
      alert("Network error publishing job.");
    }
  });

  // 4. Submit Bid
  document.getElementById("submitBidForm").addEventListener("submit", async (e) => {
    e.preventDefault();

    const payload = {
      job_id: document.getElementById("bidJobId").value,
      contractor_id: currentUser.id,
      contractor_name: currentUser.name,
      contractor_email: currentUser.email,
      contractor_phone: "(404) 555-0142",
      amount: parseFloat(document.getElementById("bidAmount").value),
      labor_cost: parseFloat(document.getElementById("bidLaborCost").value || 0),
      material_cost: parseFloat(document.getElementById("bidMaterialCost").value || 0),
      estimated_days: parseInt(document.getElementById("bidEstimatedDays").value || 1),
      proposal_notes: document.getElementById("bidProposalNotes").value
    };

    try {
      const res = await fetch("/api/bids", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      const data = await res.json();

      if (res.ok) {
        alert(data.message);
        closeModal("submitBidModal");
        document.getElementById("submitBidForm").reset();
        loadDashboardData();
        switchTab("my-jobs-tab");
      } else {
        alert("Error: " + (data.error || "Failed to submit bid"));
      }
    } catch (err) {
      alert("Network error submitting bid.");
    }
  });

  // 5. Counter Offer Form
  document.getElementById("counterOfferForm").addEventListener("submit", async (e) => {
    e.preventDefault();

    const payload = {
      bid_id: document.getElementById("counterBidId").value,
      counter_amount: parseFloat(document.getElementById("counterAmount").value),
      counter_notes: document.getElementById("counterNotes").value
    };
    const jobId = document.getElementById("counterJobId").value;

    try {
      const res = await fetch(`/api/jobs/${jobId}/counter`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      if (res.ok) {
        alert("✓ " + data.message);
        closeModal("counterModal");
        loadDashboardData();
        switchTab("my-jobs-tab");
      }
    } catch (err) {
      alert("Counter-offer submission error.");
    }
  });

  // 6. Review & Score Form
  document.getElementById("reviewForm").addEventListener("submit", async (e) => {
    e.preventDefault();

    const payload = {
      job_id: document.getElementById("revJobId").value,
      contractor_id: document.getElementById("revContractorId").value,
      client_id: currentUser.id,
      arrived_on_time: parseInt(document.getElementById("revOnTime").value),
      rating: parseFloat(document.getElementById("revRating").value),
      review_text: document.getElementById("revText").value
    };

    try {
      const res = await fetch("/api/reviews", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      if (res.ok) {
        alert(`✓ Score updated! Rating: ${data.rating} | On-Time Rate: ${data.on_time_rate}% | Quality Score: ${data.quality_score}`);
        closeModal("reviewModal");
        document.getElementById("reviewForm").reset();
        loadContractors();
        loadMyJobs();
      }
    } catch (err) {
      alert("Review submission error.");
    }
  });
}


// ==============================================================================
// GEORGIA INTERACTIVE DISPATCH RADAR MAP (LEAFLET MONOCHROME INTEGRATION)
// ==============================================================================
const GEORGIA_COORDINATES = {
  "Atlanta, GA": [33.7490, -84.3880],
  "Midtown Atlanta, GA": [33.7845, -84.3845],
  "Downtown Atlanta, GA": [33.7537, -84.3863],
  "Buckhead Atlanta, GA": [33.8384, -84.3799],
  "Alpharetta, GA": [34.0754, -84.2941],
  "Duluth, GA": [34.0029, -84.1446],
  "Marietta, GA": [33.9526, -84.5499],
  "Savannah, GA": [32.0809, -81.0912],
  "Macon, GA": [32.8407, -83.6324],
  "Augusta, GA": [33.4735, -82.0105],
  "Columbus, GA": [32.4610, -84.9877],
  "Athens, GA": [33.9519, -83.3576],
  "Sandy Springs, GA": [33.9304, -84.3733],
  "Roswell, GA": [34.0232, -84.3616],
  "Norcross, GA": [33.9412, -84.2135],
  "Kennesaw, GA": [34.0234, -84.6155],
  "Lawrenceville, GA": [33.9562, -83.9880]
};

const CATEGORY_ICONS = {
  "CCTV & IP Surveillance": "📹",
  "Network Device Installation": "🖧",
  "Structured Cabling": "🔌",
  "Fiber Optics": "💡",
  "Access Control": "🔐"
};

let dispatchMap = null;
let mapMarkers = [];
let currentJobViewMode = "list";

function initDispatchMap() {
  const mapEl = document.getElementById("dispatchMap");
  if (!mapEl) return;

  if (typeof L === "undefined") {
    console.warn("Leaflet library not loaded yet.");
    return;
  }

  if (dispatchMap) return;

  try {
    dispatchMap = L.map("dispatchMap", {
      zoomControl: true,
      scrollWheelZoom: false
    }).setView([33.75, -84.38], 8);

    L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", {
      attribution: '&copy; OpenStreetMap &copy; CARTO',
      subdomains: "abcd",
      maxZoom: 19
    }).addTo(dispatchMap);

    if (currentJobs && currentJobs.length > 0) {
      renderMapMarkers(currentJobs);
    }
  } catch (err) {
    console.error("Map initialization error:", err);
  }
}

function renderMapMarkers(jobs) {
  if (!dispatchMap) {
    initDispatchMap();
    if (!dispatchMap) return;
  }

  mapMarkers.forEach(m => dispatchMap.removeLayer(m));
  mapMarkers = [];

  const bounds = [];
  const countEl = document.getElementById("mapPinCount");
  let plottedCount = 0;

  jobs.forEach(job => {
    let coords = GEORGIA_COORDINATES[job.location];
    if (!coords) {
      coords = [33.7490 + ((job.id % 5) * 0.05), -84.3880 + (((job.id * 3) % 5) * 0.04)];
    }

    const iconHtml = `<div class="custom-dispatch-pin" title="${escapeHtml(job.title)}">${CATEGORY_ICONS[job.category] || "⚡"}</div>`;
    const icon = L.divIcon({
      html: iconHtml,
      className: "",
      iconSize: [34, 34],
      iconAnchor: [17, 17],
      popupAnchor: [0, -18]
    });

    const marker = L.marker(coords, { icon: icon });

    const popupContent = `
      <div class="map-popup-card">
        <span class="map-popup-category">${escapeHtml(job.category)}</span>
        <h4 class="map-popup-title">${escapeHtml(job.title)}</h4>
        <div class="map-popup-budget">$${job.budget_min.toLocaleString()} - $${job.budget_max.toLocaleString()}</div>
        <p style="font-size:0.75rem; color:#a1a1aa; margin-bottom:8px;">📍 ${escapeHtml(job.location)} • ${job.drop_count ? job.drop_count + " drops" : "Commercial site"}</p>
        <button class="map-popup-btn" onclick="openBidModal(${job.id})">Place Subcontract Bid →</button>
      </div>
    `;

    marker.bindPopup(popupContent);
    marker.addTo(dispatchMap);
    mapMarkers.push(marker);
    bounds.push(coords);
    plottedCount++;
  });

  if (countEl) countEl.textContent = plottedCount;

  if (bounds.length > 0) {
    try {
      dispatchMap.fitBounds(bounds, { padding: [40, 40], maxZoom: 12 });
    } catch (e) {}
  }
}

function setJobViewMode(mode) {
  currentJobViewMode = mode;
  const grid = document.getElementById("jobsGrid");
  const mapWrapper = document.getElementById("dispatchMapWrapper");
  const btnList = document.getElementById("btnListView");
  const btnMap = document.getElementById("btnMapView");
  const btnSplit = document.getElementById("btnSplitView");

  [btnList, btnMap, btnSplit].forEach(b => b && b.classList.remove("active"));

  if (mode === "list") {
    btnList.classList.add("active");
    grid.style.display = "grid";
    mapWrapper.style.display = "none";
    grid.classList.remove("jobs-split-container");
  } else if (mode === "map") {
    btnMap.classList.add("active");
    grid.style.display = "none";
    mapWrapper.style.display = "block";
    mapWrapper.style.width = "100%";
    if (!dispatchMap) initDispatchMap();
    setTimeout(() => { if (dispatchMap) dispatchMap.invalidateSize(); }, 150);
  } else if (mode === "split") {
    btnSplit.classList.add("active");
    grid.style.display = "grid";
    mapWrapper.style.display = "block";
    if (!dispatchMap) initDispatchMap();
    setTimeout(() => { if (dispatchMap) dispatchMap.invalidateSize(); }, 150);
  }
}

// Modal Helpers
function openModal(id) { document.getElementById(id).classList.add("active"); }
function closeModal(id) { document.getElementById(id).classList.remove("active"); }
function escapeHtml(str) {
  if (!str) return "";
  return String(str).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#039;");
}

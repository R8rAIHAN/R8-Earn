/**
 * R8 EARN - ULTRA PREMIUM LUXURY ECOSYSTEM CORE JS LAYER
 * PRODUCTION READY - COMPACT STATE MOTOR ENGINE
 */

// Global State Repository Configuration 
const R8_State = {
    authToken: null,
    userInfo: null,
    wallet: null,
    availableTasks: [],
    currentSubview: 'dashboard',
    tgInitParams: null,
    referrerId: null
};

// Initialize Application Lifecycles on Document Mount
document.addEventListener("DOMContentLoaded", async () => {
    parseTelegramDeepLinkParams();
    initializeTelegramSDKContext();
    await executeAuthenticationHandshake();
});

/**
 * Parses deep-linking query variables handed down by Telegram Mini App launcher containers
 */
function parseTelegramDeepLinkParams() {
    const urlParams = new URLSearchParams(window.location.search);
    
    // Check if structural route requests admin layout bypass fields
    const activeViewMode = urlParams.get('view');
    if (activeViewMode === 'admin_dashboard') {
        R8_State.currentSubview = 'admin_dashboard';
    }
    
    // Extract optional referral ID tracking attributes from startapp context
    const startAppParam = urlParams.get('tgWebAppStartParam');
    if (startAppParam && !isNaN(startAppParam)) {
        R8_State.referrerId = parseInt(startAppParam);
    }
}

/**
 * Connects with native Telegram WebApp Javascript container layers
 */
function initializeTelegramSDKContext() {
    if (window.Telegram && window.Telegram.WebApp) {
        const tgApp = window.Telegram.WebApp;
        tgApp.ready();
        tgApp.expand();
        
        // Handle theme configuration adaptations dynamically
        if (tgApp.colorScheme === 'dark' || tgApp.colorScheme === 'light') {
            document.documentElement.classList.add('dark'); // Force sleek luxury dark schema context
        }
        
        // Extract raw structural verification initData parameters
        if (tgApp.initData) {
            R8_State.tgInitParams = tgApp.initData;
        }
    }
}

/**
 * Handles security handshakes with production API servers
 */
async function executeAuthenticationHandshake() {
    try {
        const globalLoader = document.getElementById('global-loader');
        
        // Handle isolated rendering states for the corporate backend admin interface
        if (R8_State.currentSubview === 'admin_dashboard') {
            if (globalLoader) globalLoader.classList.add('hidden');
            document.getElementById('admin-dashboard-root').classList.remove('hidden');
            await loadBackofficeAnalyticsTelemetry();
            return;
        }

        // Standard User Space WebApp Handshake Routine
        const authPayload = {
            init_data: R8_State.tgInitParams || "",
            referrer_id: R8_State.referrerId
        };

        const response = await fetch('/api/auth/telegram', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(authPayload)
        });

        if (!response.ok) {
            const errorDetails = await response.json();
            alert(`Authentication Security Error: ${errorDetails.detail || 'Handshake rejected.'}`);
            return;
        }

        const data = await response.json();
        R8_State.authToken = data.token;

        // Fetch dashboard statistics records 
        await synchronizeUserEcosystemData();
        
        // Dismiss loading splash screens 
        if (globalLoader) globalLoader.classList.add('hidden');
        document.getElementById('user-app-container').classList.remove('hidden');
        
    } catch (err) {
        console.error("[CRITICAL SHUTDOWN ERROR] Authentication failed: ", err);
        alert("Ecosystem synchronization protocol failure. Please restart inside Telegram.");
    }
}

/**
 * Synchronizes wallet statistics fields from API services
 */
async function synchronizeUserEcosystemData() {
    try {
        const response = await fetch('/api/user/profile', {
            method: 'GET',
            headers: { 'Authorization': `Bearer ${R8_State.authToken}` }
        });

        if (!response.ok) return;
        const profile = await response.json();

        R8_State.userInfo = profile.user_info;
        R8_State.wallet = profile.wallet;

        // Update UI Text Nodes
        document.getElementById('display-username').innerText = `@${R8_State.userInfo.username}`;
        document.getElementById('display-vip-badge').innerText = `VIP Level ${R8_State.userInfo.vip_level}`;
        document.getElementById('display-xp-count').innerText = `${R8_State.userInfo.xp} XP`;
        document.getElementById('global-notice-ticker').innerText = profile.app_notice;
        
        document.getElementById('balance-main').innerText = parseFloat(R8_State.wallet.balance).toFixed(2);
        document.getElementById('balance-pending').innerText = parseFloat(R8_State.wallet.pending_balance).toFixed(2);
        document.getElementById('balance-lifetime').innerText = parseFloat(R8_State.wallet.lifetime_earnings).toFixed(2);
        
        document.getElementById('referral-link-input').value = R8_State.userInfo.referral_link;
        document.getElementById('ref-count-display').innerText = `${profile.referral_count} Users`;

        // Update quota parameters metrics trackers
        calculateDailyMetricsQuotaVelocity();

    } catch (error) {
        console.error("Profile sync exception handled: ", error);
    }
}

/**
 * Computes custom visual indicator bars parameters
 */
function calculateDailyMetricsQuotaVelocity() {
    if (!R8_State.wallet) return;
    const todayEarned = parseFloat(R8_State.wallet.today_earnings || 0);
    const quotaTarget = 100.0; // Benchmark objective point settings definition
    const completedPct = Math.min(Math.round((todayEarned / quotaTarget) * 100), 100);

    document.getElementById('progress-text-pct').innerText = `${completedPct}% Completed`;
    document.getElementById('progress-bar-fill').style.width = `${completedPct}%`;
}

/**
 * Updates visible DOM view sub-frames dynamically without asset reloads
 */
function switchSubview(targetView) {
    const panels = {
        'dashboard': document.getElementById('subview-dashboard'),
        'tasks': document.getElementById('subview-tasks'),
        'referrals': document.getElementById('subview-referrals'),
        'wallet': document.getElementById('subview-wallet')
    };

    // Swap visible display parameters properties classes
    Object.keys(panels).forEach(viewKey => {
        if (viewKey === targetView) {
            panels[viewKey].classList.remove('hidden');
            panels[viewKey].classList.add('subview-transition');
            document.getElementById(`nav-btn-${viewKey}`).className = "flex flex-col items-center justify-center py-1.5 px-3 rounded-xl text-amber-400 bg-amber-400/10 font-bold transition-all";
        } else {
            panels[viewKey].classList.add('hidden');
            panels[viewKey].classList.remove('subview-transition');
            document.getElementById(`nav-btn-${viewKey}`).className = "flex flex-col items-center justify-center py-1.5 px-3 rounded-xl text-slate-400 font-semibold transition-all";
        }
    });

    R8_State.currentSubview = targetView;

    // Fire runtime content fetches based on view parameters properties state triggers
    if (targetView === 'tasks') {
        loadTaskEcosystemContracts();
    }
}

/**
 * Connects task assignment listings records with active backend database objects
 */
async function loadTaskEcosystemContracts() {
    try {
        const container = document.getElementById('tasks-injection-container');
        container.innerHTML = `<div class="text-center py-6 text-xs text-slate-500 animate-pulse"><i class="fa-solid fa-spinner animate-spin mr-2"></i>Compiling secure available task structures...</div>`;

        const response = await fetch('/api/tasks/list', {
            method: 'GET',
            headers: { 'Authorization': `Bearer ${R8_State.authToken}` }
        });

        if (!response.ok) return;
        const tasks = await response.json();
        R8_State.availableTasks = tasks;

        if (tasks.length === 0) {
            container.innerHTML = `<div class="text-center py-8 glass-card rounded-2xl text-xs text-slate-500">All assignment nodes synchronized. Standby for next block schedule cycle.</div>`;
            return;
        }

        container.innerHTML = "";
        tasks.forEach(task => {
            const element = document.createElement('div');
            element.className = "glass-card rounded-2xl p-4 flex items-center justify-between border border-white/[0.02] hover:border-amber-400/20 transition-all";
            element.innerHTML = `
                <div class="flex items-center space-x-3.5 flex-1 min-w-0">
                    <div class="w-10 h-10 rounded-xl bg-slate-900/90 border border-slate-800 flex items-center justify-center text-amber-400 text-sm">
                        <i class="${getCategoryIconVariable(task.category)}"></i>
                    </div>
                    <div class="flex-1 min-w-0">
                        <h4 class="text-xs font-bold text-white tracking-wide truncate">${task.title}</h4>
                        <p class="text-[10px] text-slate-400 truncate mt-0.5">${task.description}</p>
                        <div class="flex items-center space-x-2 mt-1">
                            <span class="text-[9px] font-extrabold text-amber-400">+${task.reward} Coins</span>
                            <span class="text-[8px] px-1.5 py-0.5 rounded bg-slate-900 border border-slate-800 text-slate-500 font-medium uppercase tracking-wider">${task.verification_type}</span>
                        </div>
                    </div>
                </div>
                <div class="flex flex-col space-y-1.5 ml-3">
                    <button onclick="launchTargetTaskDestination('${task.task_url}', ${task.id})" class="bg-slate-900 hover:bg-slate-800 border border-slate-800 text-white font-bold text-[10px] px-3 py-1.5 rounded-lg active:scale-95 transition-transform uppercase tracking-wider">Open</button>
                    <button onclick="triggerTaskVerificationSequence(${task.id})" class="bg-gradient-to-r from-amber-500 to-yellow-400 text-slate-950 font-black text-[10px] px-3 py-1.5 rounded-lg active:scale-95 transition-transform uppercase tracking-wider">Claim</button>
                </div>
            `;
            container.appendChild(element);
        });

    } catch (e) {
        console.error("Task list initialization engine failure: ", e);
    }
}

function getCategoryIconVariable(category) {
    switch (category) {
        case 'Telegram': return 'fa-brands fa-telegram';
        case 'YouTube': return 'fa-brands fa-youtube';
        case 'Facebook': return 'fa-brands fa-facebook';
        default: return 'fa-solid fa-link';
    }
}

function launchTargetTaskDestination(url, taskId) {
    // Send background task allocation initialization alerts to storage frameworks
    fetch('/api/tasks/action', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${R8_State.authToken}` },
        body: JSON.stringify({ task_id: taskId, action: "start" })
    });
    window.open(url, '_blank');
}

async function triggerTaskVerificationSequence(taskId) {
    try {
        const response = await fetch('/api/tasks/action', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${R8_State.authToken}` },
            body: JSON.stringify({ task_id: taskId, action: "verify" })
        });

        const data = await response.json();
        if (!response.ok) {
            alert(data.detail || "Task claim transaction failure.");
            return;
        }

        alert(data.status === 'Approved' ? "Payout Complete! Reward tokens processed successfully." : "Proof submitted. Manual audit queued.");
        await synchronizeUserEcosystemData();
        await loadTaskEcosystemContracts();

    } catch (err) {
        console.error(err);
    }
}

/**
 * Submits high-end payout withdrawal validation forms objects
 */
async function submitWithdrawalForm(event) {
    event.preventDefault();
    const method = document.querySelector('input[name="method"]:checked').value;
    const account = document.getElementById('withdraw-account').value;
    const amount = document.getElementById('withdraw-amount').value;

    try {
        const response = await fetch('/api/withdraw/request', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${R8_State.authToken}` },
            body: JSON.stringify({ method, account, amount })
        });

        const data = await response.json();
        if (!response.ok) {
            alert(data.detail || "Withdraw operational error.");
            return;
        }

        alert(data.msg || "Withdrawal ledger request verified successfully.");
        document.getElementById('withdrawal-request-form').reset();
        await synchronizeUserEcosystemData();

    } catch (e) {
        console.error(e);
    }
}

/**
 * Triggers interactive gamification elements systems mechanics
 */
function openSpinWheelModal() {
    document.getElementById('modal-spin-wheel').style.display = 'flex';
}

function closeSpinWheelModal() {
    document.getElementById('modal-spin-wheel').style.display = 'none';
}

async function executeLuckyWheelEngineSpin() {
    try {
        const response = await fetch('/api/games/spin', {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${R8_State.authToken}` }
        });

        const data = await response.json();
        if (!response.ok) {
            alert(data.detail || "Wheel system cooling state active.");
            return;
        }

        const disc = document.getElementById('visual-wheel-disc');
        disc.style.transform = `rotate(${1440 + Math.floor(Math.random() * 360)}deg)`;

        setTimeout(async () => {
            alert(`Drop Matrix Result: You won ${data.win} R8 Coins!`);
            disc.style.transform = 'rotate(0deg)';
            closeSpinWheelModal();
            await synchronizeUserEcosystemData();
        }, 4100);

    } catch (err) {
        console.error(err);
    }
}

async function triggerDailyRewardClaim() {
    try {
        const res = await fetch('/api/earn/daily', {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${R8_State.authToken}` }
        });
        const data = await res.json();
        if (!res.ok) {
            alert(data.detail || "Calendar daily sequence error.");
            return;
        }
        alert(`Daily Attendance Claimed! +${data.claimed} Coins successfully compiled.`);
        await synchronizeUserEcosystemData();
    } catch (e) { console.error(e); }
}

function copyReferralLink() {
    const input = document.getElementById('referral-link-input');
    input.select();
    input.setSelectionRange(0, 99999);
    navigator.clipboard.writeText(input.value);
    alert("Referral node parameter link copied to host clipboard buffers safely.");
}


// ==========================================
// BACKOFFICE ADMIN CONTROL CENTER LAYOUT LOGIC
// ==========================================
async function loadBackofficeAnalyticsTelemetry() {
    try {
        const resStats = await fetch('/api/admin/analytics');
        if (!resStats.ok) return;
        const stats = await resStats.json();
        
        document.getElementById('adm-metric-users').innerText = stats.metrics.total_users;
        document.getElementById('adm-metric-paid').innerText = parseFloat(stats.metrics.total_paid_withdraws).toFixed(2);
        document.getElementById('adm-metric-pending-w').innerText = stats.metrics.pending_withdrawals;
        document.getElementById('adm-metric-pending-t').innerText = stats.metrics.pending_manual_tasks;

        // Populate system user records lists
        const resUsers = await fetch('/api/admin/users');
        const users = await resUsers.json();
        const usersTable = document.getElementById('adm-table-users');
        usersTable.innerHTML = "";
        
        users.forEach(u => {
            const row = document.createElement('tr');
            row.className = "border-b border-slate-900/50 hover:bg-white/[0.01]";
            row.innerHTML = `
                <td class="py-3 font-mono text-[10px] text-slate-500">${u.id}</td>
                <td class="py-3 font-mono text-slate-400">${u.telegram_id}</td>
                <td class="py-3 font-bold text-white">@${u.username || u.id}</td>
                <td class="py-3 text-amber-400 font-semibold">${parseFloat(u.balance).toFixed(2)}</td>
                <td class="py-3 text-right space-x-1">
                    <button onclick="executeAdministrativeUserModification(${u.id}, 'reward', 500)" class="bg-slate-900 border border-slate-800 text-slate-300 px-2 py-1 rounded text-[10px]">Gift 500</button>
                    ${u.banned ? 
                        `<button onclick="executeAdministrativeUserModification(${u.id}, 'unban')" class="bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 px-2 py-1 rounded text-[10px]">Lift Ban</button>` :
                        `<button onclick="executeAdministrativeUserModification(${u.id}, 'ban')" class="bg-red-500/20 text-red-400 border border-red-500/30 px-2 py-1 rounded text-[10px]">Ban</button>`
                    }
                </td>
            `;
            usersTable.appendChild(row);
        });

        // Populate withdrawal ledgers records lists
        const resWithdraws = await fetch('/api/admin/withdrawals');
        const withdraws = await resWithdraws.json();
        const wTable = document.getElementById('adm-table-withdrawals');
        wTable.innerHTML = "";
        
        if (withdraws.length === 0) {
            wTable.innerHTML = `<tr><td colspan="5" class="py-4 text-center text-slate-600">No liquidation requests inside available queues.</td></tr>`;
        } else {
            withdraws.forEach(w => {
                const row = document.createElement('tr');
                row.className = "border-b border-slate-900/50";
                row.innerHTML = `
                    <td class="py-3 font-bold text-white">@${w.username || 'Node'}</td>
                    <td class="py-3 text-slate-400">${w.method}</td>
                    <td class="py-3 font-mono text-slate-400">${w.account}</td>
                    <td class="py-3 text-amber-400 font-bold">${w.amount}</td>
                    <td class="py-3 text-right">
                        ${w.status === 'Pending' ? `
                            <button onclick="processBackofficeLiquidationRequest(${w.id}, 'Approve')" class="bg-emerald-500 text-slate-950 font-bold px-2 py-1 rounded text-[10px]">Approve</button>
                            <button onclick="processBackofficeLiquidationRequest(${w.id}, 'Reject')" class="bg-red-500 text-white font-bold px-2 py-1 rounded text-[10px] ml-1">Reject</button>
                        ` : `<span class="text-[10px] uppercase font-bold text-slate-600 px-2">${w.status}</span>`}
                    </td>
                `;
                wTable.appendChild(row);
            });
        }

    } catch (err) { console.error("Admin telemetry parsing exception: ", err); }
}

async function executeAdministrativeUserModification(userId, action, value = 0) {
    if (!confirm(`Confirm administrative ${action} action payload modifications onto database row instance?`)) return;
    await fetch('/api/admin/users/action', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: userId, action, value })
    });
    await loadBackofficeAnalyticsTelemetry();
}

async function processBackofficeLiquidationRequest(withdrawId, action) {
    await fetch('/api/admin/withdrawals/process', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ withdraw_id: withdrawId, action })
    });
    await loadBackofficeAnalyticsTelemetry();
}

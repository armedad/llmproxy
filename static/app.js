// LLM Proxy - Web UI

const state = {
    requests: [],
    selectedId: null,
    autoRefresh: false,
    refreshInterval: null,
    filters: {
        path: '',
        model: '',
        status: ''
    }
};

// DOM elements
const elements = {
    requestsBody: document.getElementById('requestsBody'),
    emptyState: document.getElementById('emptyState'),
    detailPanel: document.getElementById('detailPanel'),
    detailTitle: document.getElementById('detailTitle'),
    requestHeaders: document.getElementById('requestHeaders'),
    requestBody: document.getElementById('requestBody'),
    responseHeaders: document.getElementById('responseHeaders'),
    responseBody: document.getElementById('responseBody'),
    requestCount: document.getElementById('requestCount'),
    autoRefresh: document.getElementById('autoRefresh'),
    refreshBtn: document.getElementById('refreshBtn'),
    closeDetail: document.getElementById('closeDetail'),
    filterPath: document.getElementById('filterPath'),
    filterModel: document.getElementById('filterModel'),
    filterStatus: document.getElementById('filterStatus'),
    applyFilters: document.getElementById('applyFilters'),
    clearFilters: document.getElementById('clearFilters')
};

// Fetch requests from API
async function fetchRequests() {
    const params = new URLSearchParams();
    params.set('limit', '100');
    
    if (state.filters.path) params.set('path', state.filters.path);
    if (state.filters.model) params.set('model', state.filters.model);
    if (state.filters.status) params.set('status', state.filters.status);
    
    try {
        const response = await fetch(`/api/requests?${params}`);
        const data = await response.json();
        state.requests = data.requests;
        renderRequests();
        updateRequestCount(data.total);
    } catch (err) {
        console.error('Failed to fetch requests:', err);
    }
}

// Fetch single request detail
async function fetchRequestDetail(id) {
    try {
        const response = await fetch(`/api/requests/${id}`);
        if (!response.ok) return null;
        return await response.json();
    } catch (err) {
        console.error('Failed to fetch request detail:', err);
        return null;
    }
}

// Format timestamp for display
function formatTime(timestamp) {
    const date = new Date(timestamp);
    return date.toLocaleTimeString('en-US', { 
        hour12: false,
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
    });
}

// Format duration
function formatDuration(ms) {
    if (ms < 1000) return `${Math.round(ms)}ms`;
    return `${(ms / 1000).toFixed(2)}s`;
}

// Format tokens
function formatTokens(tokens) {
    if (!tokens) return '-';
    return `${tokens.total}`;
}

// Get status class
function getStatusClass(status) {
    if (status >= 200 && status < 400) return 'status-success';
    return 'status-error';
}

// Get method class
function getMethodClass(method) {
    return `method method-${method.toLowerCase()}`;
}

// Render request list
function renderRequests() {
    if (state.requests.length === 0) {
        elements.requestsBody.innerHTML = '';
        elements.emptyState.classList.remove('hidden');
        return;
    }
    
    elements.emptyState.classList.add('hidden');
    
    elements.requestsBody.innerHTML = state.requests.map(req => `
        <tr data-id="${req.id}" class="${req.id === state.selectedId ? 'selected' : ''}">
            <td>${formatTime(req.timestamp)}</td>
            <td><span class="${getMethodClass(req.method)}">${req.method}</span></td>
            <td class="path">${escapeHtml(req.path)}${req.is_streaming ? '<span class="streaming-badge">SSE</span>' : ''}</td>
            <td class="model">${req.model || '-'}</td>
            <td class="${getStatusClass(req.response_status)}">${req.response_status}</td>
            <td class="duration">${formatDuration(req.duration_ms)}</td>
            <td class="tokens">${formatTokens(req.tokens)}</td>
        </tr>
    `).join('');
}

// Update request count
function updateRequestCount(total) {
    elements.requestCount.textContent = `${total} request${total !== 1 ? 's' : ''}`;
}

// Show request detail
async function showDetail(id) {
    state.selectedId = id;
    
    // Update selected row
    document.querySelectorAll('tbody tr').forEach(tr => {
        tr.classList.toggle('selected', tr.dataset.id === id);
    });
    
    const detail = await fetchRequestDetail(id);
    if (!detail) return;
    
    elements.detailTitle.textContent = `${detail.method} ${detail.path}`;
    elements.requestHeaders.innerHTML = formatJson(detail.request_headers);
    elements.requestBody.innerHTML = formatJson(detail.request_body);
    elements.responseHeaders.innerHTML = formatJson(detail.response_headers);
    elements.responseBody.innerHTML = formatJson(detail.response_body);
    
    elements.detailPanel.classList.remove('hidden');
}

// Hide detail panel
function hideDetail() {
    state.selectedId = null;
    elements.detailPanel.classList.add('hidden');
    document.querySelectorAll('tbody tr').forEach(tr => tr.classList.remove('selected'));
}

// Format JSON with syntax highlighting
function formatJson(obj) {
    if (obj === null || obj === undefined) return '<span class="json-null">null</span>';
    if (typeof obj === 'string') {
        // Check if it's a string that looks like SSE data
        if (obj.includes('data: ')) {
            return escapeHtml(obj);
        }
        return escapeHtml(obj);
    }
    
    const json = JSON.stringify(obj, null, 2);
    return syntaxHighlight(json);
}

// Syntax highlight JSON
function syntaxHighlight(json) {
    json = escapeHtml(json);
    return json.replace(
        /("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*"(\s*:)?|\b(true|false|null)\b|-?\d+(?:\.\d*)?(?:[eE][+\-]?\d+)?)/g,
        (match) => {
            let cls = 'json-number';
            if (/^"/.test(match)) {
                if (/:$/.test(match)) {
                    cls = 'json-key';
                    match = match.slice(0, -1) + '</span>:';
                    return `<span class="${cls}">${match}`;
                } else {
                    cls = 'json-string';
                }
            } else if (/true|false/.test(match)) {
                cls = 'json-boolean';
            } else if (/null/.test(match)) {
                cls = 'json-null';
            }
            return `<span class="${cls}">${match}</span>`;
        }
    );
}

// Escape HTML
function escapeHtml(str) {
    if (typeof str !== 'string') return str;
    return str
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
}

// Copy to clipboard
async function copyToClipboard(elementId) {
    const element = document.getElementById(elementId);
    if (!element) return;
    
    // Get text content (strip HTML)
    const text = element.textContent;
    
    try {
        await navigator.clipboard.writeText(text);
        // Brief visual feedback could be added here
    } catch (err) {
        console.error('Failed to copy:', err);
    }
}

// Toggle auto-refresh
function toggleAutoRefresh(enabled) {
    state.autoRefresh = enabled;
    
    if (enabled) {
        state.refreshInterval = setInterval(fetchRequests, 2000);
    } else if (state.refreshInterval) {
        clearInterval(state.refreshInterval);
        state.refreshInterval = null;
    }
}

// Apply filters
function applyFilters() {
    state.filters.path = elements.filterPath.value.trim();
    state.filters.model = elements.filterModel.value.trim();
    state.filters.status = elements.filterStatus.value;
    
    // Update URL
    const params = new URLSearchParams();
    if (state.filters.path) params.set('path', state.filters.path);
    if (state.filters.model) params.set('model', state.filters.model);
    if (state.filters.status) params.set('status', state.filters.status);
    
    const newUrl = params.toString() ? `?${params}` : window.location.pathname;
    window.history.replaceState({}, '', newUrl);
    
    fetchRequests();
}

// Clear filters
function clearFilters() {
    elements.filterPath.value = '';
    elements.filterModel.value = '';
    elements.filterStatus.value = '';
    state.filters = { path: '', model: '', status: '' };
    
    window.history.replaceState({}, '', window.location.pathname);
    fetchRequests();
}

// Load filters from URL
function loadFiltersFromUrl() {
    const params = new URLSearchParams(window.location.search);
    
    if (params.has('path')) {
        state.filters.path = params.get('path');
        elements.filterPath.value = state.filters.path;
    }
    if (params.has('model')) {
        state.filters.model = params.get('model');
        elements.filterModel.value = state.filters.model;
    }
    if (params.has('status')) {
        state.filters.status = params.get('status');
        elements.filterStatus.value = state.filters.status;
    }
}

// Event listeners
elements.requestsBody.addEventListener('click', (e) => {
    const row = e.target.closest('tr');
    if (row && row.dataset.id) {
        showDetail(row.dataset.id);
    }
});

elements.closeDetail.addEventListener('click', hideDetail);

elements.refreshBtn.addEventListener('click', fetchRequests);

elements.autoRefresh.addEventListener('change', (e) => {
    toggleAutoRefresh(e.target.checked);
});

elements.applyFilters.addEventListener('click', applyFilters);
elements.clearFilters.addEventListener('click', clearFilters);

// Copy buttons
document.querySelectorAll('.btn-copy').forEach(btn => {
    btn.addEventListener('click', (e) => {
        e.stopPropagation();
        copyToClipboard(btn.dataset.target);
    });
});

// Keyboard shortcuts
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        hideDetail();
    }
    if (e.key === 'r' && !e.ctrlKey && !e.metaKey && document.activeElement.tagName !== 'INPUT') {
        fetchRequests();
    }
});

// Initialize
loadFiltersFromUrl();
fetchRequests();

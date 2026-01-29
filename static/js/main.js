/**
 * Main application logic for Job Matching System
 * Includes Mock Auth and Routing
 */

document.addEventListener('DOMContentLoaded', () => {
    setupUploadForm();
    setupSearch();
    loadDashboardMockData();

    // Check local storage for auth state
    if (localStorage.getItem('isLoggedIn') === 'true') {
        setAuthState(true);
    }

    // Init Theme
    initTheme();

    // Init CV
    updateCV();
});

/* --- Theme Logic --- */
function initTheme() {
    const savedTheme = localStorage.getItem('theme') || 'light';
    document.documentElement.setAttribute('data-theme', savedTheme);
    updateThemeIcon(savedTheme);
}

function toggleTheme() {
    const currentTheme = document.documentElement.getAttribute('data-theme');
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';

    document.documentElement.setAttribute('data-theme', newTheme);
    localStorage.setItem('theme', newTheme);
    updateThemeIcon(newTheme);
}

function updateThemeIcon(theme) {
    const icon = document.querySelector('#themeToggle i');
    if (icon) {
        if (theme === 'dark') {
            icon.classList.remove('bi-moon-stars-fill');
            icon.classList.add('bi-sun-fill');
        } else {
            icon.classList.remove('bi-sun-fill');
            icon.classList.add('bi-moon-stars-fill');
        }
    }
}

/* --- CV Builder Logic --- */
function updateCV() {
    // Basic mapping of ID -> ID
    const fields = ['Name', 'Title', 'Email', 'Phone', 'Summary', 'ExpRole', 'ExpCompany', 'ExpDesc', 'EduSchool', 'EduMajor'];

    fields.forEach(field => {
        const input = document.getElementById(`cv${field}`);
        const preview = document.getElementById(`prev${field}`);
        if (input && preview) {
            preview.textContent = input.value;
        }
    });
}

/* --- Navigation & Routing --- */
/* --- Navigation & Routing --- */
// MPA Architecture: Routing is handled by Flask and standard links.
// We remove showTab and utilize DOMContentLoaded in respective templates.

/* --- Common UI Helpers --- */
// ...

// Inner Tabs Removed - now top level pages

/* --- Authentication Mock --- */
function handleLogin(e) {
    e.preventDefault();
    processAuth(e.target, 'Welcome back!', 'You have successfully logged in.');
}

function handleRegister(e) {
    e.preventDefault();
    processAuth(e.target, 'Account Created!', 'Your account has been created successfully.');
}

function processAuth(form, title, message) {
    // Simulate API call
    const btn = form.querySelector('button[type="submit"]');
    const originalText = btn.innerHTML;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span>';

    setTimeout(() => {
        setAuthState(true);
        // Hide all auth modals
        const loginModalEl = document.getElementById('loginModal');
        const registerModalEl = document.getElementById('registerModal');

        if (loginModalEl) {
            const modal = bootstrap.Modal.getInstance(loginModalEl);
            if (modal) modal.hide();
        }
        if (registerModalEl) {
            const modal = bootstrap.Modal.getInstance(registerModalEl);
            if (modal) modal.hide();
        }

        btn.innerHTML = originalText;
        showToast(title, message, 'success');
        btn.innerHTML = originalText;
        showToast(title, message, 'success');
        window.location.href = '/dashboard';
    }, 1000);
}

function logout() {
    setAuthState(false);
    window.location.href = '/upload_page'; // Redirect to upload
    showToast('Logged out', 'See you next time!', 'info');
}

function setAuthState(isLoggedIn) {
    const authButtons = document.getElementById('authButtons');
    const userProfile = document.getElementById('userProfile');

    if (isLoggedIn) {
        localStorage.setItem('isLoggedIn', 'true');
        authButtons.classList.add('d-none');
        userProfile.classList.remove('d-none');
    } else {
        localStorage.removeItem('isLoggedIn');
        authButtons.classList.remove('d-none');
        userProfile.classList.add('d-none');
    }
}

/* --- Dashboard Kanban Data --- */
const KANBAN_DATA = {
    saved: [
        { id: 1, title: "Senior AI Engineer", company: "TechCorp", loc: "Remote", date: "2 mins" },
        { id: 2, title: "Data Scientist", company: "Innovate Inc", loc: "NY", date: "1 day" }
    ],
    applied: [
        { id: 3, title: "Backend Engineer", company: "Amazon", loc: "Seattle", date: "3 days" },
        { id: 4, title: "ML Researcher", company: "DeepMind", loc: "London", date: "5 days" }
    ],
    interview: [
        { id: 5, title: "Full Stack Dev", company: "Google", loc: "MTV", date: "1 week" }
    ],
    offer: [
        { id: 6, title: "Junior Dev", company: "StartupX", loc: "HCMC", date: "2 weeks" }
    ]
};

function loadDashboardMockData() {
    renderAllColumns();
    setupDragAndDrop();
    renderDashboardStats();
    renderDashboardSkills();
    renderRecentActivity();
}

function renderDashboardStats() {
    const totalApps = KANBAN_DATA.saved.length + KANBAN_DATA.applied.length + KANBAN_DATA.interview.length + KANBAN_DATA.offer.length;
    const statEl = document.getElementById('total-apps-stat');
    if (statEl) statEl.textContent = totalApps;
}

function renderDashboardSkills() {
    const skillContainer = document.getElementById('dashboard-skills');
    if (!skillContainer) return;

    const mockSkills = [
        { name: 'Python', level: 90, color: 'primary' },
        { name: 'Data Engineering', level: 75, color: 'info' },
        { name: 'LLM / AI', level: 85, color: 'warning' },
        { name: 'SQL Architecture', level: 65, color: 'success' }
    ];

    skillContainer.innerHTML = mockSkills.map(s => `
        <div class="mb-3">
            <div class="d-flex justify-content-between small mb-1">
                <span class="fw-bold">${s.name}</span>
                <span class="text-muted">${s.level}%</span>
            </div>
            <div class="progress" style="height: 6px; background-color: rgba(0,0,0,0.05)">
                <div class="progress-bar bg-${s.color}" style="width: ${s.level}%"></div>
            </div>
        </div>
    `).join('');
}

function renderRecentActivity() {
    const activityContainer = document.getElementById('recent-activity-list');
    if (!activityContainer) return;

    const activities = [
        { type: 'scan', title: 'CV Analyzed', subtitle: 'AI Software Engineer', time: '2 hours ago', icon: 'bi-file-earmark-pdf', color: 'info' },
        { type: 'move', title: 'Status Update', subtitle: 'Moved Amazon to Applied', time: 'Yesterday', icon: 'bi-arrow-right-circle', color: 'primary' },
        { type: 'interview', title: 'Interview Scheduled', subtitle: 'Google Cloud Team', time: '2 days ago', icon: 'bi-calendar-check', color: 'warning' },
        { type: 'builder', title: 'CV Updated', subtitle: 'Added new AWS certificate', time: '3 days ago', icon: 'bi-pencil-square', color: 'success' }
    ];

    activityContainer.innerHTML = activities.map(a => `
        <div class="d-flex gap-3 mb-4">
            <div class="activity-icon bg-${a.color} bg-opacity-10 text-${a.color} rounded-circle d-flex align-items-center justify-content-center" style="width: 32px; height: 32px; flex-shrink: 0;">
                <i class="bi ${a.icon} small"></i>
            </div>
            <div>
                <div class="small fw-bold">${a.title}</div>
                <div class="text-muted extra-small">${a.subtitle} • ${a.time}</div>
            </div>
        </div>
    `).join('');
}

function renderAllColumns() {
    renderKanbanColumn('saved', 'col-saved');
    renderKanbanColumn('applied', 'col-applied');
    renderKanbanColumn('interview', 'col-interview');
    renderKanbanColumn('offer', 'col-offer');
}

function renderKanbanColumn(key, colId) {
    const col = document.getElementById(colId);
    if (!col) return;

    col.innerHTML = KANBAN_DATA[key].map(item => `
        <div class="card border-0 shadow-sm mb-3 kanban-card draggable" draggable="true" data-id="${item.id}" data-origin="${key}">
            <div class="card-body p-3">
                <h6 class="fw-bold mb-1 text-truncate">${item.title}</h6>
                <div class="text-muted small mb-2">${item.company}</div>
                <div class="d-flex justify-content-between align-items-center">
                    <span class="badge bg-light text-dark border"><i class="bi bi-geo-alt me-1"></i>${item.loc}</span>
                    <small class="text-muted" style="font-size:0.7rem">${item.date}</small>
                </div>
            </div>
        </div>
    `).join('');

    // Update badge count if exists
    const badge = col.parentElement.querySelector('.badge');
    if (badge) badge.textContent = KANBAN_DATA[key].length;
}

/* --- Drag & Drop Logic --- */
let draggedItem = null;

function setupDragAndDrop() {
    const minHeight = "200px"; // Ensure empty cols are droppable
    const columns = document.querySelectorAll('.kanban-column');

    columns.forEach(col => {
        col.style.minHeight = minHeight;

        col.addEventListener('dragover', e => {
            e.preventDefault();
            col.style.backgroundColor = 'rgba(0,0,0,0.02)';
        });

        col.addEventListener('dragleave', e => {
            col.style.backgroundColor = '';
        });

        col.addEventListener('drop', e => {
            e.preventDefault();
            col.style.backgroundColor = '';

            if (!draggedItem) return;

            const originColKey = draggedItem.dataset.origin;
            const targetColId = col.id; // e.g., 'col-applied'
            const targetColKey = targetColId.replace('col-', '');
            const itemId = parseInt(draggedItem.dataset.id);

            if (originColKey === targetColKey) return;

            // Move data
            const itemIndex = KANBAN_DATA[originColKey].findIndex(i => i.id === itemId);
            if (itemIndex > -1) {
                const [item] = KANBAN_DATA[originColKey].splice(itemIndex, 1);
                item.date = "Just now"; // Update time
                KANBAN_DATA[targetColKey].unshift(item); // Add to new col

                // Re-render
                renderAllColumns();
                setupDragAndDrop(); // Re-attach drag events for new elements
                renderDashboardStats();
                renderDashboardSkills();
                renderRecentActivity();
                showToast('Moved', `Moved to ${targetColKey.toUpperCase()}`, 'success');
            }
        });
    });

    // We delegate dragstart since we re-render often, but for now re-attaching is simpler
    // Or we use a static parent listener. Let's stick to delegating or simple re-attach.
    // Actually, since we re-render, we need to bind events to the new elements.
    // Let's modify renderKanbanColumn to attaching dragstart there? 
    // Easier: use document-level delegation or just re-query in setupDragAndDrop which is called after render.

    document.querySelectorAll('.draggable').forEach(draggable => {
        draggable.addEventListener('dragstart', () => {
            draggedItem = draggable;
            draggable.classList.add('opacity-50');
        });

        draggable.addEventListener('dragend', () => {
            draggedItem = null;
            draggable.classList.remove('opacity-50');
        });
    });
}

function handleAddApp(e) {
    e.preventDefault();
    const title = document.getElementById('appTitle').value;
    const company = document.getElementById('appCompany').value;
    const loc = document.getElementById('appLocation').value;
    const status = document.getElementById('appStatus').value;

    const newItem = {
        id: Date.now(),
        title, company, loc, date: "Just now"
    };

    KANBAN_DATA[status].unshift(newItem);
    renderAllColumns();
    setupDragAndDrop();
    renderDashboardStats();
    renderRecentActivity();

    bootstrap.Modal.getInstance(document.getElementById('addAppModal')).hide();
    e.target.reset();
    showToast('Success', 'Application added!', 'success');
}

/* --- Search Mock Logic --- */
function setupSearch() {
    // Populate some initial results
    const resultsDiv = document.getElementById('searchResults');
    const jobs = [
        { title: "Frontend Developer", company: "WebFlow", loc: "San Francisco", type: "Full-time" },
        { title: "Backend Engineer", company: "Amazon", loc: "Seattle", type: "Full-time" },
        { title: "UX Designer", company: "Figma", loc: "Remote", type: "Contract" },
        { title: "Product Manager", company: "Notion", loc: "New York", type: "Full-time" }
    ];

    if (resultsDiv) {
        resultsDiv.innerHTML = jobs.map(job => `
            <div class="card mb-3 border-0 shadow-sm">
                <div class="card-body d-flex justify-content-between align-items-center">
                    <div>
                        <h5 class="card-title text-primary fw-bold mb-1">${job.title}</h5>
                        <p class="card-text text-muted mb-0">
                            <i class="bi bi-building me-1"></i> ${job.company} 
                            <span class="mx-2">•</span> 
                            <i class="bi bi-geo-alt me-1"></i> ${job.loc}
                        </p>
                        <span class="badge bg-light text-dark mt-2">${job.type}</span>
                    </div>
                    <button class="btn btn-primary">Apply</button>
                </div>
            </div>
        `).join('');
    }
}

/* --- Core Functionality (Upload etc) --- */
function setupUploadForm() {
    const form = document.getElementById('uploadForm');
    const fileInput = document.getElementById('pdfFile');
    const uploadArea = document.querySelector('.upload-area');

    if (!form || !fileInput) return;

    // Drag and drop events
    if (uploadArea) {
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            uploadArea.addEventListener(eventName, e => {
                e.preventDefault();
                e.stopPropagation();
            }, false);
        });

        uploadArea.addEventListener('dragover', () => uploadArea.classList.add('dragover'));
        uploadArea.addEventListener('dragleave', () => uploadArea.classList.remove('dragover'));

        uploadArea.addEventListener('drop', (e) => {
            uploadArea.classList.remove('dragover');
            const files = e.dataTransfer.files;
            fileInput.files = files;
            handleFiles(files);
        });

        uploadArea.addEventListener('click', () => fileInput.click());
        fileInput.addEventListener('change', () => handleFiles(fileInput.files));
    }

    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        const loader = document.getElementById('globalLoader');
        if (loader) loader.classList.add('active');

        const formData = new FormData();
        formData.append('pdf_file', fileInput.files[0]);

        try {
            const response = await fetch('/upload', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();

            if (data.success) {
                // Update UI with results
                // showToast('Success', 'CV analysis complete!', 'success'); // Optional, redundant if we move fast

                // Move to results tab
                window.location.href = '/results-page';

                // Reload graph if needed
                // initializeGraph(true);
            } else {
                showToast('Error', data.error || 'Upload failed', 'danger');
            }
        } catch (error) {
            showToast('Error', error.message, 'danger');
        } finally {
            if (loader) loader.classList.remove('active');
        }
    });
}

function handleFiles(files) {
    const fileLabel = document.getElementById('fileNameDisplay');
    if (files.length > 0 && fileLabel) {
        fileLabel.textContent = files[0].name;
        fileLabel.style.display = 'inline-block';
    }
}

// Re-using existing load functions with minor tweaks for ID selectors
async function loadResults() {
    const container = document.getElementById('resultsListContainer'); // Changed ID in HTML
    if (!container) return; // Guard clause

    container.innerHTML = '<div class="text-center py-5"><div class="spinner-border text-primary" role="status"></div></div>';

    try {
        const response = await fetch('/results');
        const results = await response.json();

        if (!Array.isArray(results) || results.length === 0) {
            // container.innerHTML = '<div class="alert alert-info">No match results yet. Upload a CV to get started.</div>';
            return;
        }

        let html = `
            <div class="row g-4 justify-content-center">
            <div class="col-md-10">
                <div class="d-flex justify-content-between align-items-center mb-4">
                    <h3 class="fw-bold mb-0">Top AI Recommendations</h3>
                    <button class="btn btn-outline-secondary btn-sm" onclick="window.location.href='/upload_page'">
                        <i class="bi bi-arrow-left me-2"></i>Upload New CV
                    </button>
                </div>
        `;

        results.forEach((job, index) => {
            html += `
                <div class="job-card d-flex align-items-center justify-content-between fade-in" style="animation-delay: ${index * 0.1}s">
                    <div class="d-flex align-items-center">
                        <div class="badge-score me-4 fs-5">${(job.score * 100).toFixed(0)}%</div>
                        <div>
                            <h5 class="fw-bold mb-1">${job.title}</h5>
                            <div class="text-secondary mb-1">
                                <i class="bi bi-building me-2"></i>${job.company}
                                <span class="mx-2">•</span>
                                <i class="bi bi-geo-alt me-2"></i>${job.city}
                            </div>
                            <div class="small text-success">
                                <i class="bi bi-graph-up-arrow me-1"></i> High text similarity
                            </div>
                        </div>
                    </div>
                    <div>
                        <button class="btn btn-outline-primary btn-sm me-2" onclick="loadJobDetail(${index})">View Analysis</button>
                        <a href="${job.url}" target="_blank" class="btn btn-primary btn-sm">Apply</a>
                    </div>
                </div>
            `;
        });
        html += '</div></div>';
        container.innerHTML = html;

        // Also inject into search results just for demo
        loadDashboardMockData();

    } catch (error) {
        container.innerHTML = `<div class="alert alert-danger">Error loading results: ${error.message}</div>`;
    }
}

async function loadJobDetail(index) {
    try {
        const response = await fetch(`/job/${index}`);
        const detail = await response.json();

        const modalBody = document.getElementById('jobModalBody');

        let html = `
            <div class="row mb-4">
                <div class="col-md-6">
                    <h5 class="mb-3">Overview</h5>
                    <p class="mb-1"><strong>Company:</strong> ${detail.company}</p>
                    <p class="mb-1"><strong>Location:</strong> ${detail.city}</p>
                    <p class="mb-1"><strong>Total Match:</strong> <span class="text-primary fw-bold">${(detail.score * 100).toFixed(1)}%</span></p>
                </div>
                <div class="col-md-6">
                    <h5 class="mb-3">Score Breakdown</h5>
                    <div class="progress mb-2" style="height: 10px;">
                        <div class="progress-bar bg-success" role="progressbar" style="width: ${(detail.components.skill * 100)}%"></div>
                    </div>
                    <small>Skill: ${(detail.components.skill * 100).toFixed(1)}%</small>
                </div>
            </div>

            <div class="mb-4">
                <h6 class="fw-bold mb-3 text-success">Matched Skills</h6>
                <div class="d-flex flex-wrap gap-2">
                    ${(detail.matched_skills || []).map(s =>
            `<span class="badge bg-success bg-opacity-10 text-success border border-success border-opacity-25 p-2">
                            ${s.skill} ${(s.user_prob * 100).toFixed(0)}%
                         </span>`
        ).join('') || '<span class="text-muted">No direct matches</span>'}
                </div>
            </div>
            
             <div>
                 <h6 class="fw-bold mb-3 text-danger">Missing / Required Skills</h6>
                 <div class="d-flex flex-wrap gap-2">
                    ${(detail.missing_skills || []).map(s =>
            `<span class="badge bg-danger bg-opacity-10 text-danger border border-danger border-opacity-25 p-2">
                            ${s.skill}
                         </span>`
        ).join('') || '<span class="text-muted">No missing skills detected!</span>'}
                </div>
            </div>
        `;

        if (modalBody) modalBody.innerHTML = html;
        const modal = new bootstrap.Modal(document.getElementById('jobModal'));
        modal.show();
    } catch (error) {
        showToast('Error', 'Failed to load details', 'danger');
    }
}

async function loadSkills() {
    const container = document.getElementById('skillsList');
    if (!container) return;

    try {
        const response = await fetch('/user-skills');
        const skills = await response.json();

        let html = `
            <div class="d-flex justify-content-between align-items-center mb-4">
                <h3 class="fw-bold mb-0">Extracted Skill Profile</h3>
                <button class="btn btn-outline-secondary btn-sm" onclick="window.location.href='/upload_page'">
                    <i class="bi bi-arrow-left me-2"></i>New CV
                </button>
            </div>
            <div class="d-flex flex-wrap gap-2 p-3 bg-light rounded">
        `;
        skills.forEach(skill => {
            const className = skill.is_core ? 'badge bg-primary' : 'badge bg-secondary';
            html += `<span class="${className} p-2">${skill.name}</span>`;
        });
        html += '</div>';

        container.innerHTML = html;
    } catch (error) {
        console.error(error);
    }
}

async function loadStatistics() {
    // Re-use logic or just leave blank for now as it triggers on tab click
    const container = document.getElementById('statisticsDiv');
    try {
        const response = await fetch('/statistics');
        const stats = await response.json();
        container.innerHTML = `
            <div class="d-flex justify-content-between align-items-center mb-4">
                <h3 class="fw-bold mb-0">Database Statistics</h3>
                <button class="btn btn-outline-secondary btn-sm" onclick="window.location.href='/upload_page'">
                    <i class="bi bi-arrow-left me-2"></i>New CV
                </button>
            </div>
            <div class="row g-4">
                <div class="col-md-3">
                    <div class="card p-3 text-center border-0 shadow-sm">
                        <div class="display-6 fw-bold text-primary">${stats.total_jobs}</div>
                        <div class="small text-muted">Total Jobs</div>
                    </div>
                </div>
                <!-- ... other stats ... -->
            </div>
        `;
    } catch (e) { }
}

function showToast(title, message, type = 'primary') {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show position-fixed top-0 end-0 m-3 shadow-lg`;
    alertDiv.style.zIndex = '9999';
    alertDiv.innerHTML = `
        <strong>${title}</strong> ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    document.body.appendChild(alertDiv);

    setTimeout(() => {
        alertDiv.remove();
    }, 4000);
}


/* --- Mock Interview Interaction --- */
let interviewState = {
    active: false,
    history: []
};

async function startInterview() {
    const messagesDiv = document.getElementById('chat-messages');
    messagesDiv.innerHTML = ''; // Clear start prompt

    interviewState.active = true;
    toggleChatControls(true);

    // Initial Greeting
    addChatMessage('ai', 'Hello! I am your AI interviewer. Based on your CV, I see you are applying for a software engineering role. Let\'s start with a simple question: Can you introduce yourself and highlight your key technical skills?');

    // In a real app, we would call /interview/start here
}

function toggleChatControls(active) {
    document.getElementById('chat-input').disabled = !active;
    document.getElementById('chat-send-btn').disabled = !active;
    if (active) document.getElementById('chat-input').focus();
}

async function handleChatSubmit(e) {
    e.preventDefault();
    const input = document.getElementById('chat-input');
    const message = input.value.trim();

    if (!message) return;

    // 1. Add User Message
    addChatMessage('user', message);
    input.value = '';

    // 2. Show Typing Indicator
    const typingId = showTypingIndicator();

    // 3. Simulate API / Delay
    try {
        const response = await fetch('/interview/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: message, history: interviewState.history })
        });

        const data = await response.json();

        // Remove typing indicator logic would go here (or just replace it)
        removeTypingIndicator(typingId);

        if (data.reply) {
            addChatMessage('ai', data.reply);
        } else {
            addChatMessage('ai', "I'm having trouble connecting to the interview server. Let's try another question.");
        }

    } catch (err) {
        removeTypingIndicator(typingId);
        addChatMessage('ai', "Error connecting to AI service.");
    }
}

function addChatMessage(role, text) {
    const messagesDiv = document.getElementById('chat-messages');
    const bubble = document.createElement('div');
    const timestamp = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

    bubble.className = `chat-bubble ${role} d-flex flex-column`;
    bubble.innerHTML = `
        <span>${text}</span>
        <span class="meta">${timestamp}</span>
    `;

    messagesDiv.appendChild(bubble);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;

    // Add to history
    interviewState.history.push({ role, content: text });
}

function showTypingIndicator() {
    const messagesDiv = document.getElementById('chat-messages');
    const id = 'typing-' + Date.now();
    const bubble = document.createElement('div');
    bubble.className = 'chat-bubble ai';
    bubble.id = id;
    bubble.innerHTML = '<div class="bg-dot-pulse p-2 mx-3"></div>';
    messagesDiv.appendChild(bubble);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
    return id;
}

function removeTypingIndicator(id) {
    const el = document.getElementById(id);
    if (el) el.remove();
}

function endInterview() {
    if (!interviewState.active) return;

    if (confirm("Are you sure you want to end the interview session?")) {
        interviewState.active = false;
        toggleChatControls(false);
        addChatMessage('ai', "Thank you for the session! Good luck with your actual interview.");
    }
}

function downloadTranscript() {
    if (interviewState.history.length === 0) {
        alert("No transcript available yet.");
        return;
    }

    const text = interviewState.history.map(m => `${m.role.toUpperCase()}: ${m.content}`).join('\n\n');
    const blob = new Blob([text], { type: 'text/plain' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'Interview_Transcript.txt';
    a.click();
}

/* --- Salary Prediction Logic (Real API) --- */
async function handleSalaryPredict(e) {
    e.preventDefault();

    const roleInput = document.getElementById('salary-role');
    const expInput = document.getElementById('salary-exp');
    const locInput = document.getElementById('salary-loc');
    const btn = e.target.querySelector('button[type="submit"]');

    const role = roleInput.value;
    const exp = expInput.value;
    const location = locInput ? locInput.value : '';

    // UI Loading State
    const originalBtnText = btn.innerHTML;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Calculating...';
    btn.disabled = true;

    try {
        const response = await fetch('/api/salary-estimate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ role, exp, location })
        });

        const data = await response.json();

        // Update UI
        const placeholder = document.getElementById('salary-placeholder');
        const resultSection = document.getElementById('salary-result');

        if (placeholder && resultSection) {
            placeholder.classList.add('d-none');
            resultSection.classList.remove('d-none');

            // Animate numbers
            if (data.min && data.max) {
                animateValue(document.getElementById('salary-min'), 0, data.min, 1000);
                animateValue(document.getElementById('salary-max'), 0, data.max, 1000);
            }
        }

    } catch (error) {
        showToast('Error', 'Failed to fetch salary estimate', 'danger');
        console.error(error);
    } finally {
        btn.innerHTML = originalBtnText;
        btn.disabled = false;
    }
}

function animateValue(obj, start, end, duration) {
    if (!obj) return;
    let startTimestamp = null;
    const step = (timestamp) => {
        if (!startTimestamp) startTimestamp = timestamp;
        const progress = Math.min((timestamp - startTimestamp) / duration, 1);
        obj.innerHTML = Math.floor(progress * (end - start) + start).toLocaleString();
        if (progress < 1) {
            window.requestAnimationFrame(step);
        }
    };
    window.requestAnimationFrame(step);
}

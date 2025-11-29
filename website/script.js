// Configuration
// IMPORTANT: serve the static site and the backend on different ports.
// Default backend origin for development. If you serve the static files on
// port 8000 (python -m http.server 8000), run the backend on 8001.
const API_URL = 'http://localhost:8001';  // Backend API (use port 8001 when static server uses 8000)

const SOURCES = [
    { name: "LBC", checked: true },
    { name: "MTV", checked: true },
    { name: "961", checked: true },
    { name: "Al Manar", checked: true }
];

// DOM Elements
const toggleBtn = document.getElementById('settingsToggle');
const menuBox = document.getElementById('settingsPanel');
const checkButton = document.getElementById('checkButton');
const urlInput = document.getElementById('articleUrl');
const sourcesGrid = document.getElementById('sourcesGrid');
const resultsSection = document.getElementById('resultsSection');
const errorSection = document.getElementById('errorSection');
const claimsCount = document.getElementById('claimsCount');
const useSampleToggle = () => document.getElementById('useSampleToggle');

// Initialize the app
function initApp() {
    setupEventListeners();
    populateSources();
    checkBackendHealth();
}

// Check if backend is running
async function checkBackendHealth() {
    try {
        const response = await fetch(`${API_URL}/health`);
        const data = await response.json();
        
        console.log('✅ Backend connected:', data);
        
        if (data.articles < 5) {
            console.log(`ℹ️ Database is being populated (${data.articles} articles). Background scraper is running...`);
        }
    } catch (error) {
        console.error('❌ Backend not available:', error);
        showError(`Backend server is not running. Start the backend (example): uvicorn backend.veritas_api:app --reload --port 8001`);
    }
}

// Set up all event listeners
function setupEventListeners() {
    toggleBtn.addEventListener('click', toggleSettings);
    checkButton.addEventListener('click', analyzeArticle);
    urlInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') analyzeArticle();
    });
}

// Populate sources checkboxes
function populateSources() {
    SOURCES.forEach(source => {
        const label = document.createElement('label');
        label.className = 'source-checkbox';
        
        label.innerHTML = `
            <input type="checkbox" name="source" value="${source.name}" ${source.checked ? 'checked' : ''}>
            <span>${source.name}</span>
        `;
        
        sourcesGrid.appendChild(label);
    });
}

// Toggle settings panel
function toggleSettings() {
    menuBox.classList.toggle('active');
    const arrow = toggleBtn.querySelector('.toggle-arrow');
    arrow.style.transform = menuBox.classList.contains('active') ? 'rotate(180deg)' : 'rotate(0deg)';
}

// Main analysis function
async function analyzeArticle() {
    const url = urlInput.value.trim();
    
    if (!url) {
        showError('Please enter a valid URL');
        return;
    }

    // Validate URL
    try {
        new URL(url);
    } catch {
        // If the user enabled the sample toggle, allow empty/invalid URLs and use example.com
        const sampleEl = useSampleToggle();
        if (sampleEl && sampleEl.checked) {
            // continue using example.com as the request URL so the backend returns analysis.json
        } else {
            showError('Please enter a valid URL (include http:// or https://)');
            return;
        }
    }

    setLoadingState(true);
    hideError();
    hideResults();

    try {
        const analysisData = await performAnalysis(url);
        displayResults(analysisData);
    } catch (error) {
        console.error('Analysis error:', error);
        showError(error.message || 'Analysis failed. Please try again.');
    } finally {
        setLoadingState(false);
    }
}

// Call REAL API backend
async function performAnalysis(url) {
    console.log('🔍 Starting fact-check for:', url);
    // show backend status text to user
    const backendStatusEl = document.getElementById('backendStatus');
    if (backendStatusEl) backendStatusEl.textContent = 'Calling backend...';
    
    // Get selected sources
    const selectedSources = Array.from(document.querySelectorAll('input[name="source"]:checked'))
        .map(input => input.value);
    
    // Get articles limit (default 50)
    const articlesLimit = 50;
    
    // Call real backend API
    // If the sample toggle is checked or the url is empty, use example.com so the backend returns website/analysis.json
    const sampleEl = useSampleToggle();
    const requestUrl = (sampleEl && sampleEl.checked) || !url ? 'http://example.com' : url;

    const response = await fetch(`${API_URL}/api/fact-check`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            url: requestUrl,
            sources: selectedSources,
            articles_limit: articlesLimit
        })
    });

    if (!response.ok) {
        const errorData = await response.json();
        if (backendStatusEl) backendStatusEl.textContent = `Backend error: ${errorData.detail || 'request failed'}`;
        throw new Error(errorData.detail || `HTTP ${response.status}: Analysis failed`);
    }

    const data = await response.json();
    console.log('✅ Analysis complete:', data);
    if (backendStatusEl) backendStatusEl.textContent = 'Backend responded';

    // Normalize data: accept either the frontend-shaped JSON (article/claims/stats)
    // or the older raw model output that uses `claims_in_A` and `comparisons`.
    return normalizeAnalysis(data);
}


// Normalize model output to the frontend format expected by displayResults
function normalizeAnalysis(raw) {
    // If already in frontend format, return as-is
    if (raw && raw.claims && raw.article && raw.stats) return raw;

    // Raw model format with claims_in_A
    const mappedClaims = [];
    const rawClaims = raw.claims_in_A || [];

    rawClaims.forEach(c => {
        const matches = (c.comparisons || []).map(comp => {
            const mtype = (comp.match_type || '').toLowerCase();
            const verdict = (mtype === 'support' || mtype === 'agreement') ? 'entailment' : (mtype === 'contradiction' ? 'contradiction' : 'neutral');

            return {
                source: comp.source || comp.source_name || null,
                text: comp.article_title || comp.matched_claim_text || '',
                // preserve actual numeric values when provided; otherwise null
                similarity: (typeof comp.similarity === 'number') ? comp.similarity : null,
                nli_verdict: verdict,
                nli_confidence: (typeof comp.nli_confidence === 'number') ? comp.nli_confidence : null,
                timestamp: comp.published_at || comp.timestamp || null
            };
        });

        mappedClaims.push({
            text: c.claim_text || c.claim || '',
            matches: matches
        });
    });

    // Build stats conservatively
    const total = mappedClaims.length;
    const verified = mappedClaims.reduce((acc, cl) => acc + (cl.matches.some(m => m.nli_verdict === 'entailment') ? 1 : 0), 0);
    const disputed = mappedClaims.reduce((acc, cl) => acc + (cl.matches.some(m => m.nli_verdict === 'contradiction') ? 1 : 0), 0);

    // compute avg_confidence from any provided per-match confidences
    const allConfidences = [].concat(...mappedClaims.map(c => c.matches.map(m => m.nli_confidence))).filter(v => typeof v === 'number');
    const computedAvgConfidence = allConfidences.length ? (allConfidences.reduce((a, b) => a + b, 0) / allConfidences.length) : null;

    const stats = {
        total_claims: total,
        verified_claims: verified,
        disputed_claims: disputed,
        avg_confidence: computedAvgConfidence,
        sources_used: new Set([].concat(...mappedClaims.map(c => c.matches.map(m => m.source))).filter(Boolean)).size
    };

    const article = {
        title: raw.article_title || raw.title || (raw.article && raw.article.title) || 'Article',
        source: raw.current_source || raw.source || (raw.article && raw.article.source) || 'unknown',
        timestamp: raw.user_published_at || raw.published_at || raw.scraped_at || (raw.article && raw.article.timestamp) || null
    };

    // Map bias analysis (if provided by model)
    const bias = raw.bias || raw.bias_analysis || null;

    return { article: article, claims: mappedClaims, stats: stats, bias: bias };
}

// Display results in the UI
function displayResults(data) {
    displayArticleInfo(data.article);
    // Show stats first, then bias analysis, then the claim list
    displayStats(data.stats);
    displayBias(data.bias, data.stats);
    displayClaims(data.claims);
    showResults();
}

function displayBias(bias, stats) {
    const container = document.getElementById('biasContainer');
    if (!container) return;

    if (!bias) {
        container.innerHTML = '';
        return;
    }

    const overall = (stats && stats.overall_bias_score !== undefined && stats.overall_bias_score !== null)
        ? Math.round(stats.overall_bias_score * 100) + '%'
        : '—';

    // Build a small card showing overall bias and the key textual findings
    let biasHTML = `
        <div class="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
            <div class="flex items-start gap-6">
                <div class="flex-shrink-0 w-20 h-20 rounded-xl bg-orange-50 flex items-center justify-center">
                    <div class="text-2xl font-bold text-orange-600">${overall}</div>
                </div>
                <div>
                    <div class="text-sm uppercase tracking-wide text-gray-400 font-semibold">Bias Analysis</div>
                    <div class="mt-2 text-sm text-gray-700">${bias.framing_bias || ''}</div>
                </div>
            </div>
            <div class="mt-4 grid md:grid-cols-3 gap-4">
                <div class="p-4 bg-orange-50 rounded-lg">
                    <div class="text-sm font-semibold text-orange-700">Emotional Language</div>
                    <div class="text-xs text-gray-600 mt-2">${bias.emotional_language || 'No data'}</div>
                </div>
                <div class="p-4 bg-orange-50 rounded-lg">
                    <div class="text-sm font-semibold text-orange-700">Omissions</div>
                    <div class="text-xs text-gray-600 mt-2">${bias.omission_bias || 'No data'}</div>
                </div>
                <div class="p-4 bg-orange-50 rounded-lg">
                    <div class="text-sm font-semibold text-orange-700">Source Bias</div>
                    <div class="text-xs text-gray-600 mt-2">${bias.source_bias || 'No data'}</div>
                </div>
            </div>
        </div>
    `;

    container.innerHTML = biasHTML;
}

function displayArticleInfo(article) {
    const articleInfo = document.getElementById('articleInfo');
    // Format publish date safely -- if timestamp missing or invalid, show 'Unknown'
    let formattedDate = 'Unknown';
    if (article && article.timestamp) {
        try {
            const publishDate = new Date(article.timestamp);
            if (!Number.isNaN(publishDate.getTime())) {
                formattedDate = publishDate.toLocaleDateString('en-US', {
                    year: 'numeric',
                    month: 'long',
                    day: 'numeric',
                    hour: '2-digit',
                    minute: '2-digit'
                });
            }
        } catch (e) {
            formattedDate = 'Unknown';
        }
    }

    // Article summary shown in the results area
    articleInfo.innerHTML = `
        <h4 class="text-lg font-semibold text-veritas-blue">${article.title || 'Article'}</h4>
        <div class="article-meta mt-1 text-sm text-gray-600 flex gap-4">
            <span><strong>Source:</strong> ${article.source || 'unknown'}</span>
            <span><strong>Published:</strong> ${formattedDate}</span>
        </div>
    `;

    // Update hero / header placeholders (if present)
    const heroTitle = document.getElementById('heroTitle');
    const heroMeta = document.getElementById('heroMeta');
    const analyzingBadge = document.getElementById('analyzingBadge');

    if (heroTitle) heroTitle.textContent = article.title || 'Article';
    if (heroMeta) heroMeta.textContent = `${formattedDate}${article.source ? ' • ' + article.source : ''}`;
    if (analyzingBadge) analyzingBadge.textContent = `Analyzing: ${article.source || 'Article'}`;
}

function displayClaims(claims) {
    const container = document.getElementById('claimsContainer');
    container.innerHTML = '';
    
    claimsCount.textContent = `${claims.length} Claims Found`;

    if (claims.length === 0) {
        container.innerHTML = '<div class="no-matches"><p>No claims found in the article.</p></div>';
        return;
    }

    claims.forEach(claim => {
        const claimElement = createClaimElement(claim);
        container.appendChild(claimElement);
    });
}

function createClaimElement(claim) {
    const div = document.createElement('div');
    div.className = 'claim-card bg-white rounded-2xl p-4 shadow-sm border border-gray-100';
    
    let matchesHTML = '';
    
    if (claim.matches.length === 0) {
        matchesHTML = '<div class="no-matches text-sm text-gray-600"><p>ℹ️ No matching claims found in recent articles</p></div>';
    } else {
        claim.matches.forEach(match => {
            const verdictClass = getVerdictClass(match.nli_verdict);
            const verdictText = getVerdictText(match.nli_verdict);
            
            // Format match timestamp safely; fallback to an empty string when not present
            let formattedDate = '';
            if (match && match.timestamp) {
                try {
                    const matchDate = new Date(match.timestamp);
                    if (!Number.isNaN(matchDate.getTime())) {
                        formattedDate = matchDate.toLocaleDateString('en-US', {
                            month: 'short',
                            day: 'numeric',
                            year: 'numeric'
                        });
                    }
                } catch (e) {
                    formattedDate = '';
                }
            }
            
            // prepare display-safe strings for similarity and confidence
            const scoreText = (typeof match.similarity === 'number') ? `${Math.round(match.similarity * 100)}% match` : '';
            const confText = (typeof match.nli_confidence === 'number') ? ` (${Math.round(match.nli_confidence * 100)}%)` : '';

            matchesHTML += `
                <div class="match-card bg-gray-50 rounded-xl p-3 mb-3 border border-gray-100">
                    <div class="match-header flex items-center justify-between mb-2 text-sm text-gray-700">
                        <span class="match-source font-medium">${match.source}</span>
                        <span class="match-score text-gray-500">${scoreText}</span>
                    </div>
                    <p class="match-text text-sm text-gray-800 mb-2">${match.text}</p>
                    <div class="match-meta flex items-center justify-between text-xs text-gray-500">
                        <span>${formattedDate}</span>
                        <span class="verdict ${verdictClass} font-semibold">${verdictText}${confText}</span>
                    </div>
                </div>
            `;
        });
    }

    div.innerHTML = `
        <div class="claim-text text-md text-veritas-blue font-medium mb-3">"${claim.text}"</div>
        <div class="matches-container">${matchesHTML}</div>
    `;

    return div;
}

function displayStats(stats) {
    const container = document.getElementById('statsContainer');
    const summaryContainer = document.getElementById('summaryContainer');
    
    // Top summary colored cards (Cross-source agreement | Bias detected | Sources)
    const agreementPct = (stats.agreement_pct !== undefined && stats.agreement_pct !== null)
        ? Math.round(stats.agreement_pct)
        : (typeof stats.avg_confidence === 'number' ? Math.round(stats.avg_confidence * 100) : null);

    const biasPct = (stats.overall_bias_score !== undefined && stats.overall_bias_score !== null)
        ? Math.round(stats.overall_bias_score * 100)
        : null;

    const summaryHTML = `
        <div class="grid md:grid-cols-3 gap-4 mb-6">
            <div class="rounded-2xl p-6" style="background: linear-gradient(90deg,#ecfdf5,#d1fae5); border:1px solid #d1fae5;"> 
                <div class="text-sm uppercase tracking-wide text-emerald-600 font-semibold">CROSS-SOURCE</div>
                <div class="flex items-center justify-between mt-3">
                    <div class="text-4xl font-bold text-emerald-700">${agreementPct !== null ? agreementPct + '%' : '—'}</div>
                    <div class="w-8 h-8 rounded-full bg-emerald-400"></div>
                </div>
                <div class="mt-3 text-sm text-emerald-700">High agreement across government & opposition sources</div>
            </div>
            <div class="rounded-2xl p-6" style="background: linear-gradient(90deg,#fff7ed,#ffedd5); border:1px solid #ffedd5;">
                <div class="text-sm uppercase tracking-wide text-orange-600 font-semibold">BIAS DETECTED</div>
                <div class="flex items-center justify-between mt-3">
                    <div class="text-4xl font-bold text-orange-700">${biasPct !== null ? biasPct + '%' : (stats.avg_confidence ? Math.round((1 - stats.avg_confidence) * 100) + '%' : '—')}</div>
                    <div class="w-8 h-8 rounded-full bg-orange-300"></div>
                </div>
                <div class="mt-3 text-sm text-orange-700">Emotional language and unverified predictions found</div>
            </div>
            <div class="rounded-2xl p-6" style="background: linear-gradient(90deg,#eff6ff,#e0f2fe); border:1px solid #e0f2fe;">
                <div class="text-sm uppercase tracking-wide text-blue-600 font-semibold">SOURCES</div>
                <div class="flex items-center justify-between mt-3">
                    <div class="text-4xl font-bold text-blue-700">${stats.sources_used ?? '—'}</div>
                    <div class="w-8 h-8 rounded-full bg-blue-300"></div>
                </div>
                <div class="mt-3 text-sm text-blue-700">Sources compared</div>
            </div>
        </div>
    `;

    // Build HTML with smaller stat cards (kept for detail).
    // The outer grid wrapper is not included here because the container
    // (`#statsContainer`) already has the responsive grid classes.
    const avgConfidenceDisplay = (typeof stats.avg_confidence === 'number') ? (Math.round(stats.avg_confidence * 100) + '%') : '—';

    let statsHTML = `
            <div class="bg-white rounded-2xl p-4 shadow-sm border border-gray-100 text-center">
                <div class="stat-value text-2xl font-bold">${stats.total_claims}</div>
                <div class="stat-label text-sm text-gray-500">Total Claims Analyzed</div>
            </div>
            <div class="bg-white rounded-2xl p-4 shadow-sm border border-gray-100 text-center">
                <div class="stat-value text-2xl font-bold">${stats.verified_claims}</div>
                <div class="stat-label text-sm text-gray-500">Supported Claims</div>
            </div>
            <div class="bg-white rounded-2xl p-4 shadow-sm border border-gray-100 text-center">
                <div class="stat-value text-2xl font-bold">${stats.disputed_claims}</div>
                <div class="stat-label text-sm text-gray-500">Contradicted Claims</div>
            </div>
            <div class="bg-white rounded-2xl p-4 shadow-sm border border-gray-100 text-center">
                <div class="stat-value text-2xl font-bold">${avgConfidenceDisplay}</div>
                <div class="stat-label text-sm text-gray-500">Average Confidence</div>
            </div>
            <div class="bg-white rounded-2xl p-4 shadow-sm border border-gray-100 text-center">
                <div class="stat-value text-2xl font-bold">${stats.sources_used}</div>
                <div class="stat-label text-sm text-gray-500">Sources Used</div>
            </div>
    `;
    
    // Add API cost if available (for API-based backend)
    if (stats.api_cost !== undefined) {
        statsHTML += `
            <div class="stat-card">
                <div class="stat-value">$${stats.api_cost.toFixed(4)}</div>
                <div class="stat-label">API Cost</div>
            </div>
        `;
    }
    
    // Add tokens used if available (for API-based backend)
    if (stats.tokens_used !== undefined) {
        statsHTML += `
            <div class="stat-card">
                <div class="stat-value">${stats.tokens_used.toLocaleString()}</div>
                <div class="stat-label">Tokens Used</div>
            </div>
        `;
    }
    
    // Render summary into its own container to avoid being constrained by the stats grid
    if (summaryContainer) summaryContainer.innerHTML = summaryHTML;
    container.innerHTML = statsHTML;
}

// Helper functions
function getVerdictClass(verdict) {
    // Return Tailwind utility classes for verdict badges
    const verdictMap = {
        'entailment': 'text-emerald-700 bg-emerald-50',
        'contradiction': 'text-red-600 bg-red-50',
        'neutral': 'text-yellow-600 bg-yellow-50'
    };
    return verdictMap[verdict] || 'text-gray-600 bg-gray-50';
}

function getVerdictText(verdict) {
    const textMap = {
        'entailment': '✅ Supported',
        'contradiction': '❌ Contradicted',
        'neutral': '⚠️ Uncertain'
    };
    return textMap[verdict] || '⚠️ Uncertain';
}

function setLoadingState(loading) {
    if (loading) {
        checkButton.classList.add('loading');
        checkButton.disabled = true;
    } else {
        checkButton.classList.remove('loading');
        checkButton.disabled = false;
    }
}

function showResults() {
    resultsSection.classList.add('active');
    // Scroll to results
    setTimeout(() => {
        resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }, 100);
}

function hideResults() {
    resultsSection.classList.remove('active');
}

function showError(message) {
    const errorMessage = document.getElementById('errorMessage');
    errorMessage.textContent = message;
    // Make the error section visible (remove the 'hidden' utility if present)
    errorSection.classList.remove('hidden');
    errorSection.classList.add('active');
    
    // Auto-hide after 10 seconds
    setTimeout(() => {
        hideError();
    }, 10000);
}

function hideError() {
    errorSection.classList.remove('active');
    // Hide the error section again
    errorSection.classList.add('hidden');
}

// Initialize the app when the page loads
document.addEventListener('DOMContentLoaded', initApp);

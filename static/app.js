const $ = id => document.getElementById(id);
const form = $('mainForm');
const step1 = $('step1');
const loadingState = $('loadingState');
const resultsState = $('resultsState');
const errorState = $('errorState');
const customTopic = $('customTopic');
const fileInput = $('fileInput');
const fileList = $('fileList');
const submitBtn = $('submitBtn');
const loadingTitle = $('loadingTitle');
const loadingDesc = $('loadingDesc');
const articlesContainer = $('articlesContainer');
const useSampleStyle = $('useSampleStyle');

let hasFiles = false;
let sourceCount = 0;

// Topic quick-select buttons
document.querySelectorAll('.topic-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        const wasSelected = btn.classList.contains('selected');
        document.querySelectorAll('.topic-btn').forEach(b => b.classList.remove('selected'));

        if (!wasSelected) {
            btn.classList.add('selected');
            customTopic.value = btn.dataset.topic.charAt(0).toUpperCase() + btn.dataset.topic.slice(1) + ' news';
        }
        updateSubmitState();
    });
});

customTopic.addEventListener('input', () => {
    document.querySelectorAll('.topic-btn').forEach(b => b.classList.remove('selected'));
    updateSubmitState();
});

useSampleStyle.addEventListener('change', updateSubmitState);

// File upload
$('uploadArea').addEventListener('click', () => fileInput.click());

$('uploadArea').addEventListener('dragover', e => {
    e.preventDefault();
    e.currentTarget.style.borderColor = '#635bff';
    e.currentTarget.style.background = 'rgba(99, 91, 255, 0.1)';
});

$('uploadArea').addEventListener('dragleave', e => {
    e.currentTarget.style.borderColor = '#d0d5dd';
    e.currentTarget.style.background = '#f6f9fc';
});

$('uploadArea').addEventListener('drop', e => {
    e.preventDefault();
    e.currentTarget.style.borderColor = '#d0d5dd';
    e.currentTarget.style.background = '#f6f9fc';
    fileInput.files = e.dataTransfer.files;
    handleFiles(e.dataTransfer.files);
});

fileInput.addEventListener('change', e => handleFiles(e.target.files));

function handleFiles(files) {
    hasFiles = files.length > 0;
    fileList.innerHTML = Array.from(files).map(f =>
        `<span class="file-tag">${f.name}</span>`
    ).join('');

    if (hasFiles) {
        useSampleStyle.checked = false;
    }
    updateSubmitState();
}

function updateSubmitState() {
    const topicValid = customTopic.value.trim().length > 0;
    const styleValid = hasFiles || useSampleStyle.checked;
    submitBtn.disabled = !(topicValid && styleValid);
}

// Progress step management
function setProgressStep(step) {
    const steps = ['search', 'analyze', 'generate'];
    const connectors = document.querySelectorAll('.progress-connector');

    steps.forEach((s, i) => {
        const el = $(`step-${s}`);
        const stepIndex = steps.indexOf(step);

        if (i < stepIndex) {
            el.classList.remove('active');
            el.classList.add('completed');
            if (connectors[i]) connectors[i].classList.add('active');
        } else if (i === stepIndex) {
            el.classList.add('active');
            el.classList.remove('completed');
        } else {
            el.classList.remove('active', 'completed');
            if (connectors[i]) connectors[i].classList.remove('active');
        }
    });
}

function resetProgressSteps() {
    ['search', 'analyze', 'generate'].forEach(s => {
        const el = $(`step-${s}`);
        el.classList.remove('active', 'completed');
    });
    document.querySelectorAll('.progress-connector').forEach(c => c.classList.remove('active'));
}

// Skeleton management
function createSkeletons(count) {
    let html = '';
    for (let i = 0; i < count; i++) {
        html += `
            <div class="article-skeleton" id="skeleton-${i}">
                <div class="skeleton-header">
                    <div class="skeleton-label"></div>
                    <div class="skeleton-btn"></div>
                </div>
                <div class="skeleton-body">
                    <div class="skeleton-line"></div>
                    <div class="skeleton-line"></div>
                    <div class="skeleton-line medium"></div>
                    <div class="skeleton-line"></div>
                    <div class="skeleton-line short"></div>
                </div>
                <div class="skeleton-footer">
                    <div class="skeleton-link"></div>
                </div>
            </div>
        `;
    }
    return html;
}

function showWritingIndicator(articleNum, total) {
    let indicator = $('writingIndicator');
    if (!indicator) {
        indicator = document.createElement('div');
        indicator.id = 'writingIndicator';
        indicator.className = 'writing-indicator';
        articlesContainer.parentNode.insertBefore(indicator, articlesContainer);
    }
    indicator.innerHTML = `
        <div class="writing-dots">
            <div class="writing-dot"></div>
            <div class="writing-dot"></div>
            <div class="writing-dot"></div>
        </div>
        <span>Writing article ${articleNum} of ${total}...</span>
    `;
}

function hideWritingIndicator() {
    const indicator = $('writingIndicator');
    if (indicator) {
        indicator.style.opacity = '0';
        setTimeout(() => indicator.remove(), 300);
    }
}

// Form submission with SSE streaming
form.addEventListener('submit', async e => {
    e.preventDefault();
    if (submitBtn.disabled) return;

    // Reset state
    sourceCount = 0;
    step1.classList.add('hidden');
    loadingState.classList.remove('hidden');
    errorState.classList.add('hidden');
    resultsState.classList.add('hidden');
    articlesContainer.innerHTML = '';
    resetProgressSteps();

    loadingTitle.textContent = 'Starting generation...';
    loadingDesc.textContent = 'This takes about 60 seconds — searching, analyzing, and writing in your voice';
    setProgressStep('search');

    try {
        const formData = new FormData(form);
        formData.set('topic', 'custom');
        formData.set('custom_topic', customTopic.value.trim());

        const response = await fetch('/generate', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || 'Request failed');
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });

            // Process complete SSE messages
            const lines = buffer.split('\n');
            buffer = lines.pop() || '';

            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    try {
                        const data = JSON.parse(line.slice(6));
                        handleStreamEvent(data);
                    } catch (e) {
                        console.error('Parse error:', e);
                    }
                }
            }
        }

    } catch (err) {
        loadingState.classList.add('hidden');
        errorState.textContent = err.message || 'Something went wrong. Please try again.';
        errorState.classList.remove('hidden');
        step1.classList.remove('hidden');
    }
});

function handleStreamEvent(data) {
    switch (data.type) {
        case 'status':
            updateLoadingStatus(data.message);
            break;

        case 'sources':
            sourceCount = data.count;
            // Transition to results view with skeletons
            loadingState.classList.add('hidden');
            resultsState.classList.remove('hidden');
            articlesContainer.innerHTML = createSkeletons(sourceCount);
            break;

        case 'article':
            // Replace skeleton with real article
            replaceSkeletonWithArticle(data.article, data.index);
            break;

        case 'error':
            loadingState.classList.add('hidden');
            resultsState.classList.add('hidden');
            errorState.textContent = data.message;
            errorState.classList.remove('hidden');
            step1.classList.remove('hidden');
            break;

        case 'done':
            hideWritingIndicator();
            break;
    }
}

function updateLoadingStatus(message) {
    const lowerMsg = message.toLowerCase();

    if (lowerMsg.includes('searching')) {
        loadingTitle.textContent = 'Searching for articles...';
        loadingDesc.textContent = 'Finding relevant sources on your topic (~10-15 seconds)';
        setProgressStep('search');
    } else if (lowerMsg.includes('found') && lowerMsg.includes('source')) {
        loadingTitle.textContent = 'Sources found!';
        loadingDesc.textContent = message;
        // Mark search as complete, move to analyze
        $('step-search').classList.remove('active');
        $('step-search').classList.add('completed');
        document.querySelectorAll('.progress-connector')[0].classList.add('active');
        setProgressStep('analyze');
    } else if (lowerMsg.includes('analyz')) {
        loadingTitle.textContent = 'Analyzing your style...';
        loadingDesc.textContent = 'Learning your unique writing voice (~10-15 seconds)';
        setProgressStep('analyze');
    } else if (lowerMsg.includes('style analyzed')) {
        loadingTitle.textContent = 'Style captured!';
        loadingDesc.textContent = 'Ready to write in your voice';
        $('step-analyze').classList.remove('active');
        $('step-analyze').classList.add('completed');
        document.querySelectorAll('.progress-connector')[1].classList.add('active');
    } else if (lowerMsg.includes('writing article')) {
        // Extract article number from message like "Writing article 1 of 3..."
        const match = message.match(/article (\d+) of (\d+)/i);
        if (match) {
            showWritingIndicator(match[1], match[2]);
        }
        setProgressStep('generate');
    }
}

function replaceSkeletonWithArticle(article, index) {
    const skeleton = $(`skeleton-${index}`);
    if (skeleton) {
        const articleHtml = `
            <div class="article-card article-animate">
                <div class="article-header">
                    <span class="article-label">Article ${index + 1}</span>
                    <button type="button" class="copy-btn" onclick="copyText(this, 'article${index}')">Copy</button>
                </div>
                <div class="article-body" id="article${index}">${escapeHtml(article.content)}</div>
                <div class="article-footer">
                    <a href="${article.source.url}" target="_blank" rel="noopener">Source: ${escapeHtml(article.source.title)}</a>
                </div>
            </div>
        `;
        skeleton.outerHTML = articleHtml;
    }

    // Update writing indicator for next article
    if (index < sourceCount - 1) {
        showWritingIndicator(index + 2, sourceCount);
    }
}

// Reset
$('resetBtn').addEventListener('click', () => {
    resultsState.classList.add('hidden');
    step1.classList.remove('hidden');
    form.reset();
    document.querySelectorAll('.topic-btn').forEach(b => b.classList.remove('selected'));
    fileList.innerHTML = '';
    hasFiles = false;
    submitBtn.disabled = true;
    errorState.classList.add('hidden');
    hideWritingIndicator();
});

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function copyText(btn, id) {
    const text = $(id).innerText;
    navigator.clipboard.writeText(text);
    btn.textContent = 'Copied';
    btn.classList.add('copied');
    setTimeout(() => {
        btn.textContent = 'Copy';
        btn.classList.remove('copied');
    }, 2000);
}

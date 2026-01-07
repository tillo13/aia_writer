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

// Form submission with SSE streaming
form.addEventListener('submit', async e => {
    e.preventDefault();
    if (submitBtn.disabled) return;

    step1.classList.add('hidden');
    loadingState.classList.remove('hidden');
    errorState.classList.add('hidden');
    resultsState.classList.add('hidden');
    articlesContainer.innerHTML = '';

    loadingTitle.textContent = 'Starting...';
    loadingDesc.textContent = 'Connecting to AI';

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

        // Show results container immediately
        loadingState.classList.add('hidden');
        resultsState.classList.remove('hidden');

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
            // Update status in results header or show a status bar
            updateStatus(data.message);
            break;

        case 'article':
            appendArticle(data.article, data.index);
            break;

        case 'error':
            resultsState.classList.add('hidden');
            errorState.textContent = data.message;
            errorState.classList.remove('hidden');
            step1.classList.remove('hidden');
            break;

        case 'done':
            hideStatus();
            break;
    }
}

function updateStatus(message) {
    let statusEl = $('streamStatus');
    if (!statusEl) {
        statusEl = document.createElement('div');
        statusEl.id = 'streamStatus';
        statusEl.className = 'stream-status';
        articlesContainer.parentNode.insertBefore(statusEl, articlesContainer);
    }
    statusEl.innerHTML = `<div class="status-dot"></div><span>${message}</span>`;
}

function hideStatus() {
    const statusEl = $('streamStatus');
    if (statusEl) {
        statusEl.style.opacity = '0';
        setTimeout(() => statusEl.remove(), 300);
    }
}

function appendArticle(article, index) {
    const articleHtml = `
        <div class="article-card article-animate" style="animation-delay: ${index * 0.1}s">
            <div class="article-header">
                <span class="article-label">Article ${index + 1}</span>
                <button type="button" class="copy-btn" onclick="copyText(this, 'article${index}')">Copy</button>
            </div>
            <div class="article-body" id="article${index}">${escapeHtml(article.content)}</div>
            <div class="article-footer">
                <a href="${article.source.url}" target="_blank" rel="noopener">Source: ${article.source.title}</a>
            </div>
        </div>
    `;
    articlesContainer.insertAdjacentHTML('beforeend', articleHtml);
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

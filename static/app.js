const $ = id => document.getElementById(id);
const form = $('mainForm');
const step1 = $('step1');
const loadingState = $('loadingState');
const resultsState = $('resultsState');
const errorState = $('errorState');
const topicInput = $('topicInput');
const customTopic = $('customTopic');
const fileInput = $('fileInput');
const fileList = $('fileList');
const submitBtn = $('submitBtn');
const loadingTitle = $('loadingTitle');
const loadingDesc = $('loadingDesc');
const articlesContainer = $('articlesContainer');

let selectedTopic = null;
let hasFiles = false;

const loadingSteps = [
    { title: 'Searching for recent articles', desc: 'Finding relevant sources on your topic' },
    { title: 'Analyzing your writing style', desc: 'Learning your voice, tone, and patterns' },
    { title: 'Generating content', desc: 'Creating articles in your authentic voice' },
    { title: 'Verifying sources', desc: 'Ensuring all citations are valid' },
];

// Topic selection
document.querySelectorAll('.topic-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        document.querySelectorAll('.topic-btn').forEach(b => b.classList.remove('selected'));
        btn.classList.add('selected');
        selectedTopic = btn.dataset.topic;
        topicInput.value = selectedTopic;

        if (selectedTopic === 'custom') {
            customTopic.classList.remove('hidden');
            customTopic.focus();
        } else {
            customTopic.classList.add('hidden');
            customTopic.value = '';
        }
        updateSubmitState();
    });
});

// File upload
$('uploadArea').addEventListener('click', () => fileInput.click());

$('uploadArea').addEventListener('dragover', e => {
    e.preventDefault();
    e.currentTarget.style.borderColor = 'var(--border-hover)';
});

$('uploadArea').addEventListener('dragleave', e => {
    e.currentTarget.style.borderColor = 'var(--border)';
});

$('uploadArea').addEventListener('drop', e => {
    e.preventDefault();
    e.currentTarget.style.borderColor = 'var(--border)';
    fileInput.files = e.dataTransfer.files;
    handleFiles(e.dataTransfer.files);
});

fileInput.addEventListener('change', e => handleFiles(e.target.files));

function handleFiles(files) {
    hasFiles = files.length > 0;
    fileList.innerHTML = Array.from(files).map(f =>
        `<span class="file-tag">${f.name}</span>`
    ).join('');
    updateSubmitState();
}

function updateSubmitState() {
    const topicValid = selectedTopic && (selectedTopic !== 'custom' || customTopic.value.trim());
    submitBtn.disabled = !(topicValid && hasFiles);
}

customTopic.addEventListener('input', updateSubmitState);

// Form submission
form.addEventListener('submit', async e => {
    e.preventDefault();
    if (submitBtn.disabled) return;

    step1.classList.add('hidden');
    loadingState.classList.remove('hidden');
    errorState.classList.add('hidden');

    let stepIndex = 0;
    const loadingInterval = setInterval(() => {
        stepIndex = (stepIndex + 1) % loadingSteps.length;
        loadingTitle.textContent = loadingSteps[stepIndex].title;
        loadingDesc.textContent = loadingSteps[stepIndex].desc;
    }, 4000);

    try {
        const formData = new FormData(form);
        const res = await fetch('/generate', { method: 'POST', body: formData });
        const data = await res.json();

        clearInterval(loadingInterval);

        if (data.error) {
            loadingState.classList.add('hidden');
            errorState.textContent = data.error;
            errorState.classList.remove('hidden');
            step1.classList.remove('hidden');
            return;
        }

        articlesContainer.innerHTML = data.articles.map((article, i) => `
            <div class="article-card">
                <div class="article-header">
                    <span class="article-label">Article ${i + 1}</span>
                    <button type="button" class="copy-btn" onclick="copyText(this, 'article${i}')">Copy</button>
                </div>
                <div class="article-body" id="article${i}">${escapeHtml(article.content)}</div>
                <div class="article-footer">
                    <a href="${article.source.url}" target="_blank" rel="noopener">Source: ${article.source.title}</a>
                </div>
            </div>
        `).join('');

        loadingState.classList.add('hidden');
        resultsState.classList.remove('hidden');

    } catch (err) {
        clearInterval(loadingInterval);
        loadingState.classList.add('hidden');
        errorState.textContent = 'Something went wrong. Please try again.';
        errorState.classList.remove('hidden');
        step1.classList.remove('hidden');
    }
});

// Reset
$('resetBtn').addEventListener('click', () => {
    resultsState.classList.add('hidden');
    step1.classList.remove('hidden');
    form.reset();
    document.querySelectorAll('.topic-btn').forEach(b => b.classList.remove('selected'));
    customTopic.classList.add('hidden');
    fileList.innerHTML = '';
    selectedTopic = null;
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

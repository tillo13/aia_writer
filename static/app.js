const $ = id => document.getElementById(id);
const form = $('mainForm'), step1 = $('step1'), step2 = $('step2'), loading = $('loading');
const results = $('results'), errorDiv = $('error'), articlesDiv = $('articles');
const customInput = $('customTopic'), dropZone = $('dropZone'), fileList = $('fileList');
const loadingText = $('loadingText'), loadingSubtext = $('loadingSubtext');

const loadingMessages = [
    { text: "Searching the web...", sub: "Finding the freshest stories on your topic" },
    { text: "Scanning headlines...", sub: "Looking for the most relevant angles" },
    { text: "Analyzing your style...", sub: "Learning your voice patterns and tone" },
    { text: "Decoding your writing DNA...", sub: "Extracting what makes your writing unique" },
    { text: "Crafting your articles...", sub: "Blending news with your authentic voice" },
    { text: "Adding your signature flair...", sub: "Making sure it sounds like you wrote it" },
    { text: "Polishing the final draft...", sub: "Almost there, just a few more touches" },
    { text: "Quality checking...", sub: "Ensuring every article has real sources" }
];

let messageIndex = 0, messageInterval;

// Topic selection
document.querySelectorAll('input[name="topic"]').forEach(r => {
    r.addEventListener('change', () => {
        customInput.classList.toggle('hidden', r.value !== 'custom');
        if (r.value === 'custom') customInput.focus();
    });
});

// Drag and drop
dropZone.addEventListener('click', () => $('files').click());
dropZone.addEventListener('dragover', e => { e.preventDefault(); dropZone.classList.add('dragover'); });
dropZone.addEventListener('dragleave', () => dropZone.classList.remove('dragover'));
dropZone.addEventListener('drop', e => {
    e.preventDefault();
    dropZone.classList.remove('dragover');
    $('files').files = e.dataTransfer.files;
    showFiles(e.dataTransfer.files);
});

$('files').addEventListener('change', e => showFiles(e.target.files));

function showFiles(files) {
    fileList.innerHTML = Array.from(files).map(f =>
        `<span class="file-tag">📎 ${f.name}</span>`
    ).join('');
}

function nextStep() {
    const selected = document.querySelector('input[name="topic"]:checked');
    if (!selected) { shake(step1); return; }
    if (selected.value === 'custom' && !customInput.value.trim()) { shake(customInput); return; }

    step1.style.opacity = '0';
    step1.style.transform = 'translateY(-20px)';
    setTimeout(() => {
        step1.classList.add('hidden');
        step2.classList.remove('hidden');
        step2.style.opacity = '0';
        step2.style.transform = 'translateY(20px)';
        setTimeout(() => {
            step2.style.opacity = '1';
            step2.style.transform = 'translateY(0)';
        }, 50);
    }, 300);
}

function shake(el) {
    el.style.animation = 'none';
    el.offsetHeight;
    el.style.animation = 'shake 0.5s ease';
}

document.head.insertAdjacentHTML('beforeend', `<style>
@keyframes shake { 0%, 100% { transform: translateX(0); } 25% { transform: translateX(-8px); } 75% { transform: translateX(8px); } }
</style>`);

function cycleLoadingMessages() {
    messageIndex = (messageIndex + 1) % loadingMessages.length;
    loadingText.style.opacity = '0';
    loadingSubtext.style.opacity = '0';
    setTimeout(() => {
        loadingText.textContent = loadingMessages[messageIndex].text;
        loadingSubtext.textContent = loadingMessages[messageIndex].sub;
        loadingText.style.opacity = '1';
        loadingSubtext.style.opacity = '1';
    }, 300);
}

form.addEventListener('submit', async e => {
    e.preventDefault();
    const files = $('files').files;
    if (!files.length) { shake(dropZone); return; }

    // Show loading
    step2.classList.add('hidden');
    loading.classList.remove('hidden');
    errorDiv.classList.add('hidden');

    messageIndex = 0;
    loadingText.textContent = loadingMessages[0].text;
    loadingSubtext.textContent = loadingMessages[0].sub;
    messageInterval = setInterval(cycleLoadingMessages, 3000);

    try {
        const res = await fetch('/generate', { method: 'POST', body: new FormData(form) });
        const data = await res.json();

        clearInterval(messageInterval);

        if (data.error) {
            loading.classList.add('hidden');
            errorDiv.textContent = data.error;
            errorDiv.classList.remove('hidden');
            step2.classList.remove('hidden');
            return;
        }

        articlesDiv.innerHTML = data.articles.map((a, i) => `
            <div class="article-card" style="animation: fadeIn 0.5s ease ${i * 0.15}s forwards; opacity: 0;">
                <div class="article-header">
                    <span class="article-number">Article ${i + 1}</span>
                    <button type="button" class="copy-btn" onclick="copyArticle(${i}, this)">Copy</button>
                </div>
                <div class="article-content" id="content${i}">${escapeHtml(a.content)}</div>
                <div class="article-source">
                    <a href="${a.source.url}" target="_blank" rel="noopener">
                        <span>↗</span> ${a.source.title}
                    </a>
                </div>
            </div>
        `).join('');

        loading.classList.add('hidden');
        results.classList.remove('hidden');
    } catch (err) {
        clearInterval(messageInterval);
        loading.classList.add('hidden');
        errorDiv.textContent = 'Something went wrong. Please try again.';
        errorDiv.classList.remove('hidden');
        step2.classList.remove('hidden');
    }
});

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function copyArticle(i, btn) {
    const content = $(`content${i}`).innerText;
    navigator.clipboard.writeText(content);
    btn.textContent = 'Copied!';
    btn.classList.add('copied');
    setTimeout(() => {
        btn.textContent = 'Copy';
        btn.classList.remove('copied');
    }, 2000);
}

function reset() {
    results.classList.add('hidden');
    step1.classList.remove('hidden');
    step1.style.opacity = '1';
    step1.style.transform = 'translateY(0)';
    step2.style.opacity = '1';
    step2.style.transform = 'translateY(0)';
    form.reset();
    fileList.innerHTML = '';
    customInput.classList.add('hidden');
    errorDiv.classList.add('hidden');
}

// Add smooth transitions
[loadingText, loadingSubtext].forEach(el => el.style.transition = 'opacity 0.3s ease');
[step1, step2].forEach(el => el.style.transition = 'opacity 0.3s ease, transform 0.3s ease');

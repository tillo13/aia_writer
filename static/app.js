const form = document.getElementById('mainForm');
const step1 = document.getElementById('step1');
const step2 = document.getElementById('step2');
const results = document.getElementById('results');
const customInput = document.getElementById('customTopic');
const status = document.getElementById('status');
const topicDisplay = document.getElementById('topicDisplay');
const errorDiv = document.getElementById('error');
const articlesDiv = document.getElementById('articles');
const fileList = document.getElementById('fileList');

// Show custom input when "Custom" selected
document.querySelectorAll('input[name="topic"]').forEach(r => {
    r.addEventListener('change', () => {
        customInput.style.display = r.value === 'custom' ? 'block' : 'none';
    });
});

// Show selected files
document.getElementById('files').addEventListener('change', e => {
    fileList.innerHTML = Array.from(e.target.files).map(f => `<div class="file">${f.name}</div>`).join('');
});

function nextStep() {
    const selected = document.querySelector('input[name="topic"]:checked');
    if (!selected) { alert('Pick a topic'); return; }
    if (selected.value === 'custom' && !customInput.value.trim()) { alert('Enter a custom topic'); return; }

    topicDisplay.textContent = selected.value === 'custom' ? customInput.value : selected.value;
    step1.classList.add('hidden');
    step2.classList.remove('hidden');
}

form.addEventListener('submit', async e => {
    e.preventDefault();
    const files = document.getElementById('files').files;
    if (files.length < 1) { alert('Upload at least one writing sample'); return; }

    status.classList.remove('hidden');
    errorDiv.classList.add('hidden');

    const formData = new FormData(form);
    try {
        const res = await fetch('/generate', { method: 'POST', body: formData });
        const data = await res.json();

        if (data.error) {
            errorDiv.textContent = data.error;
            errorDiv.classList.remove('hidden');
            status.classList.add('hidden');
            return;
        }

        articlesDiv.innerHTML = data.articles.map((a, i) => `
            <div class="article">
                <div class="article-header">
                    <span>Article ${i + 1}</span>
                    <button type="button" onclick="copy(${i})">Copy</button>
                </div>
                <div class="article-content" id="content${i}">${a.content}</div>
                <div class="source">
                    <strong>Source:</strong> <a href="${a.source.url}" target="_blank">${a.source.title}</a>
                </div>
            </div>
        `).join('');

        step2.classList.add('hidden');
        status.classList.add('hidden');
        results.classList.remove('hidden');
    } catch (err) {
        errorDiv.textContent = 'Something went wrong. Try again.';
        errorDiv.classList.remove('hidden');
        status.classList.add('hidden');
    }
});

function copy(i) {
    navigator.clipboard.writeText(document.getElementById(`content${i}`).innerText);
    event.target.textContent = 'Copied!';
    setTimeout(() => event.target.textContent = 'Copy', 2000);
}

function reset() {
    results.classList.add('hidden');
    step1.classList.remove('hidden');
    form.reset();
    fileList.innerHTML = '';
    customInput.style.display = 'none';
}

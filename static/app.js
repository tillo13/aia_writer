let sty = null, nws = null;
let newsPromise = null; // Cache the news fetch promise
let newsFetchStartTime = null;

// Prefetch news immediately when file input is clicked
function prefetchNews() {
    if (newsPromise) {
        console.log('ℹ️ News fetch already in progress, skipping duplicate request');
        return; // Already fetching
    }

    newsFetchStartTime = Date.now();
    console.log('═══════════════════════════════════════════════════════════');
    console.log('🚀 NEWS FETCH STARTED IMMEDIATELY ON FILE BUTTON CLICK');
    console.log('⏱️  Started at:', new Date().toLocaleTimeString());
    console.log('📡 Endpoint: /prefetch_news');
    console.log('═══════════════════════════════════════════════════════════');

    newsPromise = fetch('/prefetch_news')
        .then(r => {
            console.log('📥 Response received from server');
            console.log('⏱️  Response time:', (Date.now() - newsFetchStartTime) + 'ms');
            return r.json();
        })
        .then(d => {
            const totalTime = Date.now() - newsFetchStartTime;
            console.log('═══════════════════════════════════════════════════════════');
            console.log('✅ NEWS FETCH COMPLETE');
            console.log('⏱️  Total time:', totalTime + 'ms');
            console.log('💾 Cached:', d.cached || false);
            console.log('📰 News length:', d.news?.length || 0, 'characters');
            console.log('═══════════════════════════════════════════════════════════');
            return d.news;
        })
        .catch(e => {
            const totalTime = Date.now() - newsFetchStartTime;
            console.log('═══════════════════════════════════════════════════════════');
            console.error('❌ NEWS FETCH ERROR');
            console.error('⏱️  Failed after:', totalTime + 'ms');
            console.error('📛 Error:', e);
            console.log('═══════════════════════════════════════════════════════════');
            newsPromise = null; // Reset on error so it can retry
            throw e;
        });
}

// Get news (either from cache or wait for prefetch)
async function getNews() {
    if (!newsPromise) {
        console.log('⚠️  WARNING: No prefetch found, fetching now (this should not happen!)');
        prefetchNews();
    } else {
        console.log('⏳ Waiting for prefetched news to complete...');
    }

    const result = await newsPromise;
    console.log('✅ News ready for use!');
    return result;
}

function toggle(id) {
    let c = document.getElementById(id + '-content'),
        i = document.getElementById(id + '-icon');
    // Check computed style, not inline style
    let isHidden = window.getComputedStyle(c).display === 'none';
    if (isHidden) {
        c.style.display = 'block';
        i.textContent = '▼';
    } else {
        c.style.display = 'none';
        i.textContent = '▶';
    }
}

async function analyze() {
    let f = document.getElementById('files').files;
    if (!f.length) {
        alert('Please select files first!');
        return;
    }

    console.log('═══════════════════════════════════════════════════════════');
    console.log('📂 FILE ANALYSIS STARTED');
    console.log('📄 Number of files:', f.length);
    console.log('═══════════════════════════════════════════════════════════');

    let s = document.getElementById('upload-status');
    s.innerHTML = '<p class="progress"><span class="spinner"></span>Analyzing your writing style...</p>';

    let fd = new FormData();
    for (let file of f) {
        console.log('📎 File:', file.name, '(' + (file.size / 1024).toFixed(1) + ' KB)');
        fd.append('files', file);
    }

    try {
        console.log('📤 Sending files to /analyze endpoint...');
        const analyzeStartTime = Date.now();

        let r = await fetch('/analyze', { method: 'POST', body: fd });

        console.log('📥 Analysis response received in', (Date.now() - analyzeStartTime) + 'ms');

        let d = await r.json();

        if (d.error) {
            console.error('❌ Analysis error:', d.error);
            s.innerHTML = `<p style="color: #ef4444;">❌ Error: ${d.error}</p>`;
            return;
        }

        sty = d.style_json;

        const totalAnalyzeTime = Date.now() - analyzeStartTime;
        console.log('✅ Style analysis complete in', totalAnalyzeTime + 'ms');
        console.log('📊 Style profile received');

        // Display JSON without code fence
        let styleText = typeof sty === 'string' ? sty : JSON.stringify(sty, null, 2);
        document.getElementById('style-json').textContent = styleText;
        document.getElementById('style-section').style.display = 'block';
        s.innerHTML = `<p style="color: #10b981;">✅ Style analysis complete! (${(totalAnalyzeTime / 1000).toFixed(2)}s)</p>`;

        // Use prefetched news
        console.log('═══════════════════════════════════════════════════════════');
        console.log('📰 NOW RETRIEVING PREFETCHED NEWS...');
        const newsWaitStart = Date.now();

        nws = await getNews();

        console.log('✅ News retrieved in', (Date.now() - newsWaitStart) + 'ms');
        console.log('📰 News preview:', nws.substring(0, 100) + '...');
        console.log('═══════════════════════════════════════════════════════════');

        let nt = document.getElementById('news-text');
        nt.innerHTML = nws.split('\n\n').map(p => `<p>${p}</p>`).join('');
        document.getElementById('news-section').style.display = 'block';
        document.getElementById('cta-box').style.display = 'block';

    } catch (e) {
        console.error('❌ Analysis error:', e);
        s.innerHTML = `<p style="color: #ef4444;">❌ Error: ${e.message}</p>`;
    }
}

async function restyle() {
    if (!sty || !nws) {
        alert('Please analyze files first!');
        return;
    }

    let btn = document.getElementById('restyle-btn');
    btn.disabled = true;
    btn.textContent = 'Generating...';

    let out = document.getElementById('styled-output');
    out.innerHTML = '<p class="progress"><span class="spinner"></span>Writing in your style...</p>';
    document.getElementById('styled-section').style.display = 'block';

    try {
        let claudeVersion = 'sonnet-4';
        let r = await fetch('/restyle', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ style: sty, news: nws, claude_version: claudeVersion })
        });

        let d = await r.json();

        if (d.error) {
            out.innerHTML = `<p style="color: #ef4444;">❌ Error: ${d.error}</p>`;
            btn.disabled = false;
            btn.textContent = 'Write This in My Style';
            return;
        }

        let st = d.styled.split('\n\n').map(p => `<p>${p}</p>`).join('');
        out.innerHTML = st + `<div class="cost-info">💰 Cost: $${d.cost.toFixed(6)}</div>`;

        await showModelOptions();

        btn.disabled = false;
        btn.textContent = 'Write This in My Style';

    } catch (e) {
        out.innerHTML = `<p style="color: #ef4444;">❌ Error: ${e.message}</p>`;
        btn.disabled = false;
        btn.textContent = 'Write This in My Style';
    }
}

async function showModelOptions() {
    try {
        let r = await fetch('/available_models');
        let data = await r.json();

        let html = `
            <h4>✨ Want to see how other AI models would write this?</h4>
            <p>Compare different models' interpretations of your style:</p>
            <div class="model-buttons">
        `;

        for (let model of data.models) {
            html += `
                <button class="model-btn" onclick="restyleWithModel('${model.key}')">
                    <strong>${model.name}</strong>
                    <span>${model.description}</span>
                </button>
            `;
        }

        html += '</div>';

        document.getElementById('model-options').innerHTML = html;
        document.getElementById('model-options').style.display = 'block';

    } catch (e) {
        console.error('Error loading models:', e);
    }
}

async function restyleWithModel(modelKey) {
    let container = document.getElementById('alt-models-output');
    container.style.display = 'block';

    let modelDiv = document.getElementById(`model-${modelKey}`);
    if (!modelDiv) {
        modelDiv = document.createElement('div');
        modelDiv.id = `model-${modelKey}`;
        modelDiv.className = 'model-output';
        container.appendChild(modelDiv);
    }

    modelDiv.innerHTML = `
        <h3>🤖 ${modelKey}</h3>
        <div class="model-content">
            <p class="progress"><span class="spinner"></span>Generating with ${modelKey}...</p>
        </div>
    `;

    modelDiv.scrollIntoView({ behavior: 'smooth', block: 'start' });

    let cleanSty = typeof sty === 'string' ? sty : JSON.stringify(sty);

    try {
        let r = await fetch('/restyle_with_model', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                style: cleanSty,
                news: nws,
                model: modelKey,
                claude_version: modelKey
            })
        });

        let d = await r.json();

        if (d.error) {
            modelDiv.querySelector('.model-content').innerHTML = `
                <p style="color: #ef4444;">❌ Error: ${d.error}</p>
            `;
            return;
        }

        let st = d.styled.split('\n\n').map(p => `<p>${p}</p>`).join('');
        modelDiv.querySelector('.model-content').innerHTML = st +
            `<div class="cost-info">💰 Cost: $${d.cost.toFixed(6)}</div>`;

    } catch (e) {
        modelDiv.querySelector('.model-content').innerHTML = `
            <p style="color: #ef4444;">❌ Error: ${e.message}</p>
        `;
    }
}

let chatMessages = [];

function updateSlider(id) {
    document.getElementById(id + 'Value').textContent = document.getElementById(id + 'Slider').value;
}

document.getElementById('tempSlider')?.addEventListener('input', () => updateSlider('temp'));
document.getElementById('tokenSlider')?.addEventListener('input', () => updateSlider('token'));

async function send() {
    let input = document.getElementById('messageInput'),
        msg = input.value.trim();
    if (!msg) return;

    input.value = '';

    let container = document.getElementById('chatContainer'),
        userDiv = document.createElement('div');
    userDiv.className = 'message user';
    userDiv.textContent = msg;
    container.appendChild(userDiv);

    chatMessages.push({ role: 'user', content: msg });

    let assistantDiv = document.createElement('div');
    assistantDiv.className = 'message assistant';
    assistantDiv.textContent = '';
    container.appendChild(assistantDiv);

    container.scrollTop = container.scrollHeight;

    try {
        let r = await fetch('/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                model: document.getElementById('modelSelect').value,
                messages: chatMessages,
                temperature: parseFloat(document.getElementById('tempSlider').value),
                max_tokens: parseInt(document.getElementById('tokenSlider').value),
                web_search: document.getElementById('webSearchToggle').checked,
                thinking: document.getElementById('thinkingToggle').checked
            })
        });

        let reader = r.body.getReader(),
            decoder = new TextDecoder(),
            fullText = '';

        while (true) {
            let { done, value } = await reader.read();
            if (done) break;

            let chunk = decoder.decode(value),
                lines = chunk.split('\n');

            for (let line of lines) {
                if (line.startsWith('data: ')) {
                    let data = line.slice(6);
                    if (data === '[DONE]') break;
                    if (data.startsWith('Error:')) {
                        assistantDiv.textContent += '\n\n' + data;
                        break;
                    }
                    fullText += data;
                    assistantDiv.textContent = fullText;
                    container.scrollTop = container.scrollHeight;
                }
            }
        }

        chatMessages.push({ role: 'assistant', content: fullText });

    } catch (e) {
        assistantDiv.textContent = 'Error: ' + e.message;
    }
}
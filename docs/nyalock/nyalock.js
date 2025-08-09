// Simple RAG client for GitHub Pages
// - Loads docs/real_transcriptions.json or docs/nyalock/real_transcriptions.json
// - Builds a simple TF-IDF index in the browser
// - Retrieves top-k passages and optionally calls an LLM relay endpoint

const chat = document.getElementById('chat');
const form = document.getElementById('ask-form');
const queryInput = document.getElementById('query');
const useLlm = document.getElementById('use-llm');
const relayEndpoint = document.getElementById('relay-endpoint');

// State
let docs = [];
let index = null;

function addMsg(role, text, meta = null) {
  const el = document.createElement('div');
  el.className = `msg ${role}`;
  el.textContent = text;
  if (meta) {
    const ref = document.createElement('div');
    ref.className = 'ref';
    ref.textContent = meta;
    el.appendChild(ref);
  }
  chat.appendChild(el);
  chat.scrollTop = chat.scrollHeight;
}

function tokenize(text) {
  return text
    .toLowerCase()
    .replace(/[\p{P}\p{S}]/gu, ' ')
    .split(/\s+/)
    .filter(Boolean);
}

function buildIndex(items) {
  const df = new Map();
  const tf = items.map(item => {
    const counts = new Map();
    for (const t of tokenize(item.text)) {
      counts.set(t, (counts.get(t) || 0) + 1);
    }
    for (const term of counts.keys()) {
      df.set(term, (df.get(term) || 0) + 1);
    }
    return counts;
  });
  const N = items.length;
  return { items, df, tf, N };
}

function score(query, index, topK = 8) {
  const qTokens = tokenize(query);
  const qCounts = new Map();
  for (const t of qTokens) qCounts.set(t, (qCounts.get(t) || 0) + 1);

  const scores = index.items.map((it, i) => {
    let s = 0;
    for (const [term, qtf] of qCounts.entries()) {
      const df = index.df.get(term) || 0;
      if (df === 0) continue;
      const idf = Math.log((index.N + 1) / (df + 0.5));
      const tf = index.tf[i].get(term) || 0;
      s += (qtf * (1 + Math.log(1 + tf))) * idf;
    }
    return { i, s };
  });
  scores.sort((a, b) => b.s - a.s);
  return scores.slice(0, topK).map(({ i, s }) => ({ ...index.items[i], score: s }));
}

async function fetchJsonWithFallback(paths) {
  let lastErr = null;
  for (const p of paths) {
    try {
      const res = await fetch(p, { cache: 'no-store' });
      if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
      const ct = res.headers.get('content-type') || '';
      const text = await res.text();
      if (!ct.includes('application/json') && text.trim().startsWith('<')) {
        throw new Error('Received HTML instead of JSON');
      }
      return JSON.parse(text);
    } catch (e) {
      lastErr = e;
    }
  }
  throw lastErr || new Error('All fetch attempts failed');
}

async function loadData() {
  try {
    // Try same folder first, then parent docs folder
    const data = await fetchJsonWithFallback([
      './real_transcriptions.json',
      '../real_transcriptions.json'
    ]);

    const items = [];
    if (Array.isArray(data?.transcriptions)) {
      for (const t of data.transcriptions) {
        const title = t?.metadata?.title || 'Untitled';
        const date = t?.metadata?.record_date || t?.metadata?.estimated_date || '';
        const url = t?.metadata?.url || '';
        const text = t?.transcription || '';
        if (!text) continue;
        const parts = text.split(/\n\n+/).filter(Boolean);
        parts.forEach((p, idx) => {
          items.push({ id: `${url}#p${idx}`, text: p.slice(0, 2000), title, date, url });
        });
      }
    }
    if (Array.isArray(data?.videos)) {
      for (const v of data.videos) {
        const title = v?.metadata?.title || 'Untitled';
        const date = v?.metadata?.estimated_date || '';
        const url = v?.metadata?.url || '';
        const text = v?.transcription || '';
        if (!text) continue;
        const parts = text.split(/\n\n+/).filter(Boolean);
        parts.forEach((p, idx) => {
          items.push({ id: `${url}#p${idx}`, text: p.slice(0, 2000), title, date, url });
        });
      }
    }
    docs = items;
    index = buildIndex(items);
    addMsg('bot', `データを読み込みました（チャンク数: ${items.length}）。質問をどうぞ。`);
  } catch (e) {
    addMsg('bot', `データ読み込みに失敗しました: ${e}`);
  }
}

async function callRelay(prompt, contexts) {
  const endpoint = relayEndpoint.value?.trim();
  if (!endpoint) return null;
  const payload = { prompt, contexts, persona: 'kamui', style: { tone: '落ち着いた・丁寧', disfluencies: true, persona: '神威' }};
  const res = await fetch(endpoint, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
  if (!res.ok) throw new Error(`Relay error: ${res.status}`);
  const data = await res.json();
  return data?.text || data?.answer || JSON.stringify(data);
}

form.addEventListener('submit', async (e) => {
  e.preventDefault();
  const q = queryInput.value.trim();
  if (!q) return;
  addMsg('user', q);
  queryInput.value = '';

  if (!index) {
    addMsg('bot', '索引が未構築です。ページを更新してください。');
    return;
  }
  const top = score(q, index, 8);
  const refText = top.slice(0, 3).map(t => `${t.title} (${t.date})`).join(' / ');

  if (useLlm.checked) {
    try {
      const answer = await callRelay(q, top);
      addMsg('bot', answer || '中継応答が空でした。', `参照: ${refText}`);
    } catch (e) {
      addMsg('bot', `LLM中継に失敗: ${e}`, `参照: ${refText}`);
    }
  } else {
    const stitched = top.map(t => `【${t.title} ${t.date}】\n${t.text}`).join('\n\n');
    const template = `以下は会議/記事の抜粋です。これに基づき、神威の口調（丁寧/落ち着き/フィラー可）で要点を回答してください。\n\n${stitched}\n\n回答:`;
    addMsg('bot', template, `参照: ${refText}`);
  }
});

loadData();

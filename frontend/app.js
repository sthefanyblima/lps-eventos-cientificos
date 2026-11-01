// Frontend do produto derivado. Todas as chamadas passam pelo API Gateway (/api/<microservice>/...).
// As abas exibidas dependem das features do produto (GET /api/product).
const S = { product: null, user: null, token: null, agenda: new Set() };
const $ = s => document.querySelector(s);
const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

async function api(svc, path, opts = {}) {
  const headers = { 'Content-Type': 'application/json' };
  if (S.token) headers.Authorization = `Bearer ${S.token}`;   // JWT validado pelo API Gateway
  const r = await fetch(`/api/${svc}${path}`, {
    headers, ...opts,
    body: opts.body ? JSON.stringify(opts.body) : undefined,
  });
  const data = r.headers.get('content-type')?.includes('json') ? await r.json() : await r.text();
  if (!r.ok) throw new Error(data.detail || r.statusText);
  return data;
}
const has = f => S.product.features.includes(f);
const svcOn = s => s in S.product.services;

async function boot() {
  S.product = await (await fetch('/api/product')).json();
  document.documentElement.style.setProperty('--pri', S.product.theme || '#2563eb');
  document.title = S.product.name;
  $('#ev-name').textContent = S.product.name;
  const ev = await api('events', '/event');
  $('#ev-sub').textContent = `${ev.period} · ${ev.location} · tenant: ${ev.tenant}`;

  // badges "microservice :porta" em cada painel (item 8 do relatório)
  document.querySelectorAll('.badge[data-svc]').forEach(b => {
    const s = S.product.services[b.dataset.svc];
    b.textContent = s ? `${b.dataset.svc}-service :${s.port}` : '';
  });
  renderStrip();
  setInterval(renderStrip, 10000);

  const demo = await api('users', '/auth/demo-accounts');
  $('#user-list').innerHTML = demo.map(u => `<div class="user"><div><b>${esc(u.name)}</b> <span class="muted">· ${u.role}</span><br>
    <span class="meta">${esc(u.email)} · senha: ${esc(u.password)}</span></div>
    <button type="button" class="ghost" data-email="${esc(u.email)}" data-pass="${esc(u.password)}">Usar</button></div>`).join('');
  $('#user-list').onclick = e => {
    if (!e.target.dataset.email) return;
    $('#login-form').email.value = e.target.dataset.email; $('#login-form').password.value = e.target.dataset.pass;
  };
  $('#login-form').onsubmit = async e => {
    e.preventDefault();
    try {
      const res = await api('users', '/auth/login', { method: 'POST', body: { email: e.target.email.value, password: e.target.password.value } });
      S.token = res.access_token; S.user = res.user; enterApp();
    } catch (err) { $('#login-error').hidden = false; $('#login-error').textContent = err.message; }
  };
}

async function renderStrip() {
  const d = await (await fetch('/api/ports')).json();
  $('#ms-strip').innerHTML = '<b>Microservices deste produto:</b> ' + d.services.map(s =>
    `<span class="ms ${s.status === 'UP' ? 'up' : 'down'}">${s.service}:${s.port}</span>`).join('');
}

function enterApp() {
  $('#login').hidden = true; $('#tabs').hidden = false; $('#app').hidden = false;
  $('#who').innerHTML = `${esc(S.user.name)} <span class="muted" style="color:#fff;opacity:.8">(${S.user.role})</span><button class="ghost" id="logout">Sair</button>`;
  $('#logout').onclick = () => location.reload();
  const sections = [...document.querySelectorAll('main section')].filter(s => has(s.dataset.feature));
  document.querySelectorAll('main section').forEach(s => { if (!has(s.dataset.feature)) s.remove(); });
  $('#tabs').innerHTML = sections.map(s => `<button data-tab="${s.dataset.tab}">${s.dataset.label}</button>`).join('');
  $('#tabs').onclick = e => e.target.dataset.tab && show(e.target.dataset.tab);
  show(sections[0].dataset.tab);
}

const loaders = {
  programacao: loadSessions, recomendacoes: loadRecs, inscricao: loadRegistration, submissoes: loadSubs,
  revisao: loadQueue, certificados: loadCerts, notificacoes: loadInbox, assistente: loadAgent,
};
function show(tab) {
  document.querySelectorAll('#tabs button').forEach(b => b.classList.toggle('active', b.dataset.tab === tab));
  document.querySelectorAll('main section').forEach(s => s.classList.toggle('active', s.dataset.tab === tab));
  loaders[tab]?.().catch(err => alert(err.message));
}

async function refreshAgenda() { S.agenda = new Set(await api('registration', `/agenda/${S.user.id}/ids`)); }

function sessionCard(s, extra = '') {
  const inAg = S.agenda.has(s.id);
  return `<div class="card session">${s.score !== undefined ? `<span class="score">score ${s.score}</span>` : ''}
    <h3>[${s.id}] ${esc(s.title)}</h3>
    <div class="meta">${s.kind} · ${esc(s.speaker)}<br>${s.day} ${s.start} · ${esc(s.room)}${s.track ? ` · <b>${esc(s.track)}</b>` : ''}</div>
    <div class="tags">${s.tags.map(t => `<span>${esc(t)}</span>`).join('')}</div>${extra}
    <div class="actions">
      <button class="ghost" data-act="favorite" data-id="${s.id}">★ Favoritar</button>
      <button ${inAg ? 'disabled' : ''} data-act="agenda" data-id="${s.id}">${inAg ? '✔ Na agenda' : '+ Agenda'}</button>
    </div></div>`;
}
async function sessionAction(e) {
  const { act, id } = e.target.dataset; if (!act) return;
  if (act === 'favorite') {
    await api('users', `/users/${S.user.id}/history`, { method: 'POST', body: { session_id: +id, action: 'favorite' } });
    e.target.textContent = '★ Favoritada';
  } else {
    const r = await api('registration', `/agenda/${S.user.id}`, { method: 'POST', body: { session_id: +id } });
    alert(r.message); await refreshAgenda(); e.target.disabled = r.ok; if (r.ok) e.target.textContent = '✔ Na agenda';
  }
}

async function loadSessions() {
  await refreshAgenda();
  if (has('Trilhas')) {
    const tracks = await api('events', '/tracks');
    const sel = $('#track'); sel.hidden = false;
    if (!sel.options.length) sel.innerHTML = '<option value="">Todas as trilhas</option>' + tracks.map(t => `<option>${esc(t)}</option>`).join('');
  }
  const draw = async () => {
    const p = new URLSearchParams({ q: $('#q').value, track: $('#track').value || '' });
    const list = await api('events', `/sessions?${p}`);
    $('#sessions').innerHTML = list.map(s => sessionCard(s)).join('') || '<p class="muted">Nada encontrado.</p>';
  };
  $('#q').oninput = draw; $('#track').onchange = draw; $('#sessions').onclick = sessionAction;
  draw();
  // registrar "view" ao abrir um card (alimenta o histórico)
  $('#sessions').ondblclick = e => {
    const card = e.target.closest('.session'); if (!card) return;
    const id = +card.querySelector('[data-id]').dataset.id;
    api('users', `/users/${S.user.id}/history`, { method: 'POST', body: { session_id: id, action: 'view' } });
  };
}

async function loadRecs() {
  await refreshAgenda();
  const r = await api('recommendation', `/recommendations/${S.user.id}?k=6`);
  $('#rec-info').innerHTML = `Estratégia: <b>${r.strategy}</b> (variante <code>${r.variant}</code>) · baseada em seus interesses
    (${r.based_on.interests.map(esc).join(', ')}) e em ${r.based_on.history_size} interações do seu histórico.`;
  $('#recs').innerHTML = r.items.map(s => sessionCard(s, `<div class="reason">💡 ${esc(s.reason)}</div>`)).join('');
  $('#recs').onclick = async e => { await sessionAction(e); if (e.target.dataset.act) loadRecs(); };
  const hist = await api('recommendation', `/recommendations/${S.user.id}/history`);
  $('#rec-hist').innerHTML = '<table class="tbl"><tr><th>Gerada em</th><th>Sessão</th><th>Score</th><th>Estratégia</th></tr>' +
    hist.slice(0, 12).map(h => `<tr><td>${h.generated_at}</td><td>${esc(h.session_title)}</td><td>${h.score}</td><td>${h.strategy}</td></tr>`).join('') + '</table>';
}

async function loadRegistration() {
  const pm = await api('registration', '/payment-method');
  let reg = null; try { reg = await api('registration', `/registrations/${S.user.id}`); } catch { }
  const box = $('#reg');
  const fee = pm.fee ? `R$ ${pm.fee.toFixed(2)}` : 'gratuita';
  if (reg && reg.status === 'approved') {
    box.innerHTML = `<span class="ok">✔ Inscrição confirmada</span> · ${pm.label} · ${esc(reg.details.details)}`;
  } else if (reg && reg.status === 'pending') {
    box.innerHTML = `<span class="warn">⏳ Pagamento pendente</span> (${pm.label})<pre class="code">${esc(reg.details.pix_code)}</pre>
      <button id="confirm">Simular confirmação do PIX</button>`;
    $('#confirm').onclick = async () => { await api('registration', `/registrations/${S.user.id}/confirm`, { method: 'POST' }); loadRegistration(); };
  } else {
    box.innerHTML = `Taxa de inscrição: <b>${fee}</b> · forma de pagamento deste evento: <b>${pm.label}</b>
      ${reg && reg.status === 'refused' ? `<p class="bad">Recusado: ${esc(reg.details.details)}</p>` : ''}
      <div class="toolbar" style="margin-top:10px">${pm.variant === 'CartaoCredito' ? '<input id="card" value="4111 1111 1111 1111" placeholder="Cartão de teste">' : ''}
      <button id="do-reg">Inscrever-me</button></div>`;
    $('#do-reg').onclick = async () => {
      await api('registration', '/registrations', { method: 'POST', body: { user_id: S.user.id, card_number: $('#card')?.value } });
      loadRegistration();
    };
  }
  const ag = await api('registration', `/agenda/${S.user.id}`);
  $('#agenda').innerHTML = ag.length ? ag.map(s => `<div class="card">${s.day} <b>${s.start}</b> — ${esc(s.title)} <span class="meta">· ${esc(s.room)}</span>
      <button class="ghost" style="float:right" data-rm="${s.id}">remover</button></div>`).join('') : '<p class="muted">Agenda vazia. Veja a aba “Para você”.</p>';
  $('#agenda').onclick = async e => { if (e.target.dataset.rm) { await api('registration', `/agenda/${S.user.id}/${e.target.dataset.rm}`, { method: 'DELETE' }); loadRegistration(); } };
}

async function loadSubs() {
  const formats = await api('submissions', '/formats');
  $('#formats').innerHTML = formats.map(f => `<option value="${f.id}">${f.label}</option>`).join('');
  $('#sub-form').onsubmit = async e => {
    e.preventDefault();
    const body = Object.fromEntries(new FormData(e.target)); body.author_id = S.user.id;
    await api('submissions', '/submissions', { method: 'POST', body }); e.target.reset(); loadSubs();
  };
  const subs = await api('submissions', `/submissions?author_id=${S.user.id}`);
  const label = { submitted: 'submetido', under_review: 'em revisão', accepted: 'ACEITO', rejected: 'rejeitado' };
  const parts = await Promise.all(subs.map(async s => {
    let revs = '';
    if (svcOn('reviews')) {
      const rv = await api('reviews', `/reviews/submission/${s.id}`);
      revs = rv.map(r => `<div class="meta">• ${esc(r.reviewer_name)}: nota ${r.score} — ${esc(r.comment)}</div>`).join('');
    }
    return `<div class="card"><b>#${s.id} ${esc(s.title)}</b> <span class="meta">(${s.format})</span> —
      <span class="${s.status === 'accepted' ? 'ok' : s.status === 'rejected' ? 'bad' : 'warn'}">${label[s.status]}</span>${revs}</div>`;
  }));
  $('#my-subs').innerHTML = parts.join('') || '<p class="muted">Nenhuma submissão.</p>';
}

async function loadQueue() {
  const pol = await api('reviews', '/policy');
  $('#policy').innerHTML = `Política: <b>${pol.label}</b> — ${pol.description}`;
  const q = await api('reviews', `/queue/${S.user.id}`);
  $('#queue').innerHTML = q.map(s => `<div class="card"><b>#${s.id} ${esc(s.title)}</b> <span class="meta">(${s.format})</span><br>
      <span class="meta">Autores: ${esc(s.authors)} · status: ${s.status}</span><p>${esc(s.abstract)}</p>
      ${s.reviewed ? '<span class="ok">✔ parecer enviado</span>' : `<div class="toolbar"><select data-score="${s.id}">
        ${[3, 2, 1, 0, -1, -2, -3].map(v => `<option value="${v}">${v}</option>`).join('')}</select>
        <input data-comment="${s.id}" placeholder="Comentário"><button data-review="${s.id}">Enviar parecer</button></div>`}</div>`).join('')
    || '<p class="muted">Nenhum trabalho para revisar.</p>';
  $('#queue').onclick = async e => {
    const id = e.target.dataset.review; if (!id) return;
    const r = await api('reviews', '/reviews', { method: 'POST', body: {
      submission_id: +id, reviewer_id: S.user.id, score: +$(`[data-score="${id}"]`).value, comment: $(`[data-comment="${id}"]`).value } });
    alert(`Média ${r.average} → ${r.status}`); loadQueue();
  };
}

async function loadCerts() {
  const cs = await api('certificates', `/certificates/${S.user.id}`);
  $('#certs').innerHTML = cs.map(c => `<div class="card"><b>${c.type}</b> · ${c.hours}h<p>${esc(c.text)}</p>
     <span class="meta">Código: ${c.code}</span> · <a target="_blank" href="/api/certificates/view/${c.code}">abrir certificado</a></div>`).join('')
    || '<p class="muted">Nenhum certificado disponível (é preciso inscrição confirmada ou trabalho aceito).</p>';
}

async function loadInbox() {
  const n = await api('notifications', `/notifications/${S.user.id}`);
  $('#inbox').innerHTML = n.map(x => `<div class="card"><b>${esc(x.subject)}</b> <span class="meta">· ${x.at}</span><br>${esc(x.message)}</div>`).join('')
    || `<p class="muted">Sem notificações no app${S.product.components.notification_channels?.includes('Email') ?  ' (e-mails simulados ficam na tabela email_enviado)' : ''}.</p>`;
}

async function loadAgent() {
  const tools = await api('ai_agent', `/tools/${S.user.id}`);
  const arch = await api('ai_agent', '/architecture');
  $('#arch').innerHTML = `<p class="meta">Provedor: <b>${esc(arch.provider)}</b> · consulta ao modelo: ${esc(arch.querying)}</p>` +
    Object.entries(arch.components).map(([k, v]) => `<p><b>${esc(k)}</b>: ${v.map(esc).join(' · ')}</p>`).join('');
  $('#agent-info').innerHTML = `Provedor: <b>${S.product.components.ai_provider}</b> · ferramentas disponíveis (dependem das features do produto): ${tools.map(t => `<code>${t.name}</code>`).join(', ')}`;
  const sugg = ['O que você recomenda para mim?', 'Tem sessões sobre microservices?', 'Tem mais sessões sobre isso?', 'Me recomende algo e adicione à agenda', 'Mostre minha agenda', 'O que você sabe sobre mim?', 'Como estão minhas submissões?'];
  $('#suggestions').innerHTML = sugg.map(s => `<button type="button">${s}</button>`).join('');
  $('#suggestions').onclick = e => { if (e.target.tagName === 'BUTTON') { $('#msg').value = e.target.textContent; $('#chat-form').requestSubmit(); } };
  $('#chat-form').onsubmit = async e => {
    e.preventDefault();
    const msg = $('#msg').value.trim(); if (!msg) return; $('#msg').value = '';
    $('#chat').insertAdjacentHTML('beforeend', `<div class="bubble me">${esc(msg)}</div>`);
    const r = await api('ai_agent', '/chat', { method: 'POST', body: { user_id: S.user.id, message: msg } });
    $('#chat').insertAdjacentHTML('beforeend', `<div class="bubble bot">${esc(r.answer)}</div>
      <details class="trace"><summary>explainer · ${esc(r.provider)} · ${r.trace.length} chamada(s) de ferramenta · caixa-preta ${r.request_id.slice(0, 8)}</summary>
      <pre>${esc(r.explanation.join('\n'))}\n\n${esc(r.trace.map(t => `→ [${t.service}] ${t.tool}(${JSON.stringify(t.input)}) — ${t.status}\n← ${JSON.stringify(t.output).slice(0, 260)}`).join('\n\n'))}</pre></details>`);
  };
}

boot().catch(e => { document.body.insertAdjacentHTML('afterbegin', `<p class="bad" style="padding:16px">Erro: ${esc(e.message)}</p>`); });

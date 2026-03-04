const sessionListEl = document.getElementById('session-list');
const chatMessagesEl = document.getElementById('chat-messages');
const messageInputEl = document.getElementById('message-input');
const sendBtnEl = document.getElementById('send-btn');
const newSessionBtnEl = document.getElementById('new-session-btn');

let currentSessionId = '';
let streaming = false;

function makeSessionId() {
  if (window.crypto && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  return `session-${Date.now()}`;
}

function escapeHtml(text) {
  return text
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');
}

function renderMessage(content, role) {
  const div = document.createElement('div');
  div.className = `message ${role}`;
  div.innerHTML = escapeHtml(content);
  chatMessagesEl.appendChild(div);
  chatMessagesEl.scrollTop = chatMessagesEl.scrollHeight;
  return div;
}

async function listSessions() {
  const resp = await fetch('/api/history');
  const data = await resp.json();
  return data.ids || [];
}

async function loadSessionMessages(sessionId) {
  const resp = await fetch(`/api/history?id=${encodeURIComponent(sessionId)}`);
  const data = await resp.json();
  return data.messages || [];
}

function renderSessionList(ids) {
  sessionListEl.innerHTML = '';

  if (ids.length === 0) {
    const empty = document.createElement('div');
    empty.className = 'session-id';
    empty.textContent = '暂无会话';
    sessionListEl.appendChild(empty);
    return;
  }

  ids.forEach((id) => {
    const item = document.createElement('div');
    item.className = `session-item${id === currentSessionId ? ' active' : ''}`;

    const idEl = document.createElement('div');
    idEl.className = 'session-id';
    idEl.textContent = id;
    idEl.onclick = () => selectSession(id);

    const delBtn = document.createElement('button');
    delBtn.className = 'icon-btn';
    delBtn.textContent = '×';
    delBtn.title = '删除会话';
    delBtn.onclick = async (e) => {
      e.stopPropagation();
      await fetch(`/api/history?id=${encodeURIComponent(id)}`, { method: 'DELETE' });
      if (id === currentSessionId) {
        currentSessionId = '';
        chatMessagesEl.innerHTML = '';
      }
      await refreshSessions();
    };

    item.appendChild(idEl);
    item.appendChild(delBtn);
    sessionListEl.appendChild(item);
  });
}

async function refreshSessions() {
  const ids = await listSessions();

  if (!currentSessionId) {
    if (ids.length > 0) {
      currentSessionId = ids[0];
    } else {
      currentSessionId = makeSessionId();
    }
  }

  renderSessionList(ids);
}

async function selectSession(sessionId) {
  currentSessionId = sessionId;
  const msgs = await loadSessionMessages(sessionId);

  chatMessagesEl.innerHTML = '';
  msgs.forEach((msg) => {
    const role = msg.role === 'user' ? 'user' : 'assistant';
    renderMessage(msg.content || '', role);
  });

  await refreshSessions();
}

function setSendingState(isSending) {
  streaming = isSending;
  sendBtnEl.disabled = isSending;
  messageInputEl.disabled = isSending;
}

async function sendMessage() {
  if (streaming) {
    return;
  }

  const content = messageInputEl.value.trim();
  if (!content) {
    return;
  }

  if (!currentSessionId) {
    currentSessionId = makeSessionId();
  }

  renderMessage(content, 'user');
  messageInputEl.value = '';

  const assistantEl = renderMessage('', 'assistant');

  setSendingState(true);

  const url = `/api/chat?id=${encodeURIComponent(currentSessionId)}&message=${encodeURIComponent(content)}`;
  const source = new EventSource(url);

  source.onmessage = (event) => {
    assistantEl.textContent += event.data;
    chatMessagesEl.scrollTop = chatMessagesEl.scrollHeight;
  };

  source.addEventListener('done', async () => {
    source.close();
    setSendingState(false);
    await refreshSessions();
  });

  source.onerror = async () => {
    source.close();
    setSendingState(false);
    await refreshSessions();
  };
}

newSessionBtnEl.addEventListener('click', async () => {
  currentSessionId = makeSessionId();
  chatMessagesEl.innerHTML = '';
  await refreshSessions();
});

sendBtnEl.addEventListener('click', sendMessage);
messageInputEl.addEventListener('keydown', (event) => {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault();
    sendMessage();
  }
});

(async function bootstrap() {
  await refreshSessions();
  if (currentSessionId) {
    const ids = await listSessions();
    if (ids.includes(currentSessionId)) {
      await selectSession(currentSessionId);
    }
  }
})();

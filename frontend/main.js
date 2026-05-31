const API_BASE = 'http://127.0.0.1:8000/api/v1';
const TOKEN_STORAGE_KEY = 'fpt_assistant_token';

let authToken = localStorage.getItem(TOKEN_STORAGE_KEY) || '';
let currentConversationId = '';
let currentUser = null;
let conversations = [];

document.addEventListener('DOMContentLoaded', async () => {
  const chatInput = document.getElementById('chatInput');
  const sendBtn = document.getElementById('sendBtn');
  const welcomeScreen = document.getElementById('welcomeScreen');
  const conversationContainer = document.getElementById('conversationContainer');
  const chatArea = document.getElementById('chatArea');
  const promptCards = document.querySelectorAll('.prompt-card');
  const authOverlay = document.getElementById('authOverlay');
  const authForm = document.getElementById('authForm');
  const authEmail = document.getElementById('authEmail');
  const authName = document.getElementById('authName');
  const authPassword = document.getElementById('authPassword');
  const authStatusText = document.getElementById('authStatusText');
  const authTitle = document.getElementById('authTitle');
  const authSubtitle = document.getElementById('authSubtitle');
  const authSubmitBtn = document.getElementById('authSubmitBtn');
  const authModeBtn = document.getElementById('authModeBtn');
  const nameField = document.getElementById('nameField');
  const newChatBtn = document.getElementById('newChatBtn');
  const historyGroups = document.getElementById('historyGroups');
  const historyEmpty = document.getElementById('historyEmpty');
  const userAvatar = document.getElementById('userAvatar');
  const userName = document.getElementById('userName');
  const userEmail = document.getElementById('userEmail');
  const logoutBtn = document.getElementById('logoutBtn');
  const openSidebarBtn = document.getElementById('openSidebarBtn');
  const closeSidebarBtn = document.getElementById('closeSidebarBtn');
  const sidebar = document.getElementById('sidebar');

  let authMode = 'login';

  setInputEnabled(false);

  if (authToken) {
    setAuthStatus('Restoring your session...');
    const restored = await initializeAuthenticatedApp();
    if (!restored) {
      signOut(false);
    }
  }

  if (!authToken) {
    showAuth();
  }

  authModeBtn.addEventListener('click', () => {
    authMode = authMode === 'login' ? 'register' : 'login';
    updateAuthMode();
  });

  authForm.addEventListener('submit', async (event) => {
    event.preventDefault();
    await handleAuthSubmit();
  });

  logoutBtn.addEventListener('click', () => signOut());

  openSidebarBtn.addEventListener('click', () => sidebar.classList.add('open'));
  closeSidebarBtn.addEventListener('click', () => sidebar.classList.remove('open'));

  chatInput.addEventListener('input', function() {
    this.style.height = 'auto';
    this.style.height = `${this.scrollHeight}px`;
    sendBtn.disabled = this.value.trim().length === 0 || !currentConversationId;
  });

  sendBtn.addEventListener('click', () => sendMessage(chatInput.value));
  chatInput.addEventListener('keydown', (event) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      sendMessage(chatInput.value);
    }
  });

  promptCards.forEach((card) => {
    card.addEventListener('click', () => {
      const text = card.querySelector('.prompt-text').textContent;
      sendMessage(text);
    });
  });

  newChatBtn.addEventListener('click', async () => {
    await startNewConversation();
  });

  async function handleAuthSubmit() {
    const email = authEmail.value.trim();
    const password = authPassword.value;
    const fullName = authName.value.trim();

    if (!email || !password || (authMode === 'register' && !fullName)) {
      setAuthStatus('Please fill in all required fields.', 'error');
      return;
    }

    authSubmitBtn.disabled = true;
    setAuthStatus(authMode === 'login' ? 'Signing in...' : 'Creating account...');

    try {
      if (authMode === 'register') {
        await apiFetch('/auth/register', {
          method: 'POST',
          skipAuth: true,
          body: JSON.stringify({ email, password, full_name: fullName })
        });
      }

      const data = await apiFetch('/auth/login', {
        method: 'POST',
        skipAuth: true,
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: new URLSearchParams({ username: email, password })
      });

      authToken = data.access_token;
      localStorage.setItem(TOKEN_STORAGE_KEY, authToken);
      await initializeAuthenticatedApp();
    } catch (error) {
      setAuthStatus(error.message || 'Could not sign in. Please try again.', 'error');
    } finally {
      authSubmitBtn.disabled = false;
    }
  }

  async function initializeAuthenticatedApp() {
    try {
      currentUser = await apiFetch('/users/me');
      renderUser();
      hideAuth();
      setInputEnabled(true);
      await loadConversations();

      if (conversations.length > 0) {
        await selectConversation(conversations[0].conversation_id);
      } else {
        await startNewConversation();
      }

      return true;
    } catch (error) {
      setAuthStatus(error.message || 'Your session expired. Please sign in again.', 'error');
      return false;
    }
  }

  async function loadConversations() {
    conversations = await apiFetch('/chat/conversations');
    conversations.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
    renderConversationList();
  }

  async function startNewConversation() {
    try {
      const conversation = await apiFetch('/chat/conversations', {
        method: 'POST',
        body: JSON.stringify({})
      });
      conversations = [conversation, ...conversations.filter((item) => item.conversation_id !== conversation.conversation_id)];
      await selectConversation(conversation.conversation_id);
      renderConversationList();
    } catch (error) {
      showInlineError(`Could not create a new session: ${error.message}`);
    }
  }

  async function selectConversation(conversationId) {
    currentConversationId = conversationId;
    conversationContainer.innerHTML = '';
    conversationContainer.classList.remove('hidden');
    welcomeScreen.classList.add('hidden');
    addHistoryLoading();
    sendBtn.disabled = chatInput.value.trim().length === 0;
    renderConversationList();
    sidebar.classList.remove('open');

    try {
      const history = await apiFetch(`/chat/conversations/${conversationId}/history`);
      if (conversationId !== currentConversationId) return;
      renderConversationHistory(history);
    } catch (error) {
      if (conversationId !== currentConversationId) return;
      conversationContainer.innerHTML = '';
      showInlineError(`Could not load this session: ${error.message}`);
    }
  }

  async function sendMessage(text) {
    if (!text || text.trim() === '' || !currentConversationId) return;
    if (!welcomeScreen.classList.contains('hidden')) {
      welcomeScreen.classList.add('hidden');
      conversationContainer.classList.remove('hidden');
    }

    addUserMessage(text);
    chatInput.value = '';
    chatInput.style.height = 'auto';
    sendBtn.disabled = true;
    scrollToBottom();

    await fetchAIResponse(text);
    await loadConversations();
  }

  async function fetchAIResponse(text) {
    const thinkingId = `thinking-${Date.now()}`;
    addThinkingIndicator(thinkingId);

    try {
      await streamAIResponse(
        `/chat/conversations/${currentConversationId}/messages/stream`,
        { content: text },
        thinkingId
      );
    } catch (error) {
      document.getElementById(thinkingId).innerHTML =
        `<div class="message-content" style="color:#B42318">${escapeHTML(error.message || 'Error connecting to server.')}</div>`;
    }
  }

  function handleStreamEvent(elementId, event, onChunk) {
    const data = event.data || {};

    if (event.event === 'chunk') {
      onChunk(data.text || '');
      return;
    }

    if (event.event === 'done') {
      finalizeStreamingAIResponse(elementId, data);
      return;
    }

    if (event.event === 'hitl' || event.event === 'error') {
      renderAIResponse(elementId, data);
    }
  }

  window.confirmAction = async function(btn, confirm) {
    const card = btn.closest('.hitl-card');
    card.innerHTML = `<p style="color:var(--text-secondary)">Processing...</p>`;

    const thinkingId = `thinking-${Date.now()}`;
    addThinkingIndicator(thinkingId);

    try {
      card.style.display = 'none';
      await streamAIResponse(
        `/chat/conversations/${currentConversationId}/confirm/stream`,
        { confirm },
        thinkingId
      );
    } catch (error) {
      document.getElementById(thinkingId).innerHTML =
        `<div class="message-content" style="color:#B42318">${escapeHTML(error.message || 'Error processing action.')}</div>`;
    }
  };

  async function streamAIResponse(path, payload, elementId) {
    let streamedText = '';
    const response = await fetch(`${API_BASE}${path}`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${authToken}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(payload)
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => null);
      throw new Error(errorData?.detail || `Request failed with status ${response.status}`);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        if (!line.trim()) continue;
        const event = JSON.parse(line);
        handleStreamEvent(elementId, event, (chunk) => {
          streamedText += chunk;
          renderStreamingAIResponse(elementId, streamedText);
        });
      }
    }

    if (buffer.trim()) {
      const event = JSON.parse(buffer);
      handleStreamEvent(elementId, event, (chunk) => {
        streamedText += chunk;
        renderStreamingAIResponse(elementId, streamedText);
      });
    }
  }

  async function apiFetch(path, options = {}) {
    const headers = new Headers(options.headers || {});
    const skipAuth = options.skipAuth || false;

    if (!headers.has('Content-Type') && options.body && !(options.body instanceof URLSearchParams)) {
      headers.set('Content-Type', 'application/json');
    }

    if (authToken && !skipAuth) {
      headers.set('Authorization', `Bearer ${authToken}`);
    }

    const response = await fetch(`${API_BASE}${path}`, {
      ...options,
      headers
    });

    let data = null;
    const contentType = response.headers.get('content-type') || '';
    if (contentType.includes('application/json')) {
      data = await response.json();
    }

    if (!response.ok) {
      const detail = data?.detail;
      const message = Array.isArray(detail)
        ? detail.map((item) => item.msg).join(' ')
        : detail || `Request failed with status ${response.status}`;
      throw new Error(message);
    }

    return data;
  }

  function renderConversationList() {
    historyGroups.innerHTML = '';
    historyEmpty.classList.toggle('hidden', conversations.length > 0);

    const groups = conversations.reduce((acc, conversation) => {
      const label = getConversationGroup(conversation.created_at);
      if (!acc[label]) acc[label] = [];
      acc[label].push(conversation);
      return acc;
    }, {});

    Object.entries(groups).forEach(([label, items]) => {
      const group = document.createElement('div');
      group.className = 'history-group';

      const title = document.createElement('h3');
      title.className = 'history-title';
      title.textContent = label;

      const list = document.createElement('ul');
      list.className = 'history-list';

      items.forEach((conversation) => {
        const item = document.createElement('li');
        const button = document.createElement('button');
        button.className = `history-item${conversation.conversation_id === currentConversationId ? ' active' : ''}`;
        button.textContent = conversation.title || 'New Chat';
        button.title = conversation.conversation_id;
        button.addEventListener('click', async () => {
          await selectConversation(conversation.conversation_id);
        });
        item.appendChild(button);
        list.appendChild(item);
      });

      group.append(title, list);
      historyGroups.appendChild(group);
    });
  }

  function renderUser() {
    const name = currentUser?.full_name || currentUser?.email || 'User';
    userAvatar.textContent = name.trim().charAt(0).toUpperCase();
    userName.textContent = name;
    userEmail.textContent = currentUser?.email || '';
  }

  function showAuth() {
    authOverlay.style.display = 'flex';
    updateAuthMode();
    setInputEnabled(false);
  }

  function hideAuth() {
    authOverlay.style.display = 'none';
    authStatusText.textContent = '';
    authStatusText.className = 'auth-status';
  }

  function updateAuthMode() {
    const registering = authMode === 'register';
    authTitle.textContent = registering ? 'Create your account' : 'Sign in to FPT Assistant';
    authSubtitle.textContent = registering
      ? 'Create an account, then start real chat sessions tied to your user.'
      : 'Use your account to load your real chat sessions.';
    authSubmitBtn.textContent = registering ? 'Create account' : 'Sign in';
    authModeBtn.textContent = registering ? 'I already have an account' : 'Create an account';
    nameField.classList.toggle('hidden', !registering);
    authName.required = registering;
    authPassword.autocomplete = registering ? 'new-password' : 'current-password';
    setAuthStatus('');
  }

  function setAuthStatus(message, type = '') {
    authStatusText.textContent = message;
    authStatusText.className = `auth-status${type ? ` ${type}` : ''}`;
  }

  function signOut(showOverlay = true) {
    authToken = '';
    currentConversationId = '';
    currentUser = null;
    conversations = [];
    localStorage.removeItem(TOKEN_STORAGE_KEY);
    conversationContainer.innerHTML = '';
    conversationContainer.classList.add('hidden');
    welcomeScreen.classList.remove('hidden');
    renderConversationList();
    userAvatar.textContent = 'U';
    userName.textContent = 'Signed out';
    userEmail.textContent = 'Please sign in';
    setInputEnabled(false);

    if (showOverlay) {
      showAuth();
    }
  }

  function setInputEnabled(enabled) {
    chatInput.disabled = !enabled;
    sendBtn.disabled = !enabled || chatInput.value.trim().length === 0 || !currentConversationId;
    promptCards.forEach((card) => {
      card.disabled = !enabled;
    });
    newChatBtn.disabled = !enabled;
  }

  function showInlineError(text) {
    conversationContainer.classList.remove('hidden');
    welcomeScreen.classList.add('hidden');
    const msgDiv = document.createElement('div');
    msgDiv.className = 'message ai';
    msgDiv.innerHTML = `
      <div class="message-avatar">AI</div>
      <div class="message-content" style="color:#B42318">${escapeHTML(text)}</div>
    `;
    conversationContainer.appendChild(msgDiv);
  }

  function addHistoryLoading() {
    const msgDiv = document.createElement('div');
    msgDiv.className = 'message ai';
    msgDiv.innerHTML = `
      <div class="message-avatar">AI</div>
      <div class="message-content"><div class="thinking-indicator"><span>Loading session</span><span class="thinking-dots"><span></span><span></span><span></span></span></div></div>
    `;
    conversationContainer.appendChild(msgDiv);
  }

  function renderConversationHistory(history) {
    conversationContainer.innerHTML = '';

    if (!history.messages || history.messages.length === 0) {
      conversationContainer.classList.add('hidden');
      welcomeScreen.classList.remove('hidden');
      scrollToBottom();
      return;
    }

    conversationContainer.classList.remove('hidden');
    welcomeScreen.classList.add('hidden');

    history.messages.forEach((message, index) => {
      if (message.role === 'user') {
        addUserMessage(message.content);
        return;
      }

      const isLast = index === history.messages.length - 1;
      addAssistantMessage(message.content, {
        status: isLast ? history.status : 'success',
        tool_calls: isLast ? history.tool_calls : null
      });
    });

    scrollToBottom();
  }

  function addUserMessage(text) {
    const msgDiv = document.createElement('div');
    msgDiv.className = 'message user';
    msgDiv.innerHTML = `
      <div class="message-avatar">${escapeHTML((currentUser?.full_name || currentUser?.email || 'U').charAt(0).toUpperCase())}</div>
      <div class="message-content">${escapeHTML(text)}</div>
    `;
    conversationContainer.appendChild(msgDiv);
  }

  function addAssistantMessage(markdown, meta = {}) {
    const msgDiv = document.createElement('div');
    const id = `history-${Date.now()}-${Math.random().toString(16).slice(2)}`;
    msgDiv.className = 'message ai';
    msgDiv.id = id;
    msgDiv.innerHTML = `
      <div class="message-avatar"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path></svg></div>
      <div class="message-content"></div>
    `;
    conversationContainer.appendChild(msgDiv);
    renderAIResponse(id, {
      response: markdown,
      status: meta.status || 'success',
      tool_calls: meta.tool_calls || null
    });
  }

  function addThinkingIndicator(id) {
    const msgDiv = document.createElement('div');
    msgDiv.className = 'message ai';
    msgDiv.id = id;
    msgDiv.innerHTML = `
      <div class="message-avatar"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path></svg></div>
      <div class="message-content"><div class="thinking-indicator"><span>Thinking</span><span class="thinking-dots"><span></span><span></span><span></span></span></div></div>
    `;
    conversationContainer.appendChild(msgDiv);
    scrollToBottom();
  }

  function renderAIResponse(elementId, apiData) {
    const thinkingEl = document.getElementById(elementId);
    if (!thinkingEl) return;

    const rawMarkdown = apiData.response || '';
    const dirtyHTML = marked.parse(rawMarkdown);
    const safeHTML = DOMPurify.sanitize(dirtyHTML, { ADD_ATTR: ['target'] });

    let html = `<div class="md-body">${safeHTML}</div>`;

    if (apiData.status === 'pending_confirmation' || apiData.status === 'requires_confirmation' || apiData.status === 'interrupted') {
      let toolName = 'Action Required';
      if (apiData.tool_calls && apiData.tool_calls.length > 0) {
        toolName = apiData.tool_calls[0].name || toolName;
      }
      html += `
        <div class="hitl-card">
          <div class="hitl-title">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path><line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>
            Pending: ${escapeHTML(toolName)}
          </div>
          <p style="font-size: 13px; color: var(--text-secondary); margin-bottom: 12px;">The AI is about to execute this action. Do you approve?</p>
          <div class="hitl-actions">
            <button class="hitl-btn confirm" onclick="window.confirmAction(this, true)">Approve</button>
            <button class="hitl-btn cancel" onclick="window.confirmAction(this, false)">Reject</button>
          </div>
        </div>
      `;
    }

    thinkingEl.querySelector('.message-content').innerHTML = html;
    thinkingEl.querySelectorAll('.md-body a').forEach((anchor) => {
      anchor.target = '_blank';
      anchor.rel = 'noopener noreferrer';
    });

    if (apiData.from_cache) {
      const badge = document.createElement('div');
      badge.className = 'cache-badge';
      badge.innerHTML = 'Instant - from semantic cache';
      thinkingEl.querySelector('.message-content').appendChild(badge);
    }
    scrollToBottom();
  }

  function renderStreamingAIResponse(elementId, rawMarkdown) {
    const thinkingEl = document.getElementById(elementId);
    if (!thinkingEl) return;

    const dirtyHTML = marked.parse(rawMarkdown || '');
    const safeHTML = DOMPurify.sanitize(dirtyHTML, { ADD_ATTR: ['target'] });
    thinkingEl.querySelector('.message-content').innerHTML =
      `<div class="md-body">${safeHTML}<span class="streaming-cursor"></span></div>`;
    scrollToBottom();
  }

  function finalizeStreamingAIResponse(elementId, apiData) {
    const thinkingEl = document.getElementById(elementId);
    if (!thinkingEl) return;

    const cursor = thinkingEl.querySelector('.streaming-cursor');
    if (cursor) cursor.remove();

    thinkingEl.querySelectorAll('.md-body a').forEach((anchor) => {
      anchor.target = '_blank';
      anchor.rel = 'noopener noreferrer';
    });

    if (apiData.from_cache) {
      const badge = document.createElement('div');
      badge.className = 'cache-badge';
      badge.innerHTML = 'Instant - from semantic cache';
      thinkingEl.querySelector('.message-content').appendChild(badge);
    }

    scrollToBottom();
  }

  function getConversationGroup(createdAt) {
    const created = new Date(createdAt);
    const today = new Date();
    const createdDay = new Date(created.getFullYear(), created.getMonth(), created.getDate());
    const todayDay = new Date(today.getFullYear(), today.getMonth(), today.getDate());
    const diffDays = Math.round((todayDay - createdDay) / 86400000);

    if (diffDays === 0) return 'Today';
    if (diffDays <= 7) return 'Previous 7 Days';
    return 'Older';
  }

  function escapeHTML(str) {
    if (!str) return '';
    return String(str).replace(/[&<>'"]/g,
      (tag) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[tag] || tag)
    );
  }

  function scrollToBottom() {
    chatArea.scrollTop = chatArea.scrollHeight;
  }
});

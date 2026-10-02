const form = document.querySelector('#chat-form');
const questionInput = document.querySelector('#question');
const cropInput = document.querySelector('#crop');
const messages = document.querySelector('#messages');
const errorMessage = document.querySelector('#error-message');
const sendButton = document.querySelector('.send-button');
const imageInput = document.querySelector('#image-input');
const imagePreview = document.querySelector('#image-preview');
const previewImage = document.querySelector('#preview-image');
const imageName = document.querySelector('#image-name');
const imageStatus = document.querySelector('#image-status');
const analyzeImageButton = document.querySelector('#analyze-image');
const removeImageButton = document.querySelector('#remove-image');
let previewUrl = null;

function clearImageSelection() {
  if (previewUrl) URL.revokeObjectURL(previewUrl);
  previewUrl = null;
  imageInput.value = '';
  imagePreview.hidden = true;
  previewImage.removeAttribute('src');
  imageName.textContent = '';
  imageStatus.textContent = '';
}

async function analyzeImage(file) {
  const formData = new FormData();
  formData.append('file', file);
  analyzeImageButton.disabled = true;
  imageStatus.textContent = 'Analyse YOLOv8 en cours...';

  const response = await fetch('/diagnostic/image', {
    method: 'POST',
    body: formData,
  });
  let payload;
  try {
    payload = await response.json();
  } catch {
    throw new Error('Le serveur a renvoyé une réponse inattendue.');
  }
  if (!response.ok) throw new Error(payload.detail || 'Analyse impossible.');

  imageStatus.textContent = `Diagnostic : ${payload.disease} (${Math.round(payload.confidence * 100)} %) `;
  addMessage('assistant', payload.advice, {
    sources: payload.sources,
    usedLlm: payload.used_llm,
  });
}

function addMessage(role, text, metadata = {}) {
  const article = document.createElement('article');
  article.className = `message ${role === 'user' ? 'user-message' : 'assistant-message'}`;

  const avatar = document.createElement('div');
  avatar.className = 'avatar';
  avatar.textContent = role === 'user' ? 'V' : 'A';

  const content = document.createElement('div');
  content.className = 'message-content';

  const label = document.createElement('span');
  label.className = 'message-label';
  label.innerHTML = `${role === 'user' ? 'Vous' : 'AgriAI'} <time>à l'instant</time>`;

  const paragraph = document.createElement('p');
  paragraph.textContent = text;
  content.append(label, paragraph);

  if (metadata.sources?.length) {
    const sources = document.createElement('div');
    sources.className = 'sources';
    metadata.sources.forEach((source) => {
      const chip = document.createElement('span');
      chip.className = 'source-chip';
      chip.textContent = source.source || 'Document RAG';
      sources.appendChild(chip);
    });
    content.appendChild(sources);
  }

  if (role !== 'user' && metadata.usedLlm !== undefined) {
    const note = document.createElement('span');
    note.className = 'llm-note';
    note.textContent = metadata.usedLlm
      ? 'Réponse enrichie par Gemini'
      : 'Réponse issue directement des passages RAG';
    content.appendChild(note);
  }

  if (role === 'user') {
    article.append(content, avatar);
  } else {
    article.append(avatar, content);
  }
  messages.appendChild(article);
  messages.scrollTop = messages.scrollHeight;
}

function showTyping() {
  const article = document.createElement('article');
  article.className = 'message assistant-message';
  article.id = 'typing-message';
  article.innerHTML = '<div class="avatar">A</div><div class="typing" aria-label="AgriAI rédige une réponse"><span></span><span></span><span></span></div>';
  messages.appendChild(article);
  messages.scrollTop = messages.scrollHeight;
}

function setLoading(isLoading) {
  sendButton.disabled = isLoading;
  questionInput.disabled = isLoading;
  cropInput.disabled = isLoading;
}

async function askQuestion(question, crop) {
  const response = await fetch('/ask', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question, crop: crop || null }),
  });

  let payload;
  try {
    payload = await response.json();
  } catch {
    throw new Error('Le serveur a renvoyé une réponse inattendue.');
  }

  if (!response.ok) {
    throw new Error(payload.detail || 'Impossible de contacter le chatbot.');
  }
  return payload;
}

async function submitQuestion(question) {
  const crop = cropInput.value;
  errorMessage.hidden = true;
  addMessage('user', question);
  showTyping();
  setLoading(true);

  try {
    const result = await askQuestion(question, crop);
    document.querySelector('#typing-message')?.remove();
    addMessage('assistant', result.answer, {
      sources: result.sources,
      usedLlm: result.used_llm,
    });
  } catch (error) {
    document.querySelector('#typing-message')?.remove();
    errorMessage.textContent = error.message;
    errorMessage.hidden = false;
  } finally {
    setLoading(false);
    questionInput.focus();
  }
}

form.addEventListener('submit', (event) => {
  event.preventDefault();
  const question = questionInput.value.trim();
  if (!question) return;
  questionInput.value = '';
  questionInput.style.height = 'auto';
  submitQuestion(question);
});

imageInput.addEventListener('change', async () => {
  const file = imageInput.files[0];
  if (!file) return;

  if (previewUrl) URL.revokeObjectURL(previewUrl);
  previewUrl = URL.createObjectURL(file);
  previewImage.src = previewUrl;
  imageName.textContent = file.name;
  imageStatus.textContent = 'Image prête à être analysée';
  imagePreview.hidden = false;
});

removeImageButton.addEventListener('click', clearImageSelection);

analyzeImageButton.addEventListener('click', async () => {
  const file = imageInput.files[0];
  if (!file) return;

  try {
    await analyzeImage(file);
  } catch (error) {
    imageStatus.textContent = error.message;
  } finally {
    analyzeImageButton.disabled = false;
  }
});

questionInput.addEventListener('keydown', (event) => {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault();
    form.requestSubmit();
  }
});

questionInput.addEventListener('input', () => {
  questionInput.style.height = 'auto';
  questionInput.style.height = `${Math.min(questionInput.scrollHeight, 130)}px`;
});

document.querySelectorAll('.suggestion').forEach((button) => {
  button.addEventListener('click', () => {
    cropInput.value = button.dataset.crop || '';
    questionInput.value = button.dataset.question;
    form.requestSubmit();
  });
});

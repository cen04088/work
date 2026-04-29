let history = [];  // [{role, content}]

async function sendMessage(userText) {
  if (!userText.trim()) return;
  
  appendBubble(userText, "user");
  showLoading();
  
  const currentMessage = userText;
  
  try {
    const res = await fetch("/chatbot/api/", {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-CSRFToken": getCsrfToken() },
      body: JSON.stringify({ message: currentMessage, history: history.slice(-10) }),
    });
    const data = await res.json();
    hideLoading();
    
    if (data.status === "ok") {
        appendBubble(data.reply, "bot");
        history.push({ role: "user", parts: [{ text: currentMessage }] });
        history.push({ role: "model", parts: [{ text: data.reply }] });
    } else {
        appendBubble(data.reply || "오류가 발생했습니다. 다시 시도해주세요.", "bot");
    }
  } catch (e) {
    hideLoading();
    appendBubble("연결이 끊겼습니다. 잠시 후 다시 시도해주세요.", "bot");
  }
}

function appendBubble(text, role) {
  const wrap = document.getElementById("chat-wrap");
  if (!wrap) return;
  const div = document.createElement("div");
  div.className = `bubble ${role}`;
  div.textContent = text;
  wrap.appendChild(div);
  // 스크롤을 최신 메시지로
  setTimeout(() => { wrap.scrollTop = wrap.scrollHeight; }, 50);
}

function showLoading() {
    const wrap = document.getElementById("chat-wrap");
    if (!wrap) return;
    const div = document.createElement("div");
    div.id = "loading-bubble";
    div.className = "bubble bot";
    div.innerHTML = `
      <div class="typing-dots">
        <span></span><span></span><span></span>
      </div>`;
    wrap.appendChild(div);
    setTimeout(() => { wrap.scrollTop = wrap.scrollHeight; }, 50);
}

function hideLoading() {
    const el = document.getElementById("loading-bubble");
    if (el) el.remove();
}

function getCsrfToken() {
  const el = document.querySelector("[name=csrfmiddlewaretoken]");
  return el ? el.value : "";
}

// 음성 입력 (STT)
function startVoiceInput() {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) {
    alert("이 기기에서는 음성 입력이 지원되지 않습니다.");
    return;
  }
  const btn = document.getElementById("voiceBtn");
  const recognition = new SpeechRecognition();
  recognition.lang = "ko-KR";

  recognition.onstart = () => {
    if (btn) btn.style.background = 'rgba(192, 57, 43, 0.12)';
    if (btn) btn.style.borderColor = 'rgba(192, 57, 43, 0.4)';
    if (btn) btn.style.color = '#C0392B';
  };
  recognition.onend = () => {
    if (btn) btn.style.background = '';
    if (btn) btn.style.borderColor = '';
    if (btn) btn.style.color = '';
  };
  recognition.onresult = e => {
    const text = e.results[0][0].transcript;
    const inputEl = document.getElementById("chat-input");
    if (inputEl) {
      inputEl.value = text;
      inputEl.focus();
    }
  };
  recognition.onerror = () => {
    if (btn) btn.textContent = "🎤";
    alert("음성 인식에 실패했습니다. 다시 시도해주세요.");
  };
  recognition.start();
}

/* Universal Live AI Assistant Chatbot Widget Handler */

document.addEventListener("DOMContentLoaded", function() {
  const toggleBtn = document.getElementById("chatbot-toggle");
  const windowEl = document.getElementById("chatbot-window");
  const closeBtn = document.getElementById("chatbot-close");
  const sendBtn = document.getElementById("chatbot-send");
  const inputEl = document.getElementById("chatbot-input");
  const bodyEl = document.getElementById("chatbot-messages");
  const widgetEl = document.getElementById("chatbot-widget");

  if (!toggleBtn || !windowEl) return;

  function openChatbot() {
    windowEl.classList.remove("hidden");
    windowEl.style.display = "flex";
    inputEl.focus();
  }

  function closeChatbot() {
    windowEl.classList.add("hidden");
    windowEl.style.display = "none";
  }

  toggleBtn.addEventListener("click", (e) => {
    e.stopPropagation();
    if (windowEl.classList.contains("hidden") || windowEl.style.display === "none") {
      openChatbot();
    } else {
      closeChatbot();
    }
  });

  if (closeBtn) {
    closeBtn.addEventListener("click", (e) => {
      e.preventDefault();
      e.stopPropagation();
      closeChatbot();
    });
  }

  // Close when clicking outside chatbot widget
  document.addEventListener("click", (e) => {
    if (widgetEl && !widgetEl.contains(e.target)) {
      closeChatbot();
    }
  });

  // Close on Escape key press
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      closeChatbot();
    }
  });

  function appendMessage(text, sender) {
    const msgDiv = document.createElement("div");
    msgDiv.className = `chat-msg ${sender}`;
    msgDiv.innerHTML = text;
    bodyEl.appendChild(msgDiv);
    bodyEl.scrollTop = bodyEl.scrollHeight;
  }

  async function submitQuery(promptText) {
    if (!promptText.trim()) return;
    
    appendMessage(promptText, "user");
    inputEl.value = "";

    try {
      const res = await fetch("/api/ai/chatbot", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt: promptText })
      });
      const data = await res.json();
      if (data.response) {
        appendMessage(data.response, "bot");
      } else {
        appendMessage("Sorry, I encountered an issue fetching AI insights.", "bot");
      }
    } catch (e) {
      appendMessage("Error communicating with Effutu AI Assistant.", "bot");
    }
  }

  sendBtn.addEventListener("click", () => {
    submitQuery(inputEl.value);
  });

  inputEl.addEventListener("keypress", (e) => {
    if (e.key === "Enter") {
      submitQuery(inputEl.value);
    }
  });

  // Quick Action Buttons inside chatbot & sidebar
  document.addEventListener("click", (e) => {
    const btn = e.target.closest(".quick-ai-btn");
    if (btn) {
      const query = btn.dataset.query;
      openChatbot();
      submitQuery(query);
    }
  });
});

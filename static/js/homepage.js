// Smooth scrolling for navigation links
document.querySelectorAll('a[href^="#"]').forEach((anchor) => {
  anchor.addEventListener("click", function (e) {
    e.preventDefault();
    const target = document.querySelector(this.getAttribute("href"));
    if (target) {
      target.scrollIntoView({
        behavior: "smooth",
        block: "start",
      });
    }
  });
});

// Chatbot functionality
const chatbotButton = document.getElementById("chatbot-button");
const chatbotPopup = document.getElementById("chatbot-popup");
const cancelChatbot = document.getElementById("cancel-chatbot");
const chat = document.getElementById("chat");
const form = document.getElementById("askForm");
const input = document.getElementById("question");
const sendBtn = document.getElementById("send-btn");

chatbotButton.addEventListener("click", function () {
  chatbotPopup.classList.remove("hidden");
  setTimeout(() => {
    chatbotPopup.classList.remove("scale-0");
    chatbotPopup.classList.add("scale-100");
  }, 10);
});

cancelChatbot.addEventListener("click", function () {
  chatbotPopup.classList.add("scale-0");
  setTimeout(() => {
    chatbotPopup.classList.add("hidden");
  }, 300);
});

// Close popup when clicking outside
document.addEventListener("click", function (event) {
  if (
    !chatbotButton.contains(event.target) &&
    !chatbotPopup.contains(event.target)
  ) {
    chatbotPopup.classList.add("scale-0");
    setTimeout(() => {
      chatbotPopup.classList.add("hidden");
    }, 300);
  }
});

function appendMessage(role, text, isHtml = false) {
  const wrap = document.createElement("div");
  wrap.className = role === "user" ? "text-right" : "text-left";

  const bubble = document.createElement("div");
  bubble.className =
    role === "user"
      ? "inline-block bg-blue-600 text-white p-3 rounded-lg max-w-[80%] text-sm"
      : "inline-block bg-gray-100 border p-3 rounded-lg max-w-[80%] text-sm";

  if (isHtml) {
    bubble.innerHTML = text.replace(/\n/g, "<br>");
  } else {
    bubble.textContent = text;
  }

  wrap.appendChild(bubble);
  chat.appendChild(wrap);
  chat.scrollTop = chat.scrollHeight;
}

function setLoading(isLoading) {
  if (isLoading) {
    sendBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
    sendBtn.disabled = true;
  } else {
    sendBtn.innerHTML = '<i class="fas fa-paper-plane"></i>';
    sendBtn.disabled = false;
  }
}

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  const q = input.value.trim();
  if (!q) return;

  appendMessage("user", q);
  input.value = "";
  appendMessage("assistant", "🤖 Generating answer...");
  setLoading(true);

  try {
    const res = await fetch("/api/query", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question: q }),
    });

    const data = await res.json();

    // Remove loading message
    chat.removeChild(chat.lastChild);

    if (data.error) {
      appendMessage("assistant", `❌ Error: ${data.error}`);
    } else {
      appendMessage("assistant", data.answer || "No answer provided.");

      //if (data.sources && data.sources.length) {
      // const sourcesHtml = data.sources.filter(Boolean).join(", ");
      // appendMessage("assistant", "📚 Sources: " + sourcesHtml, true);
      //}
    }
  } catch (err) {
    // Remove loading message
    chat.removeChild(chat.lastChild);
    appendMessage("assistant", `❌ Failed to get answer: ${err.message}`);
  } finally {
    setLoading(false);
  }
});

// Auto-focus input when popup is opened
chatbotButton.addEventListener("click", () => {
  setTimeout(() => {
    input.focus();
  }, 350);
});

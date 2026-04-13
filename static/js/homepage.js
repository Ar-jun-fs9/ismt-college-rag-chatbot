// Smooth scrolling for navigation links
document.querySelectorAll('a[href^="#"]').forEach((anchor) => {
  anchor.addEventListener("click", function (e) {
    e.preventDefault();
    const target = document.querySelector(this.getAttribute("href"));
    if (target) {
      target.scrollIntoView({ behavior: "smooth", block: "start" });
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

// Open chatbot popup
chatbotButton.addEventListener("click", () => {
  chatbotPopup.classList.remove("hidden");
  // Add body class on mobile to prevent scrolling
  if (window.innerWidth <= 640) {
    document.body.classList.add("chatbot-open");
  }
  setTimeout(() => {
    chatbotPopup.classList.remove("scale-0");
    chatbotPopup.classList.add("scale-100");
    input.focus();
  }, 10);
});

// Close chatbot popup
cancelChatbot.addEventListener("click", () => {
  chatbotPopup.classList.add("scale-0");
  document.body.classList.remove("chatbot-open");
  setTimeout(() => {
    chatbotPopup.classList.add("hidden");
  }, 300);
});

// Close popup when clicking outside
document.addEventListener("click", (event) => {
  if (!chatbotButton.contains(event.target) && !chatbotPopup.contains(event.target)) {
    chatbotPopup.classList.add("scale-0");
    document.body.classList.remove("chatbot-open");
    setTimeout(() => chatbotPopup.classList.add("hidden"), 300);
  }
});

// Close on escape key
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && !chatbotPopup.classList.contains("hidden")) {
    chatbotPopup.classList.add("scale-0");
    document.body.classList.remove("chatbot-open");
    setTimeout(() => chatbotPopup.classList.add("hidden"), 300);
  }
});

// Handle window resize to reset body class
window.addEventListener("resize", () => {
  if (window.innerWidth > 640) {
    document.body.classList.remove("chatbot-open");
  }
});

// Append messages to chat
function appendMessage(role, text, isHtml = false) {
  const wrap = document.createElement("div");
  wrap.className = role === "user" ? "text-right" : "text-left";

  const bubble = document.createElement("div");
  const isMobile = window.innerWidth <= 640;
  bubble.className =
    role === "user"
      ? "inline-block bg-blue-600 text-white p-2 sm:p-3 rounded-lg max-w-[85%] sm:max-w-[80%] text-xs sm:text-sm"
      : "inline-block bg-gray-100 border p-2 sm:p-3 rounded-lg max-w-[85%] sm:max-w-[80%] text-xs sm:text-sm";

  if (isHtml) bubble.innerHTML = text.replace(/\n/g, "<br>");
  else bubble.textContent = text;

  wrap.appendChild(bubble);
  chat.appendChild(wrap);
  chat.scrollTop = chat.scrollHeight;
}

// Set loading button state
function setLoading(isLoading) {
  if (isLoading) {
    sendBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
    sendBtn.disabled = true;
  } else {
    sendBtn.innerHTML = '<i class="fas fa-paper-plane"></i>';
    sendBtn.disabled = false;
  }
}

// Create inline typing indicator with text
function createTypingIndicator() {
  const wrap = document.createElement("div");
  wrap.className = "text-left";

  // Add text with animated dots using JavaScript for precise control
  wrap.innerHTML = `
    <span class="typing-text">AI is typing</span><span class="typing-dots"><span class="dot">.</span><span class="dot">.</span><span class="dot">.</span></span>
  `;

  chat.appendChild(wrap);
  chat.scrollTop = chat.scrollHeight;

  // Animate dots using JavaScript for precise control
  const dots = wrap.querySelectorAll('.typing-dots .dot');
  let dotCount = 0;
  
  const interval = setInterval(() => {
    // Show dots based on count (1, 2, or 3)
    dots.forEach((dot, index) => {
      dot.style.opacity = index < dotCount ? '1' : '0';
    });
    
    // Cycle: 1 -> 2 -> 3 -> 0 -> repeat
    dotCount = (dotCount + 1) % 4;
  }, 400); // Change every 400ms

  // Store interval ID for cleanup
  wrap.dataset.intervalId = interval;

  return wrap; // return element to remove later
}

// Handle form submission
form.addEventListener("submit", async (e) => {
  e.preventDefault();
  const q = input.value.trim();
  if (!q) return;

  appendMessage("user", q);
  input.value = "";

  // Show typing indicator
  const typingIndicator = createTypingIndicator();
  setLoading(true);

  try {
    const res = await fetch("/api/query", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question: q }),
    });

    const data = await res.json();

    // Remove typing indicator and stop animation
    const intervalId = typingIndicator.dataset.intervalId;
    if (intervalId) clearInterval(parseInt(intervalId));
    chat.removeChild(typingIndicator);

    if (data.error) appendMessage("assistant", `❌ Error: ${data.error}`);
    else appendMessage("assistant", data.answer || "No answer provided.");
  } catch (err) {
    const intervalId = typingIndicator.dataset.intervalId;
    if (intervalId) clearInterval(parseInt(intervalId));
    chat.removeChild(typingIndicator);
    appendMessage("assistant", `❌ Failed to get answer: ${err.message}`);
  } finally {
    setLoading(false);
  }
});

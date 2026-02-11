const resumeFile = document.getElementById("resumeFile");
const uploadStatus = document.getElementById("uploadStatus");
const uploadedList = document.getElementById("uploadedList");

async function uploadResume() {
  const files = resumeFile.files;
  if (!files.length) return alert("Select at least one file.");
  const form = new FormData();
  for (const f of files) form.append("resumes", f);

  const res = await fetch("/upload", { method: "POST", body: form });
  const data = await res.json();
  uploadStatus.innerText = data.message;

  uploadedList.innerHTML = '';
  for (const f of files) {
    const li = document.createElement("li");
    li.innerText = f.name;
    uploadedList.appendChild(li);
  }
}

document.getElementById('uploadForm').addEventListener('submit', e => {
  e.preventDefault();
  uploadResume();
});

const jdInput = document.getElementById("jdInput");
const submitJD = document.getElementById("submitJD");
const miniWindow = document.getElementById("miniChatWindow");
const miniInput = document.getElementById("miniUserInput");
const miniSend = document.getElementById("miniSend");

function addMiniMessage(html, sender) {
  const msg = document.createElement("div");
  msg.className = "message " + sender;
  msg.innerHTML = html;
  miniWindow.appendChild(msg);
  miniWindow.scrollTop = miniWindow.scrollHeight;
}

submitJD.addEventListener('click', async () => {
  const jdText = jdInput.value.trim();
  if (!jdText) return alert("Please enter a job description.");

  try {
    const res = await fetch("/chatbot", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question: jdText, mode: "match_resumes" })
    });

    const data = await res.json();

    if (data.matches && data.matches.length) {
      const [best, ...others] = data.matches;

      const nameLine = best.extract.match(/Name\s*:\s*(.+)/i);
      const displayName = nameLine ? nameLine[1].trim() : best.filename;

      let html = `
        <div class="selected-box">
          <div class="selected-heading"> Selected Candidate</div>
          <div class="selected-name">${displayName}</div>
          <div class="selected-download"><a href="${best.url}" download>⬇️ Download Resume</a></div>
        </div>

        <div style="margin-top: 2rem; font-weight:bold; color:#00BFFF;">Top Matches:</div>

        <div class="bot-match-item">
          <div class="bot-summary">
            <strong>Extract:</strong>
            <div class="extract-details">${best.extract.replace(/^Extract:\s*/i, '')}</div>
          </div>
          <div class="bot-summary"><strong>Summary:</strong> ${best.summary.replace(/^Summary:\s*/i, '')}</div>
          <div class="bot-summary"><strong>Why Selected:</strong> ${best.reason.replace(/^Why Selected:\s*/i, '')}</div>
        </div>
        <hr>
      `;

      if (others.length) {
        html += `<div style="margin-top:1rem; font-weight:bold; color:#00BFFF;">Other Matches:</div>`;
        html += others.map(m => {
          return `
            <div class="bot-match-item">
              <a href="${m.url}" download class="bot-match">${m.filename}</a>
              <div class="bot-summary">
                <strong>Extract:</strong>
                <div class="extract-details">${m.extract.replace(/^Extract:\s*/i, '')}</div>
              </div>
              <div class="bot-summary"><strong>Summary:</strong> ${m.summary.replace(/^Summary:\s*/i, '')}</div>
              <div class="bot-summary"><strong>Why Selected:</strong> ${m.reason.replace(/^Why Selected:\s*/i, '')}</div>
            </div>
          `;
        }).join('');
      }

      addMiniMessage(html, "bot");

    } else {
      addMiniMessage("<em>No suitable matches found.</em>", "bot");
    }

  } catch (err) {
    console.error("❌ Chat error:", err);
    addMiniMessage("Error contacting chatbot.", "bot");
  }
});

miniSend.addEventListener("click", async () => {
  const text = miniInput.value.trim();
  if (!text) return;
  addMiniMessage(text, "user");
  miniInput.value = "";

  try {
    const res = await fetch("/chatbot", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question: text, mode: "chat" })
    });

    const data = await res.json();
    const reply = data.response || "No response.";
    addMiniMessage(reply, "bot");

  } catch (err) {
    addMiniMessage("Error contacting chatbot.", "bot");
  }
});

const clearBtn = document.getElementById("clearChat");
clearBtn.addEventListener("click", () => {
  miniWindow.innerHTML = "";
});








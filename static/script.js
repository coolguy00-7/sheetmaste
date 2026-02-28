const form = document.getElementById("analyze-form");
const filesInput = document.getElementById("files");
const dropzone = document.getElementById("dropzone");
const fileSummary = document.getElementById("file-summary");
const fileList = document.getElementById("file-list");
const meta = document.getElementById("meta");
const output = document.getElementById("output");
const generateSheetBtn = document.getElementById("generate-sheet-btn");
const sheetMeta = document.getElementById("sheet-meta");
const sheetPage1 = document.getElementById("sheet-page-1");
const sheetPage2 = document.getElementById("sheet-page-2");
const reqEventName = document.getElementById("req-event-name");
const reqDivision = document.getElementById("req-division");
const reqDifficulty = document.getElementById("req-difficulty");
const reqTargetWords = document.getElementById("req-target-words");
const reqRequiredTopics = document.getElementById("req-required-topics");
const reqBannedTopics = document.getElementById("req-banned-topics");
const reqNotes = document.getElementById("req-notes");

const renderFileSelection = () => {
  const files = filesInput.files;
  if (!files || files.length === 0) {
    fileSummary.textContent = "No files selected.";
    fileList.innerHTML = "";
    return;
  }

  fileSummary.textContent = `${files.length} file(s) selected`;
  fileList.innerHTML = "";
  Array.from(files).forEach((file) => {
    const chip = document.createElement("span");
    chip.className = "file-chip";
    chip.textContent = file.name;
    fileList.appendChild(chip);
  });
};

filesInput.addEventListener("change", renderFileSelection);

["dragenter", "dragover"].forEach((eventName) => {
  dropzone.addEventListener(eventName, (event) => {
    event.preventDefault();
    dropzone.classList.add("active");
  });
});

["dragleave", "drop"].forEach((eventName) => {
  dropzone.addEventListener(eventName, (event) => {
    event.preventDefault();
    dropzone.classList.remove("active");
  });
});

dropzone.addEventListener("drop", (event) => {
  const dropped = event.dataTransfer.files;
  if (!dropped || dropped.length === 0) {
    return;
  }

  filesInput.files = dropped;
  renderFileSelection();
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const files = filesInput.files;

  if (!files || files.length === 0) {
    output.textContent = "Please select at least one file.";
    meta.textContent = "";
    return;
  }

  const formData = new FormData();
  Array.from(files).forEach((file) => formData.append("files", file));

  output.textContent = "Loading...";
  meta.textContent = `Uploading ${files.length} file(s)...`;

  try {
    const res = await fetch("/api/analyze-practice", {
      method: "POST",
      body: formData,
    });

    const data = await res.json();
    if (!res.ok) {
      const details =
        typeof data.details === "string"
          ? data.details
          : data.details
            ? JSON.stringify(data.details, null, 2)
            : "";
      output.textContent = details ? `${data.error || "Request failed."}\n\n${details}` : data.error || "Request failed.";
      meta.textContent = "";
      return;
    }

    output.textContent = data.response || "No response text.";
    const modelUsed = data.model_used ? ` using ${data.model_used}` : "";
    meta.textContent = `Analyzed ${data.total_files} file(s)${modelUsed}: ${data.files_analyzed.join(", ")}`;
  } catch (error) {
    output.textContent = `Network error: ${error.message}`;
    meta.textContent = "";
  }
});

const splitSheetText = (text) => {
  const cleaned = text
    .replace(/\n{3,}/g, "\n\n")
    .split("\n")
    .map((line) => line.trimEnd())
    .join("\n")
    .trim();

  const paragraphs = cleaned.split(/\n{2,}/).filter(Boolean);
  if (paragraphs.length <= 1) {
    return [cleaned, ""];
  }

  const totalChars = paragraphs.reduce((sum, p) => sum + p.length, 0);
  const target = Math.floor(totalChars / 2);
  let running = 0;
  let splitIndex = 0;

  for (let i = 0; i < paragraphs.length; i += 1) {
    running += paragraphs[i].length;
    if (running >= target) {
      splitIndex = i + 1;
      break;
    }
  }

  if (splitIndex <= 0 || splitIndex >= paragraphs.length) {
    splitIndex = Math.ceil(paragraphs.length / 2);
  }

  const first = paragraphs.slice(0, splitIndex).join("\n\n").trim();
  const second = paragraphs.slice(splitIndex).join("\n\n").trim();
  return [first, second];
};

generateSheetBtn.addEventListener("click", async () => {
  const analysis = output.textContent.trim();
  if (!analysis || analysis === "No response yet." || analysis === "Loading...") {
    sheetMeta.textContent = "Generate analysis first.";
    return;
  }

  const requirements = {
    event_name: reqEventName.value.trim(),
    division: reqDivision.value.trim(),
    difficulty: reqDifficulty.value,
    target_length_words: Number(reqTargetWords.value) || 2600,
    required_topics: reqRequiredTopics.value.trim(),
    banned_topics: reqBannedTopics.value.trim(),
    notes: reqNotes.value.trim(),
  };

  sheetMeta.textContent = "Generating 2-page reference sheet...";
  sheetPage1.textContent = "Generating...";
  sheetPage2.textContent = "";

  try {
    const res = await fetch("/api/generate-reference-sheet", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ analysis, requirements }),
    });

    const data = await res.json();
    if (!res.ok) {
      const details =
        typeof data.details === "string"
          ? data.details
          : data.details
            ? JSON.stringify(data.details, null, 2)
            : "";
      sheetMeta.textContent = "Sheet generation failed.";
      sheetPage1.textContent = details ? `${data.error || "Request failed."}\n\n${details}` : data.error || "Request failed.";
      sheetPage2.textContent = "";
      return;
    }

    const [pageOne, pageTwo] = splitSheetText(data.reference_sheet || "");
    sheetPage1.textContent = pageOne || "No content generated.";
    sheetPage2.textContent = pageTwo || "No overflow content.";
    const quality = data.quality || {};
    const qualityScore =
      typeof quality.score === "number" || typeof quality.score === "string"
        ? ` | quality score ${quality.score}`
        : "";
    sheetMeta.textContent = `Reference sheet generated using ${data.model_used}${qualityScore}.`;
  } catch (error) {
    sheetMeta.textContent = "Sheet generation failed.";
    sheetPage1.textContent = `Network error: ${error.message}`;
    sheetPage2.textContent = "";
  }
});

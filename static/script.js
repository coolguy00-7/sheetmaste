const form = document.getElementById("analyze-form");
const filesInput = document.getElementById("files");
const dropzone = document.getElementById("dropzone");
const fileSummary = document.getElementById("file-summary");
const fileList = document.getElementById("file-list");
const meta = document.getElementById("meta");
const output = document.getElementById("output");

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

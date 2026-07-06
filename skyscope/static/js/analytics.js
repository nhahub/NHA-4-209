const resultsPanel = document.getElementById("resultsPanel");
const resultsTitle = document.getElementById("resultsTitle");
const resultsHead = document.getElementById("resultsHead");
const resultsBody = document.getElementById("resultsBody");
const resultsLoading = document.getElementById("resultsLoading");
const resultsTableWrap = document.getElementById("resultsTableWrap");

document.querySelectorAll(".btn-run").forEach((btn) => {
  btn.addEventListener("click", async () => {
    const queryId = btn.dataset.queryId;
    const queryTitle = btn.dataset.queryTitle;

    resultsPanel.classList.add("visible");
    resultsTitle.innerHTML = `<i class="fas fa-table me-2 text-primary"></i>${queryTitle}`;
    resultsLoading.classList.remove("d-none");
    resultsTableWrap.classList.add("d-none");
    resultsBody.innerHTML = "";

    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Running...';

    try {
      const res = await fetch(`/api/analytics/${queryId}`);
      const data = await res.json();

      resultsHead.innerHTML = `<tr>${data.columns.map((c) => `<th>${c}</th>`).join("")}</tr>`;
      resultsBody.innerHTML = data.rows
        .map((row) => `<tr>${row.map((cell) => `<td>${cell}</td>`).join("")}</tr>`)
        .join("");
    } catch {
      resultsBody.innerHTML = '<tr><td colspan="99" class="text-center text-danger py-4">Query failed.</td></tr>';
    }

    resultsLoading.classList.add("d-none");
    resultsTableWrap.classList.remove("d-none");
    btn.disabled = false;
    btn.innerHTML = '<i class="fas fa-play me-1"></i>Run Query';

    resultsPanel.scrollIntoView({ behavior: "smooth", block: "start" });
  });
});

document.getElementById("closeResults").addEventListener("click", () => {
  resultsPanel.classList.remove("visible");
});

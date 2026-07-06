let currentPage = 1;
const pageSize = 8;
let sortField = "flight_date";
let sortDir = "desc";
let currentTotal = 0;

const flightsBody = document.getElementById("flightsBody");
const searchInput = document.getElementById("searchInput");
const statusFilter = document.getElementById("statusFilter");
const airlineFilter = document.getElementById("airlineFilter");
const pagination = document.getElementById("pagination");
const tableInfo = document.getElementById("tableInfo");

let searchDebounce;

async function loadAirlines() {
  const res = await fetch("/api/airlines");
  const airlines = await res.json();
  airlineFilter.innerHTML = '<option value="">All Airlines</option>';
  airlines.forEach((a) => {
    airlineFilter.innerHTML += `<option value="${a}">${a}</option>`;
  });
}

async function loadFlights() {
  const params = new URLSearchParams({
    page: currentPage,
    page_size: pageSize,
    search: searchInput.value.trim(),
    status: statusFilter.value,
    airline: airlineFilter.value,
    sort: sortField,
    dir: sortDir,
  });
  const res = await fetch(`/api/flights?${params.toString()}`);
  const data = await res.json();
  currentTotal = data.total;
  renderTable(data.rows);
  renderPagination(data.total);
}

function delayClass(minutes) {
  if (!minutes || minutes <= 0) return "zero";
  if (minutes <= 30) return "low";
  return "high";
}

function renderTable(rows) {
  flightsBody.innerHTML = rows
    .map(
      (f) => `
    <tr>
      <td><strong>${f.Flight_Number_Operating_Airline ?? ""}</strong></td>
      <td>${f.Airline ?? ""}</td>
      <td><span class="badge bg-light text-dark border">${f.Origin ?? ""}</span></td>
      <td><span class="badge bg-light text-dark border">${f.Dest ?? ""}</span></td>
      <td>${f.FlightDate ?? ""}</td>
      <td>${f.CRSDepTime ?? ""}</td>
      <td><span class="delay-value ${delayClass(f.DepDelayMinutes)}">${f.DepDelayMinutes ?? 0} min</span></td>
      <td><span class="delay-value ${delayClass(f.ArrDelay)}">${f.ArrDelay ?? 0} min</span></td>
      <td>
        <span class="status-badge ${f.FlightStatus === "Completed" ? "on-time" : "delayed"}">
          <i class="fas fa-${f.FlightStatus === "Completed" ? "check" : "clock"}"></i>${f.FlightStatus ?? ""}
        </span>
      </td>
      ${
        window.IS_ADMIN
          ? `<td>
          <button class="btn btn-sm btn-outline-primary edit-btn" data-id="${f.id}">
            <i class="fas fa-edit"></i>
          </button>
          <button class="btn btn-sm btn-outline-danger delete-btn" data-id="${f.id}">
            <i class="fas fa-trash"></i>
          </button>
        </td>`
          : ""
      }
    </tr>`
    )
    .join("");

  const start = rows.length ? (currentPage - 1) * pageSize + 1 : 0;
  const end = (currentPage - 1) * pageSize + rows.length;
  tableInfo.textContent = currentTotal
    ? `Showing ${start}–${end} of ${currentTotal} flights`
    : "No flights found";
}

function renderPagination(total) {
  const pages = Math.ceil(total / pageSize) || 1;
  let html = "";

  html += `<li class="page-item ${currentPage === 1 ? "disabled" : ""}">
    <a class="page-link" href="#" data-page="${currentPage - 1}"><i class="fas fa-chevron-left"></i></a></li>`;

  const windowSize = 5;
  let startP = Math.max(1, currentPage - Math.floor(windowSize / 2));
  let endP = Math.min(pages, startP + windowSize - 1);
  startP = Math.max(1, endP - windowSize + 1);

  for (let i = startP; i <= endP; i++) {
    html += `<li class="page-item ${i === currentPage ? "active" : ""}">
      <a class="page-link" href="#" data-page="${i}">${i}</a></li>`;
  }

  html += `<li class="page-item ${currentPage === pages ? "disabled" : ""}">
    <a class="page-link" href="#" data-page="${currentPage + 1}"><i class="fas fa-chevron-right"></i></a></li>`;

  pagination.innerHTML = html;
}

document.querySelectorAll("#flightsTable thead th[data-sort]").forEach((th) => {
  th.addEventListener("click", () => {
    const field = th.dataset.sort;
    if (sortField === field) {
      sortDir = sortDir === "asc" ? "desc" : "asc";
    } else {
      sortField = field;
      sortDir = "asc";
    }
    document.querySelectorAll("#flightsTable thead th").forEach((h) => h.classList.remove("sorted"));
    th.classList.add("sorted");
    currentPage = 1;
    loadFlights();
  });
});

searchInput.addEventListener("input", () => {
  clearTimeout(searchDebounce);
  searchDebounce = setTimeout(() => {
    currentPage = 1;
    loadFlights();
  }, 400);
});
statusFilter.addEventListener("change", () => {
  currentPage = 1;
  loadFlights();
});
airlineFilter.addEventListener("change", () => {
  currentPage = 1;
  loadFlights();
});

pagination.addEventListener("click", (e) => {
  e.preventDefault();
  const link = e.target.closest("[data-page]");
  if (!link) return;
  const page = parseInt(link.dataset.page);
  const totalPages = Math.ceil(currentTotal / pageSize) || 1;
  if (page >= 1 && page <= totalPages) {
    currentPage = page;
    loadFlights();
  }
});

if (window.IS_ADMIN) {
  const flightModal = new bootstrap.Modal(document.getElementById("flightModal"));
  const flightForm = document.getElementById("flightForm");

  document.getElementById("addFlightBtn").addEventListener("click", () => {
    document.getElementById("flightModalTitle").textContent = "Add Flight";
    document.getElementById("flightId").value = "";
    flightForm.reset();
  });

  document.getElementById("saveFlightBtn").addEventListener("click", async () => {
    const id = document.getElementById("flightId").value;
    const payload = {
      flight_number: document.getElementById("flightNumber").value,
      airline: document.getElementById("airline").value,
      origin: document.getElementById("origin").value,
      destination: document.getElementById("destination").value,
      flight_date: document.getElementById("flightDate").value,
      dep_time: document.getElementById("depTime").value,
      dep_delay: parseInt(document.getElementById("depDelay").value) || 0,
      arr_delay: parseInt(document.getElementById("arrDelay").value) || 0,
      status: document.getElementById("status").value,
    };

    const url = id ? `/api/flights/${id}` : "/api/flights";
    const method = id ? "PUT" : "POST";

    await fetch(url, {
      method,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    flightModal.hide();
    loadFlights();
  });

  flightsBody.addEventListener("click", async (e) => {
    const editBtn = e.target.closest(".edit-btn");
    const deleteBtn = e.target.closest(".delete-btn");

    if (editBtn) {
      const id = editBtn.dataset.id;
      const flight = await (await fetch(`/api/flight/${id}`)).json();
      document.getElementById("flightModalTitle").textContent = "Edit Flight";
      document.getElementById("flightId").value = flight.id;
      document.getElementById("flightNumber").value = flight.Flight_Number_Operating_Airline;
      document.getElementById("airline").value = flight.Airline;
      document.getElementById("origin").value = flight.Origin;
      document.getElementById("destination").value = flight.Dest;
      document.getElementById("flightDate").value = flight.FlightDate;
      document.getElementById("depTime").value = flight.CRSDepTime;
      document.getElementById("depDelay").value = flight.DepDelayMinutes;
      document.getElementById("arrDelay").value = flight.ArrDelay;
      document.getElementById("status").value = flight.FlightStatus;
      flightModal.show();
    }
    if (deleteBtn) {
      if (confirm("Delete this flight?")) {
        await fetch(`/api/flights/${deleteBtn.dataset.id}`, { method: "DELETE" });
        loadFlights();
      }
    }
  });
}

loadAirlines();
loadFlights();
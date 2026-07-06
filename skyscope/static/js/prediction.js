const form = document.getElementById("predictionForm");
const resultCard = document.getElementById("predictionResult");
const placeholder = document.getElementById("predictionPlaceholder");
const resultIcon = document.getElementById("resultIcon");
const resultPrediction = document.getElementById("resultPrediction");
const resultProbability = document.getElementById("resultProbability");
const resultEstimatedDelay = document.getElementById("resultEstimatedDelay");
const probRing = document.getElementById("probRing");
const predDate = document.getElementById("predDate");
const predDayOfWeek = document.getElementById("predDayOfWeek");
const predMonth = document.getElementById("predMonth");

const DAYS_OF_WEEK = [
  "Monday", "Tuesday", "Wednesday", "Thursday",
  "Friday", "Saturday", "Sunday",
];

function parseTime(value) {
  const [hour, minute] = value.split(":").map(Number);
  return { hour, minute };
}

function setDefaultDate() {
  const today = new Date();
  predDate.value = today.toISOString().slice(0, 10);
  syncDateFields();
}

function syncDateFields() {
  if (!predDate.value) return;
  const date = new Date(`${predDate.value}T12:00:00`);
  const weekdayIndex = (date.getDay() + 6) % 7;
  predDayOfWeek.value = String(weekdayIndex + 1);
  predMonth.value = String(date.getMonth() + 1);
}

predDate.addEventListener("change", syncDateFields);
setDefaultDate();

form.addEventListener("submit", async (e) => {
  e.preventDefault();

  const origin = document.getElementById("predOrigin").value;
  const destination = document.getElementById("predDestination").value;

  if (origin === destination) {
    alert("Origin and destination must be different.");
    return;
  }

  const dep = parseTime(document.getElementById("predDepTime").value);
  const arr = parseTime(document.getElementById("predArrTime").value);
  const dayIndex = parseInt(predDayOfWeek.value, 10) - 1;

  const payload = {
    airline: document.getElementById("predAirline").value,
    origin,
    destination,
    departure_hour: dep.hour,
    departure_minute: dep.minute,
    arrival_hour: arr.hour,
    arrival_minute: arr.minute,
    month: parseInt(predMonth.value, 10),
    day_of_week: parseInt(predDayOfWeek.value, 10),
    day_of_week_name: DAYS_OF_WEEK[dayIndex],
    distance: parseInt(document.getElementById("predDistance").value, 10),
  };

  const btn = document.getElementById("predictBtn");
  btn.disabled = true;
  btn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Predicting...';

  try {
    const res = await fetch("/api/predict", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await res.json();

    if (!res.ok) {
      alert(data.error || "Prediction failed.");
      return;
    }

    placeholder.style.display = "none";
    resultCard.classList.add("visible");

    if (data.delayed) {
      resultIcon.className = "prediction-result-icon delayed";
      resultIcon.innerHTML = '<i class="fas fa-exclamation-triangle"></i>';
      resultPrediction.textContent = "Likely Delayed";
      probRing.style.borderColor = "rgba(248, 113, 113, 0.5)";
    } else {
      resultIcon.className = "prediction-result-icon on-time";
      resultIcon.innerHTML = '<i class="fas fa-check-circle"></i>';
      resultPrediction.textContent = "Likely On Time";
      probRing.style.borderColor = "rgba(110, 231, 183, 0.5)";
    }

    resultProbability.textContent = `${data.probability}%`;
    resultEstimatedDelay.textContent = `${data.estimated_delay_minutes} min`;
  } catch {
    alert("Prediction failed. Please try again.");
  }

  btn.disabled = false;
  btn.innerHTML = '<i class="fas fa-magic me-2"></i>Predict Delay';
});

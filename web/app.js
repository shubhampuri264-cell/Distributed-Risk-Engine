const API_URL = "http://127.0.0.1:8000";
let token = localStorage.getItem("risk_engine_token");
let simChart = null;
let stressChart = null;

// --- Initialization ---
document.addEventListener("DOMContentLoaded", () => {
    if (token) {
        showApp();
        updateDashboard(); // Load initial dashboard stats
    }
});

// ... (keep auth functions same) ...

// --- Features ---
// ... (keep ingestData same) ...

async function runSimulation() {
    const ticker = document.getElementById("sim-ticker").value;
    const paths = document.getElementById("sim-paths").value;
    const initial = 100.0;

    // Reset UI
    document.getElementById("sim-results").classList.add("hidden");

    try {
        const res = await fetch(`${API_URL}/simulate`, {
            method: "POST",
            headers: getHeaders(),
            body: JSON.stringify({
                ticker,
                paths: parseInt(paths),
                initial_price: initial,
                days: 252,
                volatility: 0.20,
                drift: 0.05
            })
        });

        if (res.ok) {
            const data = await res.json();
            document.getElementById("res-mean").innerText = "$" + data.mean_price.toFixed(2);
            document.getElementById("res-var").innerText = "$" + data.var_95.toFixed(2);
            document.getElementById("res-cvar").innerText = "$" + data.cvar_95.toFixed(2);
            document.getElementById("sim-results").classList.remove("hidden");

            // Render Chart
            if (data.paths) {
                renderSimulationChart(data.paths);
            }
        } else {
            alert("Simulation Failed");
        }
    } catch (e) {
        console.error(e);
        alert("Error running simulation");
    }
}

async function runStressTest() {
    const ticker = document.getElementById("stress-ticker").value;
    const type = document.getElementById("stress-type").value;
    const shock = parseFloat(document.getElementById("stress-shock").value);
    // Hardcoded initial for demo
    const initialPrice = 100.0;

    try {
        const res = await fetch(`${API_URL}/stress-test`, {
            method: "POST",
            headers: getHeaders(),
            body: JSON.stringify({
                ticker,
                scenario_type: type,
                shock_value: shock,
                initial_price: initialPrice
            })
        });

        if (res.ok) {
            const data = await res.json();
            const out = document.getElementById("stress-results");
            out.innerText = JSON.stringify(data, null, 2);
            out.classList.remove("hidden");

            // Render Chart
            renderStressChart(data, initialPrice);
        }
    } catch (e) {
        console.error(e);
    }
}

// --- Chart Rendering ---
function renderSimulationChart(pathsData) {
    const ctx = document.getElementById('sim-chart').getContext('2d');

    if (simChart) {
        simChart.destroy();
    }

    // Data Preparation: pathsData is List[List[float]] (paths x days)
    // We need datasets for Chart.js.
    // Create labels (days 0 to N)
    const labels = Array.from({ length: pathsData[0].length }, (_, i) => i);

    const datasets = pathsData.map((path, i) => ({
        label: `Path ${i + 1}`,
        data: path,
        borderColor: 'rgba(66, 153, 225, 0.3)', // Light blue transparent
        borderWidth: 1,
        pointRadius: 0, // No points for performance
        fill: false,
        tension: 0.4
    }));

    simChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: datasets
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                title: { display: true, text: 'Monte Carlo Price Paths (First 50)', color: '#a0aec0' }
            },
            scales: {
                x: {
                    grid: { color: 'rgba(255, 255, 255, 0.05)' },
                    ticks: { color: '#718096' }
                },
                y: {
                    grid: { color: 'rgba(255, 255, 255, 0.05)' },
                    ticks: { color: '#718096' }
                }
            },
            interaction: {
                mode: 'nearest',
                axis: 'x',
                intersect: false
            }
        }
    });
}

function renderStressChart(result, initialPrice) {
    const ctx = document.getElementById('stress-chart').getContext('2d');

    if (stressChart) {
        stressChart.destroy();
    }

    let labels = [];
    let data = [];
    let colors = [];
    let title = "";

    if (result.scenario === "Price Shock") {
        title = "Portfolio Value Impact";
        labels = ["Before Shock", "After Shock"];
        data = [initialPrice, result.new_price];
        colors = ['#48bb78', '#e53e3e']; // Green to Red
    } else {
        // Volatility Shock or others
        title = "Risk Metric Change (VaR 99%)";
        labels = ["Normal VaR", "Stressed VaR"];
        // Use real values from API (or 0 if missing)
        const normalVar = result.normal_var_99 || 0;
        data = [normalVar, result.new_var_99];
        colors = ['#4299E1', '#DD6B20']; // Blue to Orange
    }

    stressChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Value',
                data: data,
                backgroundColor: colors,
                borderWidth: 0,
                borderRadius: 6
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                title: { display: true, text: title, color: '#a0aec0' }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    grid: { color: 'rgba(255, 255, 255, 0.05)' },
                    ticks: { color: '#718096' }
                },
                x: {
                    ticks: { color: '#a0aec0' },
                    grid: { display: false }
                }
            }
        }
    });
}

// --- Auth ---
async function login() {
    const username = document.getElementById("username").value;
    const password = document.getElementById("password").value;
    const errorMsg = document.getElementById("login-error");

    errorMsg.innerText = "";

    try {
        const formData = new FormData();
        formData.append("username", username);
        formData.append("password", password);

        const response = await fetch(`${API_URL}/token`, {
            method: "POST",
            body: formData
        });

        if (response.ok) {
            const data = await response.json();
            token = data.access_token;
            localStorage.setItem("risk_engine_token", token);
            showApp();
        } else {
            errorMsg.innerText = "Invalid Credentials";
        }
    } catch (e) {
        errorMsg.innerText = "Connection Error";
        console.error(e);
    }
}

function logout() {
    token = null;
    localStorage.removeItem("risk_engine_token");
    document.getElementById("login-screen").classList.remove("hidden");
    document.getElementById("app").classList.add("hidden");
}

function showApp() {
    document.getElementById("login-screen").classList.add("hidden");
    document.getElementById("app").classList.remove("hidden");
    // Default to dashboard
    showTab('dashboard-tab');
}

// --- Navigation ---
function showTab(tabId) {
    document.querySelectorAll(".tab-content").forEach(el => el.classList.remove("active"));
    document.querySelectorAll(".nav-btn").forEach(el => el.classList.remove("active"));

    document.getElementById(tabId).classList.add("active");

    // Highlight sidebar button
    const btn = Array.from(document.querySelectorAll(".nav-btn")).find(b => b.onclick.toString().includes(tabId));
    if (btn) btn.classList.add("active");
}

// --- API Helpers ---
function getHeaders() {
    return {
        "Authorization": `Bearer ${token}`,
        "Content-Type": "application/json"
    };
}

async function apiCall(endpoint, method = "GET", body = null) {
    const options = {
        method,
        headers: getHeaders(),
    };
    if (body) options.body = JSON.stringify(body);

    try {
        const res = await fetch(`${API_URL}${endpoint}`, options);

        if (res.status === 401) {
            logout();
            throw new Error("Session expired. Please log in again.");
        }

        const data = await res.json();

        if (!res.ok) {
            // Use 'detail' from FastAPI or fallback
            throw new Error(data.detail || data.message || "API Error");
        }

        return data;
    } catch (e) {
        throw e;
    }
}

// --- Features ---
async function ingestData() {
    const tickers = document.getElementById("ingest-tickers").value.split(",");
    const start = document.getElementById("ingest-start").value;
    const end = document.getElementById("ingest-end").value;
    const status = document.getElementById("ingest-status");

    status.innerText = "Fetching...";
    status.style.color = "yellow";

    try {
        const data = await apiCall("/ingest", "POST", { tickers, start_date: start, end_date: end });

        if (data.status === "success") {
            status.innerText = `Success: ${data.rows} rows loaded.`;
            status.style.color = "#48bb78";

            // Render Preview
            if (data.preview && data.preview.length > 0) {
                renderDataTable(data.preview);
                document.getElementById("ingest-preview-container").classList.remove("hidden");
            }
        } else {
            status.innerText = data.message;
            status.style.color = "#e53e3e";
        }
    } catch (e) {
        status.innerText = "Error: " + e.message;
        status.style.color = "#e53e3e";
    }
}

async function runSimulation() {
    const ticker = document.getElementById("sim-ticker").value;
    const paths = document.getElementById("sim-paths").value;
    const initial = parseFloat(document.getElementById("sim-initial").value);

    // Reset UI
    document.getElementById("sim-results").classList.add("hidden");

    try {
        const data = await apiCall("/simulate", "POST", {
            ticker,
            paths: parseInt(paths),
            initial_price: initial,
            days: 252,
            volatility: 0.20,
            drift: 0.05
        });

        document.getElementById("res-mean").innerText = "$" + data.mean_price.toFixed(2);
        document.getElementById("res-var").innerText = "$" + data.var_95.toFixed(2);
        document.getElementById("res-cvar").innerText = "$" + data.cvar_95.toFixed(2);
        document.getElementById("sim-results").classList.remove("hidden");

        // Render Chart
        if (data.paths) {
            renderSimulationChart(data.paths);
        }

    } catch (e) {
        console.error(e);
        alert(e.message);
    }
}

async function runStressTest() {
    const ticker = document.getElementById("stress-ticker").value;
    const type = document.getElementById("stress-type").value;
    const shock = parseFloat(document.getElementById("stress-shock").value);
    const initialPrice = parseFloat(document.getElementById("stress-initial").value);

    try {
        const data = await apiCall("/stress-test", "POST", {
            ticker,
            scenario_type: type,
            shock_value: shock,
            initial_price: initialPrice
        });

        const out = document.getElementById("stress-results");
        out.innerText = JSON.stringify(data, null, 2);
        out.classList.remove("hidden");

        // Render Chart
        renderStressChart(data, initialPrice);

    } catch (e) {
        console.error(e);
        alert(e.message);
    }
}

// --- UI Helpers ---
function renderDataTable(data) {
    const table = document.getElementById("ingest-preview-table");
    const thead = table.querySelector("thead");
    const tbody = table.querySelector("tbody");

    // Clear existing
    thead.innerHTML = "";
    tbody.innerHTML = "";

    if (data.length === 0) return;

    // Headers
    const headers = Object.keys(data[0]);
    const trHead = document.createElement("tr");
    headers.forEach(h => {
        const th = document.createElement("th");
        th.innerText = h;
        trHead.appendChild(th);
    });
    thead.appendChild(trHead);

    // Rows
    data.forEach(row => {
        const tr = document.createElement("tr");
        headers.forEach(h => {
            const td = document.createElement("td");
            td.innerText = row[h];
            tr.appendChild(td);
        });
        tbody.appendChild(tr);
    });
}

// --- Dashboard ---
async function updateDashboard() {
    // Simple health check integration
    try {
        await apiCall("/health");
        const statusText = document.getElementById("status-text");
        const statusInd = document.getElementById("status-indicator");

        statusText.innerText = "Online";
        statusText.style.color = "#48bb78";
        statusInd.classList.add("status-online");

        // In a real app, we would fetch active tickers count etc.
        // For now, placeholders are updated manually or left as is
    } catch (e) {
        if (document.getElementById("status-text")) {
            const statusText = document.getElementById("status-text");
            const statusInd = document.getElementById("status-indicator");
            statusText.innerText = "Offline";
            statusText.style.color = "#e53e3e";
            statusInd.classList.remove("status-online");
        }
    }
}

let chart;

async function loadLatestData() {
    try {
        const response = await fetch("/api/latest");
        const data = await response.json();

        if (!data || Object.keys(data).length === 0) {
            showOffline();
            return;
        }

        if (data.machine_status === "OFFLINE") {
            showOffline();
            return;
        }
        
        document.querySelector(".container").style.opacity = "1";
        document.querySelector(".container").classList.remove("offline");
        document.getElementById("status").innerText =
            data.machine_status || "UNKNOWN";

        document.getElementById("temperature").innerText =
            `${data.temperature} °C`;

        document.getElementById("current").innerText =
            `${data.current} A`;

        document.getElementById("power").innerText =
            `${data.power} W`;

        document.getElementById("count").innerText =
            data.count;

    } catch (err) {
        console.error("Latest Data Error:", err);
    }
}

async function loadHistory() {
    try {
        const response = await fetch("/api/history");
        const records = await response.json();

        updateTable(records);
        updateChart(records);

    } catch (err) {
        console.error("History Error:", err);
    }
}
function showOffline() {

    document.getElementById("status").innerText = "OFFLINE";

    document.getElementById("temperature").innerText = "-";
    document.getElementById("current").innerText = "-";
    document.getElementById("power").innerText = "-";
    document.getElementById("count").innerText = "-";

    document.querySelector(".container").classList.add("offline");
}
function updateTable(records) {

    const table = document.getElementById("historyTable");

    table.innerHTML = "";

    records.forEach(record => {

        const row = `
            <tr>
                <td>${record.id}</td>
                <td>${record.timestamp}</td>
                <td>${record.temperature}</td>
                <td>${record.current}</td>
                <td>${record.power}</td>
                <td>${record.count}</td>
                <td>${record.machine_status}</td>
            </tr>
        `;

        table.innerHTML += row;
    });
}

function showOffline() {

    document.getElementById("status").innerText = "OFFLINE 🚫";

    document.querySelector(".container").style.opacity = "0.5";
}

function setLiveUI() {
    document.querySelector(".container").classList.remove("offline");
}

function showOffline() {
    document.querySelector(".container").classList.add("offline");
}
 

function updateChart(records) {

    const reversed = [...records].reverse();

    const labels = reversed.map(r => r.timestamp);

    const temperatures = reversed.map(r => r.temperature);

    if (chart) {
        chart.destroy();
    }

    const ctx = document
        .getElementById("machineChart")
        .getContext("2d");

    chart = new Chart(ctx, {
        type: "line",
        data: {
            labels: labels,
            datasets: [
                {
                    label: "Temperature (°C)",
                    data: temperatures,
                    borderWidth: 2,
                    tension: 0.3
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false
        }
    });
}


async function filterData() {

    const start =
        document.getElementById("startDate").value;

    const end =
        document.getElementById("endDate").value;

    if (!start || !end) {

        alert("Select start and end date");

        return;
    }

    try {

        const response = await fetch(
            `/api/history/filter?start=${start}&end=${end}`
        );

        const records = await response.json();

        updateTable(records);
        updateChart(records);

    } catch (err) {

        console.error(err);

    }
}

function exportCSV() {

    const start =
        document.getElementById("startDate").value;

    const end =
        document.getElementById("endDate").value;

    let url = "/api/export/csv";

    if (start && end) {

        url += `?start=${start}&end=${end}`;

    }

    window.open(url, "_blank");
}

async function resetData() {

    const confirmDelete = confirm(
        "Delete all records?"
    );

    if (!confirmDelete) {
        return;
    }

    try {

        await fetch("/reset", {
            method: "POST"
        });

        loadLatestData();
        loadHistory();

    } catch (err) {

        console.error(err);

    }
}

async function refreshDashboard() {

    await loadLatestData();
    await loadHistory();

}



refreshDashboard();

setInterval(refreshDashboard, 5000);

window.addEventListener("load", () => {

    const now = new Date();

    const start = new Date();

    start.setHours(0);
    start.setMinutes(0);

    document.getElementById("startDate").value =
        start.toISOString().slice(0,16);

    document.getElementById("endDate").value =
        now.toISOString().slice(0,16);

});
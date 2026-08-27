const refreshButton = document.getElementById("refreshButton");
const refreshStatus = document.getElementById("refreshStatus");
const tableMeta = document.getElementById("tableMeta");
const workbookPath = document.getElementById("workbookPath");
const peopleTable = document.getElementById("peopleTable");

function setStatus(message, mode = "idle") {
  refreshStatus.textContent = message;
  refreshStatus.dataset.mode = mode;
}

function textCell(tagName, value, className = "") {
  const cell = document.createElement(tagName);
  if (className) {
    cell.className = className;
  }
  cell.textContent = value ?? "";
  return cell;
}

function renderTable(data) {
  const thead = peopleTable.querySelector("thead");
  const tbody = peopleTable.querySelector("tbody");
  thead.textContent = "";
  tbody.textContent = "";

  const headerRow = document.createElement("tr");
  headerRow.appendChild(textCell("th", "Row"));
  for (const column of data.columns) {
    headerRow.appendChild(textCell("th", column));
  }
  for (const column of data.decisionColumns) {
    const cell = textCell("th", column, "decision-head");
    headerRow.appendChild(cell);
  }
  thead.appendChild(headerRow);

  if (!data.rows.length) {
    const emptyRow = document.createElement("tr");
    const emptyCell = textCell("td", "표시할 행이 없습니다.", "empty");
    emptyCell.colSpan = data.columns.length + data.decisionColumns.length + 1;
    emptyRow.appendChild(emptyCell);
    tbody.appendChild(emptyRow);
    return;
  }

  for (const row of data.rows) {
    const tableRow = document.createElement("tr");
    tableRow.appendChild(textCell("td", row.source_row, "row-number"));
    for (const value of row.values) {
      tableRow.appendChild(textCell("td", value));
    }
    for (const column of data.decisionColumns) {
      tableRow.appendChild(textCell("td", row.decisions[column], "decision-cell"));
    }
    tbody.appendChild(tableRow);
  }
}

async function refreshPeople() {
  refreshButton.disabled = true;
  setStatus("불러오는 중...", "loading");

  try {
    const response = await fetch("/people/data/", {
      headers: { Accept: "application/json" },
      cache: "no-store",
    });
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const data = await response.json();
    renderTable(data);
    tableMeta.textContent = `${data.sheetName} · ${data.rowCount} rows`;
    workbookPath.textContent = data.workbookPath;
    setStatus(`갱신됨 ${new Date().toLocaleTimeString("ko-KR")}`, "ok");
  } catch (error) {
    setStatus(`불러오기 실패: ${error.message}`, "error");
  } finally {
    refreshButton.disabled = false;
  }
}

refreshButton.addEventListener("click", refreshPeople);

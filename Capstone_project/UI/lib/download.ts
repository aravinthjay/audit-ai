/** Trigger a real browser file download from in-memory data (no dependencies). */
export function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

/** Download any JSON-serializable value as a formatted .json file. */
export function downloadJson(filename: string, data: unknown) {
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
  downloadBlob(blob, filename.endsWith(".json") ? filename : `${filename}.json`);
}

/** Download a list of records as a CSV file. Columns come from the first row. */
export function downloadCsv(filename: string, rows: Record<string, unknown>[]) {
  if (rows.length === 0) {
    downloadBlob(new Blob([""], { type: "text/csv" }), filename);
    return;
  }
  const columns = Object.keys(rows[0]);
  const escape = (value: unknown) => {
    const text = value === null || value === undefined ? "" : String(value);
    return /[",\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
  };
  const csv = [
    columns.join(","),
    ...rows.map((row) => columns.map((col) => escape(row[col])).join(",")),
  ].join("\n");
  downloadBlob(new Blob([csv], { type: "text/csv" }), filename.endsWith(".csv") ? filename : `${filename}.csv`);
}

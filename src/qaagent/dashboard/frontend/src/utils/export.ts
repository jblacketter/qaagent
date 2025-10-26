/**
 * Export data as CSV file
 */
export function exportDataAsCSV<T extends Record<string, any>>(
  data: T[],
  filename: string
): void {
  if (!data.length) {
    alert("No data to export");
    return;
  }

  // Get all keys from first object
  const headers = Object.keys(data[0]);

  // Create CSV content
  const csvRows = [
    headers.join(","), // Header row
    ...data.map(row =>
      headers.map(header => {
        const value = row[header];
        // Escape commas and quotes
        const escaped = String(value ?? "").replace(/"/g, '""');
        return `"${escaped}"`;
      }).join(",")
    )
  ];

  const csvContent = csvRows.join("\n");
  downloadFile(csvContent, `${filename}.csv`, "text/csv");
}

/**
 * Export data as JSON file
 */
export function exportDataAsJSON(data: any, filename: string): void {
  const jsonContent = JSON.stringify(data, null, 2);
  downloadFile(jsonContent, `${filename}.json`, "application/json");
}

/**
 * Helper to trigger file download
 */
function downloadFile(content: string, filename: string, type: string): void {
  const blob = new Blob([content], { type });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

/**
 * Flatten nested objects for CSV export
 */
export function flattenForCSV<T extends Record<string, any>>(
  data: T[]
): Record<string, any>[] {
  return data.map(item => {
    const flat: Record<string, any> = {};

    Object.keys(item).forEach(key => {
      const value = item[key];

      if (value && typeof value === "object" && !Array.isArray(value)) {
        // Flatten nested object
        Object.keys(value).forEach(subKey => {
          flat[`${key}_${subKey}`] = value[subKey];
        });
      } else if (Array.isArray(value)) {
        // Convert arrays to comma-separated strings
        flat[key] = value.join("; ");
      } else {
        flat[key] = value;
      }
    });

    return flat;
  });
}

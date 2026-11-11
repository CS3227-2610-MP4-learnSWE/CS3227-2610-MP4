const needsQuotes = /[",\r\n]/;

function cell(value: string | number | null): string {
  if (value === null) return "";
  const text = String(value);
  return needsQuotes.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
}

/** CSV text with CRLF line endings; a cell is quoted only when it contains a comma, a quote or a newline. */
export function buildCsv(
  header: string[],
  rows: (string | number | null)[][],
): string {
  return [header, ...rows].map((row) => row.map(cell).join(",")).join("\r\n");
}

/** Saves text as a UTF-8 file without a byte-order mark. Builds from loaded data; sends no request. */
export function downloadCsv(filename: string, csv: string): void {
  const url = URL.createObjectURL(
    new Blob([csv], { type: "text/csv;charset=utf-8" }),
  );
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

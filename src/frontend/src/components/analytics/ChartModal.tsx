import { useRef, type ReactNode } from "react";
import {
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  useMediaQuery,
} from "@mui/material";
import { downloadCsv } from "../../lib/csv";

export type TableData = {
  head: string[];
  rows: (string | number)[][];
};

/** Larger chart, its data as a table, "Download CSV" (built from loaded data, no request) and "Close". */
export default function ChartModal({
  title,
  chart,
  table,
  csvName,
  csv,
  onClose,
}: {
  title: string;
  chart: ReactNode;
  table: TableData;
  csvName: string;
  csv: string;
  onClose: () => void;
}) {
  const closeButton = useRef<HTMLButtonElement>(null);
  const narrow = useMediaQuery("(max-width:599.95px)");
  const still = useMediaQuery("(prefers-reduced-motion: reduce)");
  return (
    <Dialog
      open
      onClose={onClose}
      fullScreen={narrow}
      fullWidth
      maxWidth="lg"
      transitionDuration={still ? 0 : undefined}
      slotProps={{
        transition: { onEntered: () => closeButton.current?.focus() },
      }}
      aria-labelledby="analytics-hub-modal-title"
    >
      <DialogTitle id="analytics-hub-modal-title">{title}</DialogTitle>
      <DialogContent>
        {chart}
        <div
          className="table-scroll analytics-scroll analytics-hub-modal-table"
          role="region"
          aria-label={`${title} data, scrollable`}
          tabIndex={0}
        >
          <table aria-label={`${title} data`}>
            <thead>
              <tr>
                {table.head.map((h) => (
                  <th scope="col" key={h}>
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {table.rows.map((row, i) => (
                <tr key={i}>
                  {row.map((value, j) =>
                    j === 0 ? (
                      <th scope="row" key={j}>
                        {value}
                      </th>
                    ) : (
                      <td key={j}>{value}</td>
                    ),
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </DialogContent>
      <DialogActions>
        <Button variant="outlined" onClick={() => downloadCsv(csvName, csv)}>
          Download CSV
        </Button>
        <Button
          ref={closeButton}
          variant="contained"
          autoFocus
          onClick={onClose}
        >
          Close
        </Button>
      </DialogActions>
    </Dialog>
  );
}

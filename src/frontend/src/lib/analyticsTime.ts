import type { HourlyBucket } from "../services/featureAnalytics";

export const WEEKDAYS = [
  "Monday",
  "Tuesday",
  "Wednesday",
  "Thursday",
  "Friday",
  "Saturday",
  "Sunday",
] as const;

export type LocalBucket = {
  iso: string;
  weekday: number;
  hour: number;
  label: string;
};
export type HeatmapCell = {
  weekday: number;
  hour: number;
  total: number;
  failed: number;
};

export const browserZone = () =>
  Intl.DateTimeFormat().resolvedOptions().timeZone || "";

const formatters = new Map<string, Intl.DateTimeFormat>();
function formatter(timeZone: string): Intl.DateTimeFormat {
  let f = formatters.get(timeZone);
  if (!f) {
    f = new Intl.DateTimeFormat("en-US", {
      timeZone,
      hourCycle: "h23",
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      weekday: "long",
      hour: "2-digit",
      minute: "2-digit",
      timeZoneName: "longOffset",
    });
    formatters.set(timeZone, f);
  }
  return f;
}

/** The local weekday (0 = Monday), hour, label and ISO time with offset of a UTC bucket start. */
export function toLocalBucket(
  hourStartUtc: string,
  timeZone: string,
): LocalBucket {
  const parts: Record<string, string> = {};
  for (const p of formatter(timeZone).formatToParts(new Date(hourStartUtc)))
    parts[p.type] = p.value;
  const hour = Number(parts.hour);
  const offset = parts.timeZoneName.replace("GMT", "") || "+00:00";
  const date = `${parts.year}-${parts.month}-${parts.day}`;
  return {
    iso: `${date}T${parts.hour}:${parts.minute}:00${offset}`,
    weekday: WEEKDAYS.findIndex((d) => d === parts.weekday),
    hour,
    label: `${parts.weekday.slice(0, 3)} ${date} ${parts.hour}:${parts.minute}`,
  };
}

/** 168 cells, Monday first then hour 0 to 23, summing requests over the period by local weekday and hour. */
export function buildHeatmap(
  buckets: HourlyBucket[],
  timeZone: string,
): HeatmapCell[] {
  const cells: HeatmapCell[] = WEEKDAYS.flatMap((_, weekday) =>
    Array.from({ length: 24 }, (_, hour) => ({
      weekday,
      hour,
      total: 0,
      failed: 0,
    })),
  );
  for (const bucket of buckets) {
    const local = toLocalBucket(bucket.hour_start, timeZone);
    const cell = cells[local.weekday * 24 + local.hour];
    cell.total += bucket.total;
    cell.failed += bucket.failed;
  }
  return cells;
}

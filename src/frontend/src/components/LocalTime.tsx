/** Display a recorded instant locally while preserving its original ISO value. */
export default function LocalTime({ value }: { value: string }) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return <span>Date unavailable</span>;
  return (
    <time dateTime={value} title={value}>
      {new Intl.DateTimeFormat(undefined, {
        dateStyle: "medium",
        timeStyle: "short",
      }).format(date)}
    </time>
  );
}

import { AlertTriangle, CheckCircle2, Info, OctagonAlert } from "lucide-react";
import type { Severity } from "../../services/featureAnalytics";

const CHIPS = {
  critical: { Icon: OctagonAlert, words: () => "Critical: above 5%" },
  warning: { Icon: AlertTriangle, words: () => "Warning: 2% to 5%" },
  ok: { Icon: CheckCircle2, words: () => "Healthy: below 2%" },
  low_sample: {
    Icon: Info,
    words: (threshold: number) =>
      `Low sample: fewer than ${threshold} requests`,
  },
} as const;

/** An icon plus words, so colour is never the only signal. */
export default function SeverityChip({
  severity,
  threshold,
}: {
  severity: Severity;
  threshold: number;
}) {
  const { Icon, words } = CHIPS[severity];
  return (
    <span className={`analytics-hub-chip analytics-hub-chip-${severity}`}>
      <Icon size={16} aria-hidden="true" />
      {words(threshold)}
    </span>
  );
}

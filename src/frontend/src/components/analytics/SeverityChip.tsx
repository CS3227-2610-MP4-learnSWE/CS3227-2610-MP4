import { AlertTriangle, CheckCircle2, Info, OctagonAlert } from "lucide-react";
import type { Severity } from "../../services/featureAnalytics";

const CHIPS = {
  critical: { Icon: OctagonAlert, words: () => "Critical: below 95%" },
  warning: { Icon: AlertTriangle, words: () => "Warning: 95% to 98%" },
  ok: { Icon: CheckCircle2, words: () => "Healthy: 98% or above" },
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

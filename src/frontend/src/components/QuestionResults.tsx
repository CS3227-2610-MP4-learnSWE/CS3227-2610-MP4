import type { Aggregate } from "../api/feedbackAnalysis";

type Row = { key: string; label: string; count: number; percent: number };

function rows(item: Aggregate): Row[] {
  if (item.kind === "scale")
    return (item.distribution ?? []).map((d) => ({ key: d.label, ...d }));
  return (item.options ?? []).map((o) => ({
    key: o.option_id,
    label: o.label,
    count: o.count,
    percent: o.percent,
  }));
}

/** Statistics computed by the server: an accessible table per question with a CSS bar hidden from assistive technology. */
export default function QuestionResults({
  aggregates,
}: {
  aggregates: Aggregate[];
}) {
  if (!aggregates.some((a) => a.kind !== "text"))
    return <p>This form has no choice or scale questions.</p>;
  return (
    <div className="analysis-questions">
      {aggregates.map((item) => (
        <section key={item.question_id} className="analysis-question">
          <h3>{item.prompt}</h3>
          <p>
            {item.answered} answered, {item.skipped} skipped
          </p>
          {item.kind === "scale" && item.mean != null && (
            <p>
              Mean {item.mean}, median {item.median}
            </p>
          )}
          {item.kind !== "text" &&
            (item.answered === 0 ? (
              <p>No answers.</p>
            ) : (
              <table aria-label={`Results for ${item.prompt}`}>
                <thead>
                  <tr>
                    <th scope="col">Option</th>
                    <th scope="col">Responses</th>
                    <th scope="col">Percent</th>
                  </tr>
                </thead>
                <tbody>
                  {rows(item).map((row) => (
                    <tr key={row.key}>
                      <td>{row.label}</td>
                      <td>{row.count}</td>
                      <td>
                        <span className="analysis-bar-track" aria-hidden="true">
                          <span
                            className="analysis-bar"
                            style={{ width: `${Math.min(100, row.percent)}%` }}
                          />
                        </span>
                        <span>{row.percent}%</span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ))}
        </section>
      ))}
    </div>
  );
}

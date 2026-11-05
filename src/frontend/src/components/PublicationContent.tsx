import type { PublicationDetail } from "../services/publications";
import type { McqDraftQuestion } from "../services/teacherMcqs";

export function QuestionPreview({
  questions,
}: {
  questions: McqDraftQuestion[];
}) {
  return (
    <ol className="mcq-questions">
      {questions.map((q) => (
        <li key={q.id}>
          <h3>{q.question}</h3>
          <ol type="A" aria-label={`Choices for question ${q.position}`}>
            {q.choices.map((choice, i) => (
              <li key={i}>{choice}</li>
            ))}
          </ol>
          <p>
            <strong>Correct answer:</strong>{" "}
            {String.fromCharCode(65 + q.correct_choice_index)}.{" "}
            {q.choices[q.correct_choice_index]}
          </p>
          <p>
            <strong>Explanation:</strong> {q.explanation}
          </p>
        </li>
      ))}
    </ol>
  );
}
export default function PublicationContent({
  item,
}: {
  item: PublicationDetail;
}) {
  return (
    <>
      <h2>{item.title}</h2>
      <p className="muted">
        Topic: {item.topic_name}
        <br />
        Published by: {item.published_by}
        <br />
        Published: {new Date(item.published_at).toLocaleString()}
        <br />
        {item.source_draft_id
          ? `Source draft: ${item.source_draft_id}`
          : "Source draft unavailable"}
        <br />
        {item.source_version === null
          ? "Source version unavailable"
          : `Source version: ${item.source_version}`}
      </p>
      {item.withdrawn && <p>Withdrawn</p>}
      {item.kind === "note" ? (
        <div className="note-content">{item.content}</div>
      ) : (
        <QuestionPreview questions={item.questions || []} />
      )}
    </>
  );
}

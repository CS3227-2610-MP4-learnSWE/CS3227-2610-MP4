import { Tab, Tabs } from "@mui/material";
import { Link, useSearchParams } from "react-router";
import TeacherNotes from "./TeacherNotes";
import TeacherMcqs from "./TeacherMcqs";

export default function TeacherContentStudio() {
  const [params] = useSearchParams();
  const questions = params.get("tab") === "questions";
  const course = params.get("course");
  const noteParams = new URLSearchParams(course ? { course } : {});
  const questionParams = new URLSearchParams({ tab: "questions" });
  if (course) questionParams.set("course", course);
  return (
    <>
      <Tabs
        value={questions ? "questions" : "notes"}
        aria-label="Content type"
        className="studio-tabs"
      >
        <Tab
          value="notes"
          label="Study notes"
          component={Link}
          to={`/teacher/generate?${noteParams}`}
        />
        <Tab
          value="questions"
          label="Practice questions"
          component={Link}
          to={`/teacher/generate?${questionParams}`}
        />
      </Tabs>
      {questions ? <TeacherMcqs /> : <TeacherNotes />}
    </>
  );
}

import { useEffect, useState } from "react";
import {
  listTeacherCourses,
  listTeacherMaterials,
  type Course,
  type Material,
} from "../services/teacherMaterials";

export function useTeacherStudioSources<T extends { id: string }>(
  queryCourse: string,
  listDrafts: (courseId: string) => Promise<T[]>,
) {
  const [courses, setCourses] = useState<Course[]>([]);
  const [coursesReady, setCoursesReady] = useState(false);
  const [coursesError, setCoursesError] = useState("");
  const [coursesReload, setCoursesReload] = useState(0);
  const [resources, setResources] = useState<{
    course: string;
    materials: Material[];
    drafts: T[];
  }>({ course: "", materials: [], drafts: [] });
  const [resourcesLoading, setResourcesLoading] = useState(false);
  const [resourcesError, setResourcesError] = useState("");
  const [reload, setReload] = useState(0);
  const [sourceId, setSourceId] = useState("");
  const courseId =
    coursesReady && (!queryCourse || courses.some((c) => c.id === queryCourse))
      ? queryCourse || courses[0]?.id || ""
      : "";

  useEffect(() => {
    let active = true;
    setCoursesError("");
    setCoursesReady(false);
    listTeacherCourses()
      .then((items) => {
        if (!active) return;
        setCourses(items);
        setCoursesReady(true);
      })
      .catch(() => {
        if (active)
          setCoursesError("Could not load courses. Please try again.");
      });
    return () => {
      active = false;
    };
  }, [coursesReload]);

  useEffect(() => {
    setSourceId("");
  }, [courseId]);

  useEffect(() => {
    let active = true;
    setResourcesError("");
    if (!courseId) {
      setResourcesLoading(false);
      return;
    }
    setResourcesLoading(true);
    Promise.all([listTeacherMaterials(courseId), listDrafts(courseId)])
      .then(([materials, drafts]) => {
        if (!active) return;
        setResources({ course: courseId, materials, drafts });
        setSourceId((previous) =>
          materials.some((m) => m.id === previous)
            ? previous
            : materials[0]?.id || "",
        );
      })
      .catch(() => {
        if (active)
          setResourcesError(
            "Could not load sources and saved drafts. Please try again.",
          );
      })
      .finally(() => {
        if (active) setResourcesLoading(false);
      });
    return () => {
      active = false;
    };
  }, [courseId, reload, listDrafts]);

  return {
    courses,
    coursesReady,
    coursesError,
    retryCourses: () => setCoursesReload((n) => n + 1),
    courseId,
    sourceId,
    setSourceId,
    resourcesReady: resources.course === courseId,
    materials: resources.course === courseId ? resources.materials : [],
    drafts: resources.course === courseId ? resources.drafts : [],
    resourcesLoading,
    resourcesError,
    reloadResources: () => setReload((n) => n + 1),
    updateDraft: (saved: T) =>
      setResources((previous) => ({
        ...previous,
        drafts: previous.drafts.map((item) =>
          item.id === saved.id ? saved : item,
        ),
      })),
  };
}

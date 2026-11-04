# Teacher MCQ editing and unpublished-work deletion

## 2026-11-04 — Approved implementation started

- User approved authenticated teacher APIs, versioned whole-batch MCQ editing and confirmed deletion of unpublished notes/MCQ batches plus unreferenced source materials. Any managing teacher may act; publication/unpublishing and student history changes are excluded.
- Clean master `da57eab` (PR16 authentication, after PR15 PostgreSQL storage) recorded before creating `feat/tea03-edit-mcqs-delete-drafts`.
- Variant B: spec-writer first; developer and independent test designer will use the same approved specification commit and separate folders, then a strongest read-only verifier. No redundant document approval requested: user supplied the complete approved plan.
- Test infrastructure: Docker application could not launch (missing executable). Initial sandboxed initdb failed on shared memory; approved elevated initdb/pg_ctl started an isolated temporary PostgreSQL cluster at loopback port55439, database learnswe_test. This is not the developer database. Existing development data, files and .env remain untouched.
- Baseline backend and mocked browser suites started before application changes. Results and subsequent commits recorded below when available.
- No live LLM, deployment, push, PR publication or merge into master authorised by this session.

- Approved contract/stories committed0038b47; independent developer/designer launched from that exact commit. Baseline backend692passed (101.81s), before application changes.

## Baseline and independent tests

- Baseline completed before implementation:692backendPASS (101.81s),224mockedbrowserPASS (2.0m). Existing note Back/Forward test passed; no speculative navigation fix required.
- Independent designer committed backend tests `b56bc12` before implementation visibility; UI tests still in progress. Same approved contract0038b47.
- Token tracker attempted branch filter; returned0 matching requests. This means unavailable attribution, not zero actual usage/cost. Summary retained; final resources will state limitation.

- Independent designer captured RED for cookie-auth regression atb56bc12 onapprovedstart0038b47: old teacher API ignores valid cookie and returns401 demanding demoheader. No implementation visibility before this testcommit.

## Integration correction round1

- Independent tests committedb56bc12/3d80b0c/260035e before sourcevisibility; developerd19bdf4 then merged by designer5771e15. Frontendtypes/lint/build/sourceformat pass.
- Initial integratedbackend726PASS/1harnessfailure (httpx cannot serialize lone surrogate without JSONescaping); designer correctedwireencoding334367f, retainingadversarialassertion. Fullrerunpending.
- Browser found two product issues: overlimitMCQfields hidecounter; expired401dirtyeditor clearsprivatebuffers but routerblocker intercepts/login redirect. Parent ruling requires shared/login redirect (anonymousbootstrapstillguidance), preserving ordinarydirtywarnings/logoutfailurebuffers. Developer addressingboth ascorrectionround1; cap2 total.
- Exacttext locator encompassinganonymousAlertlink correctedto rolealert containment, preserving visibleguidance+zeroteachercallassertions. No weakening producttests.

- Correction66ccbd8 retains invalid/duplicate MCQ counters and schedules expiry/logout navigation after protected views unmount; types/lint/build/diffcheckPASS.
- Final integratedbackend727PASS (81.33s), followingescaped-surrogatewirefixturecorrection. Browserrerunpending.
- MobileCancelinvestigation: screenshotjourney eventtrace provedpointerdown onCancel atscroll2558, pointerup/click ondifferentfields afterscroll1351. No Cancelclick reachesapp; no-screenshotjourney consistentlypasses. Designer separates visualfullpagecapture aslastaction fromfunctionalCancel/delete assertions; retains allassertions plusnormalmobileCancelregression. No speculativeappCSSfix. Parentinspected390light/1440dark editorimages: readable/focusvisible/nooverflow; otherwidth/themeconfirmationimagespending.

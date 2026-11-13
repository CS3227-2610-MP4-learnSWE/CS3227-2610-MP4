# learnSWE User Guide

This guide lists what each role can do, then walks you through every feature step by step with text you can copy and paste.

**Not set up yet?** Follow the [README](../README.md) first (about 10 minutes). Use the **sample data** option in step 4 so every screen has something to show.

## Contents

- [Before you start](#before-you-start)
- [Features at a glance](#features-at-a-glance): [Student](#student-features) · [Teacher](#teacher-features) · [Admin](#admin-features)
- [Walkthrough](#walkthrough)
  - [Part 1: Student](#part-1-student) (steps 1 to 6)
  - [Part 2: Teacher](#part-2-teacher) (steps 7 to 13)
  - [Part 3: Admin](#part-3-admin) (steps 14 to 19)
  - [Part 4: Student answers the feedback request](#part-4-student-answers-the-feedback-request) (step 20)
  - [Part 5: Admin follows up](#part-5-admin-follows-up) (steps 21 to 25)
- [Good to know](#good-to-know)

## Before you start

**Local sign-in accounts.** The table below contains the README's public examples for a fresh local setup. The actual accounts on your computer come from `src/backend/.env`; `.env.example` leaves these values empty. If you configured different values, use those instead throughout the walkthrough.

| Role | Email | Password |
|---|---|---|
| Student | `student@example.com` | `Student-Demo-4821` |
| Teacher | `teacher@example.com` | `Teacher-Demo-4821` |
| Admin | `admin@example.com` | `Admin-Demo-4821` |

**Open the app** at <http://127.0.0.1:5173/login>. Your role decides which workspace you see.

**Use two browser windows.** The walkthrough switches between roles. Keep the student in a normal window and the teacher or admin in a private (incognito) window, so you stay signed in as both and do not need to log out each time. To log out, choose **Log out** in the sidebar, then **Log out** again to confirm.

**Follow the steps in order.** Later steps use what earlier steps create. Copy the text shown in `code style` exactly.

## Features at a glance

Select a step number to jump to it.

### Student features

| Feature | What it does | Try it |
|---|---|---|
| Overview | Lessons completed, practice average and topics to revise, read from your saved records. | [Step 2](#step-2-see-your-overview) |
| Study materials | Lessons that your teachers published for your courses. Filter by topic, search, mark complete. | [Step 3](#step-3-read-a-lesson-and-mark-it-complete) |
| Practice | Multiple-choice sets, submitted as a whole. Scores, correct answers and explanations appear only after you submit. | [Step 4](#step-4-take-a-practice-set) |
| Progress | Lessons completed per course, best and latest practice scores, and topics worth another look. | [Step 5](#step-5-check-your-progress) |
| Study companion | AI chat for hints, explanations and help using the app. It never gives practice answers before you submit. | [Step 6](#step-6-ask-the-study-companion) |
| Inbox | Feedback requests from admins (answer them, with a saved draft), plus announcements and replies. | [Step 20](#step-20-answer-the-feedback-request) |

### Teacher features

| Feature | What it does | Try it |
|---|---|---|
| Overview | Per-course lesson completion, practice results and the most-missed questions for a period. Totals only, no student names. | [Step 7](#step-7-see-your-learning-overview) |
| Materials library | Upload PDF or text sources (up to 10 MiB each), set a topic, download or delete them. Uploading never publishes anything. | [Step 8](#step-8-upload-a-material) |
| AI content studio: notes | Generate draft study notes from a source, edit them, save. | [Steps 9 and 10](#step-9-generate-draft-study-notes) |
| AI content studio: questions | Generate a batch of three multiple-choice questions, review, edit. | [Step 12](#step-12-generate-and-publish-practice-questions) |
| Publish | Publish reviewed notes or a question set to a course as a permanent version. | [Steps 11 to 13](#step-11-publish-the-notes) |
| Inbox | Answer feedback requests and read admin messages. | Same as the student [Step 20](#step-20-answer-the-feedback-request) |

### Admin features

| Feature | What it does | Try it |
|---|---|---|
| Feature Analytics | Health (success rates, response times), requests per hour, peak hours, daily activity, AI usage and AI quality, for a period you choose. Charts expand on hover and click. | [Steps 14 and 15](#step-14-open-feature-analytics) |
| Courses | Create courses. | [Step 16](#step-16-create-a-course) |
| Users | Create student, teacher and admin accounts, give or remove course access, disable, enable or archive accounts. | [Step 17](#step-17-create-an-account-and-give-it-a-course) |
| Feedback hub: Forms | Build a feedback form, choose who receives it, publish, close. | [Steps 18 and 19](#step-18-create-a-feedback-form) |
| Feedback hub: Responses | Read each submitted response and delete one if needed. | [Step 21](#step-21-read-the-response) |
| Feedback hub: Follow-up | Reply to one respondent, or send an announcement to students or teachers. | [Steps 22 and 24](#step-22-reply-to-the-student) |
| Feedback hub: Analysis | AI summary of recurring issues, with statistics, from any set of responses. | [Step 23](#step-23-analyse-the-feedback) |

## Walkthrough

## Part 1: Student

### Step 1: Sign in

1. Open <http://127.0.0.1:5173/login>.
2. Enter `student@example.com` and `Student-Demo-4821`, then choose **Sign in**.

![The sign-in page](images/guide/01-login.png)

New students can register with **Create account** (display name, email, and a password of 10 to 128 characters). Accounts created this way are always student accounts.

### Step 2: See your overview

You land on **Overview**. The three figures come from your saved records: lessons completed, practice average, and topics to revise.

![Student overview](images/guide/02-student-overview.png)

### Step 3: Read a lesson and mark it complete

1. In the sidebar choose **Study materials**. Your course (Software Engineering) shows its published lessons. Use the topic buttons or the search box to filter.

   ![Study materials](images/guide/03-student-materials.png)

2. Choose **Writing a useful test**, read it, then choose **Mark as complete**. Your choice is saved; **Mark as incomplete** undoes it.

   ![A lesson](images/guide/04-student-lesson.png) ![Lesson marked complete](images/guide/05-student-lesson-complete.png)

### Step 4: Take a practice set

1. Choose **Practice**, then **Software engineering practice**.

   ![Practice sets](images/guide/06-student-practice-list.png)

2. Answer the three questions. To see both a right and a wrong answer, choose: question 1 **A single, focused responsibility**, question 2 **To catch regressions when code changes**, question 3 **4**.

   ![Answering questions](images/guide/07-student-practice-answers.png)

3. Choose **Submit practice set**. Nothing is sent until every question is answered. After submitting you see your score, the correct answer and an explanation for each question. Choose **Start another attempt** to try again; every attempt counts toward your progress.

   ![Practice results](images/guide/08-student-practice-results.png)

### Step 5: Check your progress

Choose **Progress**. It now shows your completed lesson, your practice score (best, latest, attempts) and which topics need another look. A topic needs revision when you answered at least 3 questions on it and fewer than 60% were correct (only your latest attempt on each set counts).

![Progress page](images/guide/09-student-progress.png)

### Step 6: Ask the study companion

1. Choose the round chat button at the bottom right of any student page.
2. Type `What is a unit test, in one sentence?` and press Enter. Replies can be wrong, so check them against the lessons.

   ![Study companion reply](images/guide/10-student-companion.png)

3. Close the chat with **Escape**; your messages are kept until you reload. The refresh icon in the chat clears it.

On the Practice page, before you submit, the companion gives hints but never the answer. This step needs the AI settings from the README; without them the companion says it is unavailable.

## Part 2: Teacher

Open a private window at <http://127.0.0.1:5173/login> and sign in as `teacher@example.com` with `Teacher-Demo-4821`.

### Step 7: See your learning overview

**Overview** shows totals for each course you teach: lesson completion, practice results and the most-missed questions. Change **Reporting period** (Last 7 days, Last 30 days, All time) to reload it. You will see the student's work from Part 1.

![Teacher overview](images/guide/11-teacher-overview.png)

### Step 8: Upload a material

1. Choose **Materials library**, then **Upload material**.
2. Enter the title `Testing basics` and choose the topic **Testing**.
3. Choose **Choose a file** and select `docs/sample-files/testing-basics.txt` from the project folder (a short text about unit tests).

   ![Upload dialog](images/guide/12-teacher-upload.png)

4. Choose **Upload**. The material is private: students cannot see it until you publish content made from it.

   ![Materials library](images/guide/13-teacher-materials.png)

### Step 9: Generate draft study notes

1. Choose **AI content studio** (the **Study notes** tab is open).
2. Under **Source material** choose **Testing basics**, then **Generate draft notes**. This sends the text to the SoC LLM and takes up to a minute.
3. The notes appear under **Saved drafts**, marked *Unpublished draft · Review required*. AI can be wrong, so review them.

   ![Generated notes](images/guide/14-teacher-notes-generated.png)

### Step 10: Edit the notes

1. Choose **Edit notes**. Change **Note title** to `Testing basics: key ideas`. You can edit the content too.

   ![Editing notes](images/guide/15-teacher-notes-edit.png)

2. Choose **Save changes**. No AI is used when you save. If you leave with unsaved edits, the app asks you to keep or discard them.

### Step 11: Publish the notes

1. Choose **Publish notes**. The title and topic are filled in from your draft.
2. Review the text, then choose **Confirm publication**.

   ![Publish notes](images/guide/16-teacher-publish-notes.png)

Publishing saves a permanent version that students can read. Later edits to the draft do not change it, and each draft can be published once.

### Step 12: Generate and publish practice questions

1. Go back to **AI content studio** and open the **Practice questions** tab.
2. Choose **Source material** **Testing basics**, then **Generate 3 draft MCQs**. You get one batch of three questions, each with four choices, the correct answer and an explanation.

   ![Generated questions](images/guide/17-teacher-mcqs-generated.png)

3. Read the questions. Use **Edit questions** if you want to change any.
4. Choose **Publish practice set**, then **Confirm publication**. A batch always publishes as one three-question set.

   ![Publish practice set](images/guide/18-teacher-publish-set.png)

### Step 13: See what you published

Choose **Published content**. It lists every published lesson and practice set. Select an item to read the saved version.

![Published content](images/guide/19-teacher-published-content.png)

Switch to the student window and refresh **Study materials**: the new lessons are there, and **Practice** lists the new set.

![New lessons for the student](images/guide/20-student-new-lesson.png)

## Part 3: Admin

Open another private window and sign in as `admin@example.com` with `Admin-Demo-4821`. You land on **Feature Analytics**.

### Step 14: Open Feature Analytics

1. Choose a **Reporting period** at the top right: Today (UTC), Last 7 days, Last 30 days or a custom range. **Refresh** (the circular arrow) reloads everything.
2. **Health** shows chatbot and generation success rates, rate-limited requests and response times. Use All, Successful or Failed on a time tile to change what it measures. The percentage chip tells you if a rate is healthy, in warning or critical.

   ![Feature Analytics](images/guide/21-admin-analytics.png)

3. Further down: **Feature outcomes** (logins, practice activity, chatbot use per student, generation reliability), **AI usage** (calls, failures and tokens per feature) and **Quality** (AI-graded response quality). AI usage figures appear for a period only once collection covers all of it, so a new install fills in from the next day.

   ![Feature outcomes](images/guide/45-admin-feature-outcomes.png)
   ![AI usage](images/guide/43-admin-ai-usage.png)
   ![Quality](images/guide/44-admin-quality.png)

### Step 15: Change the chart range and expand a chart

1. Above **Requests per hour** choose **Last 24 hours**, **Last 3 days** or **Last 7 days** (or **Selected period** for the period at the top). All three hourly charts follow it.

   ![Hourly charts for the last 24 hours](images/guide/22-admin-hourly-range.png)

2. Hover a chart card to enlarge it slightly, then click it (or **Expand**) to open a larger chart with its data table, **Download CSV** and **Close**. The Feature outcomes charts work the same way.

   ![Expanded chart](images/guide/23-admin-chart-overlay.png)

### Step 16: Create a course

1. Choose **Courses**.
2. Enter `Programming Basics` in **Course title** and choose **Create course**.

   ![Course created](images/guide/24-admin-course-created.png)

### Step 17: Create an account and give it a course

1. Choose **Users**. In **Create account** enter display name `Casey Lee`, email `casey@example.com`, role **Student**, and password `Casey-Demo-4821` twice (10 to 128 characters, not a common password).

   ![Create account](images/guide/25-admin-user-create.png)

2. Choose **Create account**; a green **Account created.** message confirms it. Share the password with the owner privately.
3. Search `Casey`, choose **Manage account** for Casey Lee, pick **Programming Basics** under **Course** and choose **Grant course access**.

   ![Manage account](images/guide/26-admin-user-manage.png)

From the same window you can **Disable account** (ends their sessions; **Enable account** brings it back), **Archive account** (permanent) or remove course access. You cannot disable or archive yourself.

### Step 18: Create a feedback form

1. Choose **Feedback hub**. Its tabs are **Forms**, **Responses**, **Analysis** and **Follow-up**, each with a count. Choose **New feedback form**.
2. **Form title**: `Course feedback survey`
3. **Description**: `Tell us how the course is going so we can improve it.`
4. Choose **Add question**. **Question 1 prompt**: `How satisfied are you with the course so far?` Set its type to **Linear scale** and tick **Question 1 required**.
5. Choose **Add question** again. **Question 2 prompt**: `What is one thing we could improve?` Set its type to **Paragraph**.

   ![The form editor](images/guide/27-admin-form-editor.png)

6. Choose **Save draft**. A draft cannot receive responses and sends nothing.

### Step 19: Choose the audience and publish

1. On the saved form choose **Review audience**.
2. Keep **Audience role** set to **Students**, tick **Casey Lee** and **Student**, and choose **Review selected recipients**.

   ![Choosing the audience](images/guide/28-admin-audience.png)

3. Check the list, then choose **Publish form**. Each recipient gets a private request in their Inbox. The questions and audience are now frozen.

   ![Form published](images/guide/29-admin-form-published.png)

## Part 4: Student answers the feedback request

### Step 20: Answer the feedback request

In the student window:

1. Choose **Inbox**. The new request **Course feedback survey** shows as *Not started*.

   ![Student inbox](images/guide/30-student-inbox.png)

2. Open it, choose **4** for question 1 and enter `More worked examples in the lessons would help.` for question 2. Your answers are saved as a draft as you type, so you can leave and come back.

   ![Answering the form](images/guide/31-student-feedback-filled.png)

3. Choose **Submit feedback**. The request now shows *Completed*.

   ![Feedback submitted](images/guide/32-student-feedback-submitted.png)

Your name and answers are visible to administrators once submitted. Your unfinished draft is private.

## Part 5: Admin follows up

Back in the admin window.

### Step 21: Read the response

1. In the **Feedback hub** choose **Responses**, then **Course feedback survey** from the list.
2. Choose the response from **Student** to read the answers.

   ![Responses](images/guide/33-admin-responses-list.png) ![A response](images/guide/34-admin-response-detail.png)

On the response list, **Analyse this form** jumps to the Analysis tab with the form selected.

### Step 22: Reply to the student

1. On the response choose **Respond to feedback**. The recipient is the respondent.
2. **Subject**: `Thanks for your feedback`
3. **Message**: `Thank you for the rating and the suggestion. We will add more worked examples to the lessons this term.`

   ![Writing the reply](images/guide/35-admin-reply-compose.png)

4. Choose **Review message**, read it, then **Confirm send**. A sent message cannot be edited or recalled.

   ![Reviewing the reply](images/guide/36-admin-reply-review.png)

5. In the student window open **Inbox**. The reply is under **Messages** and says which survey it answers.

   ![The student sees the reply](images/guide/37-student-reply.png)

### Step 23: Analyse the feedback

1. Choose the **Analysis** tab. Under **Select responses** choose **Course feedback survey** and tick **Select all responses**.

   ![Selecting responses](images/guide/38-admin-analysis-select.png)

2. Choose **Generate analysis**. Statistics per question appear at once. The AI summary follows in under a minute, with recurring issues and suggestions that link to the responses they came from. Suggestions marked *AI suggestion (no supporting feedback)* are not findings.

   ![Analysis result](images/guide/39-admin-analysis-result.png)

The analysis changes nothing and stays under **Previous analyses** until you delete it. Free-text answers are sent to the AI without names or IDs.

### Step 24: Send an announcement

1. Choose the **Follow-up** tab. Keep **Students** and **All active users** selected (choose **Selected users** to pick people).
2. **Subject**: `Welcome to the new term`
3. **Message**: `Lessons and practice sets are now available. Please complete the course feedback survey in your Inbox.`

   ![Writing the announcement](images/guide/40-admin-announcement-compose.png)

4. Choose **Review message**, check the recipient list, then **Confirm send**.

   ![Reviewing the announcement](images/guide/41-admin-announcement-review.png)

5. In the student window refresh **Inbox**: the announcement is unread under **Messages**, next to your reply. **Mark as read** clears it.

   ![The student sees the announcement](images/guide/42-student-announcement.png)

### Step 25: What to try next

- In **Feature Analytics**, switch the period and the hourly range and watch the figures change.
- In **Users**, disable Casey Lee, then enable the account again.
- Close the survey with **Close collection** on the form page: nobody can submit any more, but submitted responses stay.

## Good to know

- **AI.** The study companion, AI notes and questions, feedback analysis and answer grading use the SoC LLM and need the three `SOCLAAS_*` settings in the backend `.env`. AI output can be wrong and is always for you to review.
- **Limits.** Uploads: 10 MiB per file, 100 MiB in total, text of up to 8,000 characters or 100 PDF pages for generation. The companion accepts up to 1,000 characters per message and 20 messages a minute.
- **Practice answers.** Answers and explanations are revealed only after you submit the whole set.
- **Privacy.** Teachers see only totals, never individual students. Feedback is not anonymous: administrators see who answered.
- **Sessions.** You stay signed in for up to 12 hours. Disabled accounts are signed out at once.
- **Appearance.** The sun or moon button switches light and dark mode. On a phone, open the sidebar with the menu button.
- **Trouble signing in or starting the app?** See "If something goes wrong" in the [README](../README.md#if-something-goes-wrong).


## Hosted access

**Production smoke tests.** Open <https://learnswe-prod.onrender.com/login>. Use the student or teacher account below; ask the deployment owner for its current password privately.

| Role | Email | Password location (deployment owner's computer) |
|---|---|---|
| Student | `student-production@example.com` | Repository root `.env.production.accounts.local`: `SEED_STUDENT_PASSWORD` |
| Teacher | `teacher-production@example.com` | Repository root `.env.production.accounts.local`: `SEED_TEACHER_PASSWORD` |

Both production test passwords are 12 characters. They differ from the public local examples. These ignored files are not included in a clone of the repository. Share only the relevant student and teacher values through a private channel; do not share the whole file, which also contains administrator credentials. Production administrator credentials are not part of the reviewer handoff.

**Local smoke tests.** Open <http://127.0.0.1:5173/login> after starting the app. On the deployment owner's current local setup, the student email is `user1@example.com` and the teacher email is `teacher1@example.com`. Their passwords are in `src/backend/.env`, under `SEED_STUDENT_PASSWORD` and `SEED_TEACHER_PASSWORD`. Teammates using a fresh setup should use their own seeded values or the local examples in [Before you start](#before-you-start).

**Shared test data.** Use synthetic course content and feedback. Reviewers using the same account share its saved records, so coordinate uploads, publications and practice attempts. AI features use the team's SoC quota. The local sample-data walkthrough does not guarantee that the same lessons, forms or practice sets exist in production. The separate product website links to the application; it does not host accounts or learning records.

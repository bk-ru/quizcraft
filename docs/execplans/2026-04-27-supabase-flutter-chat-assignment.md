# Supabase Flutter Chat Assignment Orientation

This orientation is a living working document for the attached assignment about a Flutter client-server chat application with Supabase. It is intentionally separate from the existing QuizCraft execution plans because the attached files describe a different target application than the current repository contents.

This document must be maintained in accordance with `.agent/PLANS.md` if it is later used as an implementation plan.

## Purpose / Big Picture

The attached assignment asks for a mobile chat application built with Flutter, Supabase Auth, Supabase PostgreSQL, Supabase Realtime, and Supabase Storage. A completed target app should let users register and sign in, exchange realtime text messages, react to messages, sign in with Google, attach images and files, view and save media, send voice messages, delete messages, and use a custom design.

The current repository at the time of this document is not a Flutter chat app. It is QuizCraft, a local Python/FastAPI and static JavaScript application for generating Russian-language quizzes from uploaded documents through LM Studio. Because there is no `pubspec.yaml`, no `lib/`, no Android/iOS Flutter project folders, and no Flutter SDK available in the current environment, the assignment cannot be implemented directly in this repository without a deliberate project replacement or a new Flutter subproject decision from the user.

## Source Materials Reviewed

The attached files contain three related materials:

1. A full theory and starter guide for a baseline Flutter Supabase chat app. It explains cloud databases, SQL, PostgreSQL, Supabase, MVVM, the database schema, Flutter project layout, models, services, viewmodels, views, and widgets.
2. A theory-only file for topic 6, focused on client-server app development with Supabase, SQL, Auth, Realtime, Storage, and MVVM.
3. A practical assignment for topic 6. This is the operative task list and extends the baseline chat app with Google OAuth, file sending, image viewing and saving, voice messages, deleting messages, custom styling, and optional encryption.

The practical assignment also requires defensive exception handling. Network loss, Supabase downtime, server errors, timeouts, denied permissions, and other non-standard states must show understandable UI messages rather than crashing or hanging.

## Current Repository Orientation

The existing project is QuizCraft. Its backend lives under `backend/app/` and exposes FastAPI routes for documents, generation, health, settings, and quizzes. Its frontend lives under `frontend/` as static Russian-language HTML, CSS, and browser JavaScript modules. The test suite is Python `pytest`; linting is `ruff`.

Important existing files:

* `README.md` describes QuizCraft and its local LM Studio workflow.
* `AGENTS.md` requires scoped changes, pytest coverage for behavior changes, Cyrillic safety, Conventional Commits, and review reporting.
* `pyproject.toml` defines Python dependencies, pytest settings, and ruff settings.
* `.agent/PLANS.md` defines the ExecPlan format.
* `docs/execplans/` stores implementation plans.

This repository has no Flutter app entry points or mobile platform folders. The assignment's expected files such as `lib/main.dart`, `lib/supabase_options.dart`, `lib/models/message.dart`, `lib/services/supabase_service.dart`, `android/app/src/main/AndroidManifest.xml`, and `ios/Runner/Info.plist` do not exist.

## Assignment Target Architecture

The target Flutter app should follow MVVM:

* Models represent database records and UI data structures: `Message`, `UserModel`, and `Reaction`.
* Services isolate Supabase and other external integrations: authentication, database operations, realtime subscriptions, storage uploads, file URL generation, and deletion.
* ViewModels hold business logic and UI state: authentication state, chat messages, loading flags, errors, selected messages, recording state, and operation results.
* Views and widgets display UI only: login, register, chat screen, image viewer, chat bubble, file attachment dialog, and audio player widget.

The starter database schema is based on PostgreSQL tables:

* `public.users` for user profiles keyed by Supabase Auth user id.
* `public.messages` for chat messages with sender, receiver, text, chat room id, message type, file URL, file name, audio URL, audio duration, and creation timestamp.
* `public.message_reactions` for per-user reactions on messages.

Realtime should be enabled for `messages` and `message_reactions`. Row Level Security must be enabled, with policies allowing users to view messages in their own chats, send their own messages, delete permitted messages, and manage their own reactions.

## Required Functional Scope

The required baseline is:

1. Create and configure a Supabase project.
2. Execute the database schema and RLS policies from the starter material.
3. Configure a Flutter app with Supabase URL and anon key.
4. Support email registration and email login.
5. Send text messages between two users.
6. Receive realtime message updates without manual refresh.
7. Add and display reactions to messages.

The required extension scope is:

1. Add Google OAuth sign-in through Google Cloud Console and Supabase Auth provider settings.
2. Add a `chat-files` Supabase Storage bucket and storage policies.
3. Add file and image selection in the chat UI.
4. Upload files to Supabase Storage under the current user's folder.
5. Send image and file messages with message metadata.
6. Render image previews, file rows, and downloadable file links in chat bubbles.
7. Add full-screen image viewing with zoom.
8. Support saving images to gallery and files to Downloads.
9. Add voice message recording by holding the send or microphone button.
10. Upload recorded audio and send audio messages.
11. Render voice messages with playback controls and progress.
12. Add message deletion through long press or selection mode.
13. Delete attached files from Storage when deleting file messages where possible.
14. Replace the app name and icon.
15. Apply a custom visual design that is clearly different from the starter app.

The optional extension is message encryption:

1. Add the Dart `encrypt` package.
2. Create a `CryptoService` singleton in the service layer.
3. Encrypt outgoing text messages before inserting them into Supabase.
4. Decrypt messages after fetching them from Supabase.
5. Keep older plaintext messages readable.
6. Handle encryption and decryption errors without crashing.

## Manual Actions Required From the User

These steps require accounts, dashboards, secrets, or mobile-platform choices and cannot be completed safely by the agent without user involvement:

1. Decide whether this repository should be converted from QuizCraft into a Flutter chat repository, whether a new Flutter subproject should be added inside this repository, or whether the Flutter assignment belongs in a different repository.
2. Provide or create a Supabase project.
3. Save the Supabase database password outside the repository.
4. Run the starter SQL schema and additional RLS/storage policies in Supabase SQL Editor, or grant the agent scoped Supabase access and permission to run them.
5. Provide the Supabase project ref, API URL, and anon public key for `lib/supabase_options.dart` or an equivalent environment/configuration approach.
6. Decide whether email confirmation should remain enabled or be disabled for easier testing.
7. Create a Google Cloud project and OAuth 2.0 Web Client ID.
8. Add the Supabase callback URL `https://YOUR_PROJECT_REF.supabase.co/auth/v1/callback` to Google authorized redirect URIs.
9. Enable the Google provider in Supabase and enter the Google Client ID and Client Secret.
10. Create the Supabase Storage bucket `chat-files`, set the required public/private mode, and confirm the intended security model.
11. Provide Android package name, iOS bundle id, app display name, app icon concept/assets, and target platforms.
12. If testing on physical devices is required, provide emulator/device access or confirm that web/desktop Flutter testing is sufficient.

No Supabase URL, anon key, service role key, Google Client Secret, database password, keystore, or Apple signing credential should be committed to the repository.

## Automatable Work Once Project Direction Is Confirmed

If the user confirms that a Flutter app should be created or added, the first implementation batch should be limited to the baseline foundation:

1. Create the Flutter project structure.
2. Add the necessary baseline dependencies: `supabase_flutter`, `provider`, and the dependencies already required by the starter material.
3. Add `lib/supabase_options.dart` with placeholders or environment-based configuration that keeps secrets out of git.
4. Implement `main.dart` with Supabase initialization and providers.
5. Implement the user, message, and reaction models.
6. Implement `SupabaseService` for email auth, profile handling, text messages, reactions, and realtime subscriptions.
7. Implement `AuthViewModel` and `ChatViewModel`.
8. Implement login, registration, user list, chat view, chat bubble, reaction UI, and basic error notifications.
9. Add internet and network-state permissions for Android.
10. Add tests where practical for model serialization, service payload construction, and viewmodel behavior.

Only after that baseline is reviewed and tested should later batches add Google OAuth, storage/file messages, image viewing and saving, voice messages, deletion, custom design, and optional encryption.

## Validation Strategy

For a real Flutter implementation, validation should include:

* `flutter pub get`
* `dart format --set-exit-if-changed .`
* `flutter analyze`
* `flutter test`
* Manual or recorded app checks for registration, login, text messaging, realtime delivery, reactions, Google login, image/file upload, image preview, file download, voice recording, audio playback, deletion, and non-crashing error handling.

For the current QuizCraft repository, validation remains:

* `python -m pytest -q`
* `python -m ruff check .`

## Progress

- [x] Reviewed the attached starter/theory material for the Flutter Supabase chat app.
- [x] Reviewed the attached practical assignment and extracted the required functional scope.
- [x] Inspected the current repository and confirmed it is QuizCraft, not a Flutter chat app.
- [x] Confirmed that Flutter and Dart are not installed in the current environment.
- [x] Created this orientation document to preserve the assignment analysis, blockers, manual steps, and safe next implementation path.
- [ ] Await user decision on whether to convert this repository, add a Flutter subproject, or work in another repository.

## Surprises & Discoveries

The attached assignment and the current repository describe different products. The assignment is for a Flutter/Supabase mobile chat application, while the repository is a Python/FastAPI quiz generator backed by LM Studio. This blocks safe implementation of the assignment features in the current codebase without an explicit product/repository decision.

Flutter tooling is also absent in the current environment. The commands `command -v flutter` and `command -v dart` did not find installed executables, so even a newly scaffolded Flutter project could not currently be built, analyzed, or tested here without setup work.

## Decision Log

Decision: Do not replace the existing QuizCraft application with a Flutter project without explicit user confirmation.

Rationale: Replacing the repository would be a large destructive product change outside the current codebase's architecture. The user's supplied files are relevant, but they conflict with the existing repo contents. A safe agent should document the mismatch and stop at the point where manual direction is required.

Date/Author: 2026-04-27 / Devin

Decision: Keep this as a documentation and planning batch rather than implementing a synthetic Flutter scaffold.

Rationale: A scaffold without the user's Supabase project, Google OAuth configuration, target mobile identifiers, and confirmation of repository direction would be unverifiable and likely misleading. The project rules also require tested behavior changes, and Flutter tests cannot be run because Flutter is not installed.

Date/Author: 2026-04-27 / Devin

## Outcomes & Retrospective

This batch converts the attached materials into an actionable orientation for future implementation. It identifies the assignment scope, the target architecture, the current repository mismatch, the manual steps that need the user, and the safe automated sequence once project direction is confirmed.

No runtime behavior in QuizCraft is changed by this document.

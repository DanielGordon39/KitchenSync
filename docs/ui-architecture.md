# UI Architecture and Platform Direction

Status: browser-first direction for the first KitchenSync UI. The framework choices below are recommendations for the initial scaffold, not installed dependencies yet.

## Goals

- Build the first usable UI in a desktop browser.
- Make the same UI responsive enough for a mobile browser.
- Keep a practical path to a desktop application and Android/iOS applications.
- Keep recipe parsing, persistence, indexing, and other business rules in Python.
- Teach the UI stack incrementally instead of introducing every useful package on day one.

## Product UI Plan

The screen, navigation, flow, and component plan lives in `docs/ui-plan/README.md`. Keep product behavior decisions there and technical framework decisions in this document.

## Current Direction

Use a client-rendered single-page application with:

- **TypeScript** in strict mode for the UI language.
- **React** for components and screen composition.
- **Vite** for the development server and production build.
- **React Router** in Data Mode when the first multi-screen flow is added.
- **Native `fetch`** for the first HTTP calls.
- **Plain CSS or CSS Modules** for the first responsive layout.
- **npm** initially because it ships with Node.js and adds the least package-manager learning overhead.

This is a web-first choice, not a web-only choice. Vite produces static HTML, CSS, and JavaScript that can run in a browser, a Tauri webview, or a Capacitor webview.

### Package Manager Decision

Use **npm** as the package manager for the initial UI and throughout v1 development.

- npm ships with Node.js, matches most beginner-oriented TypeScript and React documentation, and keeps the initial toolchain small.
- Commit `package-lock.json` so local development and automated builds install the same resolved dependency versions.
- Use `npm install` while deliberately adding or updating packages and `npm ci` for clean, lockfile-driven installs in automated environments.
- Do not mix npm and Bun lockfiles in the repository. `package-lock.json` is the single UI lockfile while npm is the chosen package manager.

Revisit **Bun** after the browser UI is stable. Consider migrating when faster dependency installation or Bun's integrated tooling would solve a demonstrated development or build problem, and only after the Vite, testing, desktop, and mobile toolchains have been checked for compatibility. If adopted, treat it as a deliberate migration from `package-lock.json` to `bun.lock`, not as a second package manager used alongside npm.

### Why React Is the Starting Recommendation

- Its component and hook model is well documented with TypeScript examples.
- Its ecosystem covers routing, forms, testing, and server-state synchronization without requiring those packages immediately.
- A normal React SPA remains compatible with static browser hosting, Tauri, and Capacitor.
- The first KitchenSync screens are interactive application workflows rather than mostly static content.

Vue and Svelte are also credible TypeScript UI choices. Reconsider them before scaffolding if their template syntax or learning style is substantially more comfortable. The durable decision is browser-first TypeScript over HTTP/JSON; React is the recommended implementation, not a business-logic boundary.

## Architecture Boundary

The intended runtime boundary remains:

```text
React + TypeScript UI
        |
        | HTTP + JSON
        v
Python HTTP API
        |
        v
KitchenSyncApp facade
        |
        +-- Markdown source files
        +-- SQLite index and app state
```

The UI should:

- Render screens and reusable controls.
- Track temporary visual state such as an open dialog or selected tab.
- Validate that an HTTP response has the shape the UI expects.
- Call product-level API operations.
- Present API errors in useful language.

The UI should not:

- Read or write recipe Markdown directly.
- Query SQLite directly.
- Reimplement recipe scaling, parsing, ingredient matching, or save rules.
- Assume that a TypeScript type proves untrusted JSON is valid at runtime.

## Important Current Gap

The repository has a Python `KitchenSyncApp` facade, but it does not yet expose a browser-facing HTTP API. A browser cannot directly call `app.recipes.list()` or open local Markdown and SQLite files.

Before the real UI can load KitchenSync data, add a thin HTTP layer that delegates to the existing facade. FastAPI is a strong candidate because it works naturally with Python type hints and Pydantic, produces OpenAPI, and can expose the existing application methods without moving business logic into the web layer.

This is a separate future implementation decision. Adding FastAPI would change runtime dependencies and requires explicit confirmation before editing project configuration or application code.

Illustrative first endpoints:

```text
GET  /api/recipes
GET  /api/recipes/{recipe_id}
GET  /api/recipes/search?q=tomato
POST /api/imports/preview
POST /api/recipes/imported
```

Endpoint names are not locked. The important rule is that the save endpoint delegates to `app.recipes.save_imported_recipe(...)` rather than reproducing its Markdown and SQLite behavior.

## Platform Roadmap

| Stage | Runtime | UI reuse | Backend consideration |
| --- | --- | --- | --- |
| 1 | Desktop browser | The original React application | Run the UI and Python API locally during development. |
| 2 | Mobile browser | Same responsive React application | A phone cannot reach the computer's `localhost`; use an explicit LAN or hosted API address. |
| 3 | Installable PWA | Same React application plus manifest and service worker | Decide offline and update behavior before caching API responses. |
| 4 | Desktop app with Tauri | Same Vite build inside a desktop webview | Bundle the Python API as a sidecar or replace local HTTP with Tauri commands later. |
| 5 | Android/iOS app with Capacitor | Same web UI inside native projects | The app still needs a reachable API; mobile cannot assume the desktop's local Python process exists. |

### Why Tauri Later

Tauri can host a static frontend and can bundle an external binary such as a packaged Python API server. That makes it a plausible desktop shell after the browser UI and HTTP contract work.

Do not start with Tauri. It would add Rust, desktop permissions, packaging, sidecar startup, and process-lifecycle concerns before the UI has proved its basic workflows.

### Why Capacitor Later

Capacitor is designed to place an existing web application in an Android or iOS native container and expose native device APIs through plugins. It preserves more UI reuse than moving immediately to React Native.

Do not add Capacitor until:

- The responsive browser UI works well on a phone.
- The mobile app has a defined way to reach KitchenSync data.
- A real native capability or app-store package is needed.

If KitchenSync later needs a deeply native interface, extensive background execution, or native widgets that are awkward in a webview, reassess Expo/React Native. That would trade UI reuse for a more native component system.

## Recommended Project Location

When the user is ready to scaffold code, keep the frontend isolated under `ui/`:

```text
KitchenSync/
  docs/
  src/kitchensync/
  tests/
  ui/
    package.json
    vite.config.ts
    src/
      app/
      components/
      features/
        recipes/
        ingredients/
      lib/
        api/
      routes/
      styles/
```

This is one repository with two toolchains:

- `uv` manages Python.
- `npm` manages the TypeScript UI.

Avoid a monorepo manager until multiple JavaScript packages create a concrete need for one.

## Package Progression

Install packages only when the current lesson or feature needs them.

### Initial Scaffold

| Package | Purpose | Why now |
| --- | --- | --- |
| `typescript` | Static type checking | Core language choice. |
| `react` and `react-dom` | Components and browser rendering | Core UI library. |
| `vite` and `@vitejs/plugin-react` | Development and static builds | Small browser-first toolchain. |
| `react-router` | URLs, layouts, loaders, and navigation | Add when the second screen appears. |

The Vite `react-ts` template supplies the core React and TypeScript boilerplate.

### Add With the HTTP Boundary

| Package | Purpose | Adoption rule |
| --- | --- | --- |
| `zod` | Runtime validation of JSON and form values | Add when real API responses arrive. |
| `openapi-typescript` | Generate TypeScript API types from OpenAPI | Add after the HTTP schema is stable enough to generate rather than hand-copy. |
| `@tanstack/react-query` | Cache, synchronize, and mutate server data | Add only when route loaders and native `fetch` produce repeated caching/refetch logic. |

TypeScript types disappear when code runs. Zod or another runtime validator protects the boundary where unknown JSON enters the UI. Generated OpenAPI types reduce duplicated DTO declarations, but generated types still do not validate data at runtime.

### Add for Larger Forms

| Package | Purpose | Adoption rule |
| --- | --- | --- |
| `react-hook-form` | Field registration, errors, and efficient form state | Add when the manual recipe editor becomes large or nested. |
| `@hookform/resolvers` | Connect React Hook Form to Zod | Add with React Hook Form if Zod owns form validation. |

Use normal React state for the first URL input and small forms. A form library is helpful when it removes demonstrated repetition, not as required setup.

### Testing Packages

| Package | Purpose |
| --- | --- |
| `vitest` | Fast unit and component test runner that shares Vite configuration. |
| `@testing-library/react` | Test components through rendered user-facing behavior. |
| `@testing-library/user-event` | Simulate realistic typing, clicking, and keyboard interactions. |
| `msw` | Mock HTTP at the network boundary instead of mocking each `fetch` call. |
| `@playwright/test` | Test complete browser workflows across Chromium, Firefox, and WebKit. |

Start with tests around the first real workflow rather than testing empty scaffold files.

### Platform Packages, Later

| Package/tool | Purpose | Do not add until |
| --- | --- | --- |
| `vite-plugin-pwa` | Manifest and service-worker integration | Offline/update behavior has been decided. |
| Tauri | Desktop shell and Python sidecar packaging | Browser workflows and API contract are stable. |
| Capacitor | Android/iOS native container | Mobile browser UX and backend reachability are proven. |

## Why Not Start With These

- **Next.js:** Server rendering and a Node application server are not needed for a local client that talks to the Python API. A static Vite build is simpler to wrap with Tauri.
- **Redux or Zustand:** Most early data is API-owned server state. Use component state, route state, and URL state first.
- **A component framework:** Learn React, semantic HTML, accessibility, and CSS before adopting a visual system. Add one later if repeated controls justify it.
- **Tailwind CSS:** It is a valid later option, but plain CSS or CSS Modules expose browser layout concepts more clearly during the tutorial phase.
- **Axios:** Native `fetch` is sufficient for the initial API wrapper. Add another HTTP client only for a demonstrated feature it handles better.

## First Vertical Slice

Build one end-to-end path before creating every navigation tab:

1. Show a recipe list from `GET /api/recipes`.
2. Open a recipe detail route.
3. Enter a recipe URL.
4. Preview the parsed recipe.
5. Review raw and parsed ingredient values.
6. Save through the one accepted-recipe endpoint.
7. Return to the recipe detail screen.

This slice exercises routing, TypeScript DTOs, loading states, forms, API errors, and responsive layout while staying close to KitchenSync's current implementation.

## Responsive and Accessible Defaults

- Start layouts at narrow widths and add space for wider screens.
- Use semantic elements such as `nav`, `main`, `form`, `label`, `button`, and headings.
- Make every action usable by keyboard.
- Keep touch targets comfortably sized and separated.
- Do not encode meaning with color alone.
- Test at narrow phone width, wide phone width, tablet width, and desktop width.
- Prefer normal document flow and CSS Grid/Flexbox over absolute positioning.

## Suggested Scaffold Command

Run this only when the user asks to create UI boilerplate:

```powershell
npm create vite@latest ui -- --template react-ts
cd ui
npm install
npm run dev
```

Then add packages lesson-by-lesson instead of installing the entire package progression at once.

## Official References

- [TypeScript Handbook](https://www.typescriptlang.org/docs/handbook/intro.html)
- [React: Using TypeScript](https://react.dev/learn/typescript)
- [Vite: Getting Started](https://vite.dev/guide/)
- [React Router modes](https://reactrouter.com/start/modes)
- [Zod](https://zod.dev/)
- [TanStack Query](https://tanstack.com/query/latest/docs/framework/react/overview)
- [FastAPI first steps and OpenAPI](https://fastapi.tiangolo.com/tutorial/first-steps/)
- [OpenAPI TypeScript](https://openapi-ts.dev/)
- [Tauri frontend configuration](https://v2.tauri.app/start/frontend/)
- [Tauri external binaries](https://v2.tauri.app/develop/sidecar/)
- [Capacitor](https://capacitorjs.com/docs)
- [Progressive Web App installation](https://web.dev/learn/pwa/installation)
- [Vitest](https://vitest.dev/guide/)
- [React Testing Library](https://testing-library.com/docs/react-testing-library/intro/)
- [Playwright](https://playwright.dev/docs/intro)

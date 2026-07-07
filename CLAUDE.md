# CLAUDE.md

## Project Structure

Excalidraw is a **monorepo** with a clear separation between the core library and the application:

- **`packages/excalidraw/`** - Main React component library published to npm as `@excalidraw/excalidraw`
- **`excalidraw-app/`** - Full-featured web application (excalidraw.com) that uses the library
- **`packages/`** - Core packages: `@excalidraw/common`, `@excalidraw/element`, `@excalidraw/math`, `@excalidraw/utils`
- **`examples/`** - Integration examples (NextJS, browser script)

## Development Workflow

1. **Package Development**: Work in `packages/*` for editor features
2. **App Development**: Work in `excalidraw-app/` for app-specific features
3. **Testing**: Always run `yarn test:update` before committing
4. **Type Safety**: Use `yarn test:typecheck` to verify TypeScript

## Development Commands

```bash
yarn test:typecheck  # TypeScript type checking
yarn test:update     # Run all tests (with snapshot updates)
yarn fix             # Auto-fix formatting and linting issues
```

## Architecture Notes

### Package System

- Uses Yarn workspaces for monorepo management
- Internal packages use path aliases (see `vitest.config.mts`)
- Build system uses esbuild for packages, Vite for the app
- TypeScript throughout with strict configuration

## AIX Core Platform Integration (do not undo)

This app is a platform-integrated AIX agent (`AGENT_ID = "aixdraw"`). The auth and entitlement pattern is LOCKED:

- Identity: AIX Core's Clerk app (shared session across `*.aiworkforce.md`). Never create or wire a separate Clerk project.
- Entitlement: every authed HTTP request and socket connection passes `server/core_access.py` (`check_core_access`), which calls Core's `/api/v1/agents/aixdraw/access` and FAILS CLOSED. Never bypass, cache longer than 60s, or remove this gate.
- No Clerk webhooks: Core owns the only Clerk webhook subscription. User/workspace rows are JIT-mirrored on first authed request (`server/auth.py::_ensure_user_exists`). Do not add webhook handlers.
- Anonymous canvas is intentional: signed-out visitors get a localStorage-only canvas. Do not add a sign-in wall, and do not expose backend data to anonymous users.
- Envs and the full integration playbook (staging + prod values, Railway setup, verification): `ai-workforce-docs` repo → `core-platform/handoff/agent-integration/` (https://github.com/Ai-Xccelerate/ai-workforce-docs/tree/main/core-platform/handoff/agent-integration). Follow those docs exactly; do not invent auth patterns.
- Branches: `develop` → Railway staging (draw-staging.aiworkforce.md), `master` → production (draw.aiworkforce.md).

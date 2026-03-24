# Stufe 3: Source-Code scannen

Verzeichnisstruktur und Dateiendungen analysieren, um Projekttyp und Architektur zu erkennen.

## Erkennungsmuster

| Muster | Erkennung |
|--------|-----------|
| `app/`, `pages/` | Web-App (Next.js, Nuxt, etc.) |
| `src/lib/`, `src/index.ts` + kein `app/` | Library |
| `src/components/`, `components/` | Komponentenbasiert (React, Vue, etc.) |
| `cmd/`, `internal/`, `pkg/` | Go CLI / Service |
| `Controllers/`, `Models/`, `Views/` | MVC-Architektur (.NET, Rails, etc.) |
| `packages/`, `apps/` | Monorepo |
| `api/`, `routes/`, `endpoints/` | API/Backend |
| `tests/`, `test/`, `spec/`, `__tests__/` | Test-Verzeichnisse |
| `public/`, `static/`, `assets/` | Static Assets |

## Zusätzlich

Stichprobenartig 5-10 Source-Dateien lesen, um verwendete Imports/Libraries zu erkennen, die nicht in Manifest-Dateien stehen (z.B. interner Code-Stil, State-Management-Library, etc.).

# Stufe 2: Infrastruktur- und Framework-Configs

Basierend auf der erkannten Sprache gezielt nach Framework-spezifischen Configs suchen.

## Infrastruktur (sprachunabhängig)

| Datei(en) | Erkennung |
|-----------|-----------|
| `Dockerfile`, `docker-compose.yml` | Container/Docker |
| `.github/workflows/*.yml` | GitHub Actions CI/CD |
| `.gitlab-ci.yml` | GitLab CI/CD |
| `vercel.json` | Vercel Deployment |
| `netlify.toml` | Netlify Deployment |
| `*.tf`, `terraform/` | Terraform/IaC |
| `k8s/`, `kubernetes/`, `helm/` | Kubernetes |
| `.env.example`, `.env.local.example` | Environment-Variablen (Struktur, nicht Werte!) |

## Framework-Configs (nach erkannter Sprache)

| Datei(en) | Erkennung |
|-----------|-----------|
| `next.config.*` | Next.js |
| `nuxt.config.*` | Nuxt |
| `vite.config.*` | Vite |
| `astro.config.*` | Astro |
| `svelte.config.*` | SvelteKit |
| `angular.json` | Angular |
| `tailwind.config.*` | Tailwind CSS |
| `tsconfig.json` | TypeScript |
| `prisma/schema.prisma` | Prisma ORM |
| `drizzle.config.*` | Drizzle ORM |
| `supabase/` | Supabase |
| `firebase.json` | Firebase |
| `jest.config.*`, `vitest.config.*` | Unit-Testing |
| `playwright.config.*`, `cypress.config.*` | E2E-Testing |
| `.eslintrc.*`, `eslint.config.*` | Linting |
| `.prettierrc.*` | Formatting |

## Datenbank-Erkennung

- Migrations-Ordner (`migrations/`, `db/migrate/`, `prisma/migrations/`)
- Connection-Strings in `.env.example` (nicht in `.env`!)
- ORM-Config-Dateien

**Hinweis:** Aktiv nach weiteren Config-Dateien suchen, die nicht in dieser Liste stehen. Neue Frameworks und Tools bringen eigene Config-Dateien mit — alles, was wie eine Konfiguration aussieht, ist relevant.

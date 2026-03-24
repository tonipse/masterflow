# Stufe 1: Manifest-Dateien (Sprache + Pakete erkennen)

Das sind die zuverlässigsten Indikatoren — sie sagen sofort Sprache, Paketmanager und alle Dependencies.

| Datei(en) | Sprache/Ökosystem | Enthält |
|-----------|-------------------|---------|
| `package.json`, `package-lock.json`, `pnpm-lock.yaml`, `yarn.lock`, `bun.lock` | JavaScript / TypeScript | Dependencies, Scripts, Engine-Version |
| `*.csproj`, `*.sln`, `Directory.Build.props`, `nuget.config`, `global.json` | C# / .NET | NuGet-Pakete, Target-Framework, SDK-Version |
| `pyproject.toml`, `requirements.txt`, `setup.py`, `Pipfile`, `poetry.lock` | Python | Packages, Python-Version |
| `go.mod`, `go.sum` | Go | Module, Dependencies |
| `Cargo.toml`, `Cargo.lock` | Rust | Crates, Edition |
| `Gemfile`, `Gemfile.lock`, `*.gemspec` | Ruby | Gems, Ruby-Version |
| `composer.json`, `composer.lock` | PHP | Packages, PHP-Version |
| `pom.xml`, `build.gradle`, `build.gradle.kts` | Java / Kotlin | Maven/Gradle Dependencies |
| `pubspec.yaml` | Dart / Flutter | Packages, SDK-Constraints |
| `Package.swift` | Swift | SPM Dependencies |
| `mix.exs` | Elixir | Hex-Packages |
| `Makefile`, `CMakeLists.txt` | C / C++ | Build-Config, Libraries |

## Regeln

- Alle gefundenen Manifest-Dateien vollständig lesen und Dependencies extrahieren
- Bei Monorepos: Rekursiv in Unterordnern suchen (z.B. `packages/*/package.json`)
- Diese Liste ist nicht abschließend — aktiv nach weiteren Dateien suchen, die auf Pakete, Dependencies oder Build-Konfigurationen hinweisen

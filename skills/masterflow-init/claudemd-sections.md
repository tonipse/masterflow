# CLAUDE.md — Skills-Abschnitt

Folgenden Abschnitt exakt in die CLAUDE.md einfügen:

```markdown
## Skills

Alle installierten Skills liegen in `.claude/skills/`. **Jeder Skill, der zur aktuellen Aufgabe passt, muss verwendet werden** — keine Ausnahmen, kein Vergessen. Vor jedem Arbeitsschritt prüfen, ob ein passender Skill existiert.

### Superpowers (AI-driven Development Framework)

Superpowers ist das Framework für strukturiertes AI-driven Development — es steuert, wie geplant, umgebaut, debuggt und reviewed wird:

#### Planung

- **`superpowers:brainstorming`** – Vor jeder kreativen Arbeit (neue Features, Komponenten, Funktionalität)
- **`superpowers:writing-plans`** – Bei Multi-Step-Tasks, bevor Code geschrieben wird

#### Umsetzung

- **`superpowers:executing-plans`** – Beim Ausführen von geschriebenen Plänen
- **`superpowers:subagent-driven-development`** – Bei Plänen mit unabhängigen Tasks (Parallelisierung)
- **`superpowers:dispatching-parallel-agents`** – Bei 2+ unabhängigen Tasks ohne Shared State

#### Qualitätssicherung

- **`superpowers:systematic-debugging`** – Bei Bugs, Testfehlern, unerwartetem Verhalten
- **`superpowers:verification-before-completion`** – Bevor Arbeit als fertig deklariert wird
- **`superpowers:requesting-code-review`** – Nach Abschluss von Features / vor Merge
- **`superpowers:receiving-code-review`** – Bei eingehendem Review-Feedback

### Weitere Skills

Neben Superpowers können in `.claude/skills/` weitere projekt- oder technologiespezifische Skills installiert sein. Diese sind gleichwertig und müssen genauso konsequent eingesetzt werden, wenn sie zur Aufgabe passen.

### Regel

**Alle Skills aus `.claude/skills/` aktiv nutzen.** Vor jedem Schritt — ob Planung, Umsetzung, Debugging oder Review — prüfen, welcher Skill passt. Kein Arbeitsschritt ohne den zugehörigen Skill, wenn einer existiert. Skills dürfen nicht ignoriert oder vergessen werden.
```

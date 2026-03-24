# Scoring-System (Wie Skills bewerten)

Jeder Skill-Kandidat wird quantitativ bewertet, um Vergleichbarkeit zu schaffen.

## Scoring-Dimensionen (je 1-5 Punkte)

| Dimension | Gewicht | 1 Punkt | 3 Punkte | 5 Punkte |
|-----------|---------|---------|----------|----------|
| **Relevanz** | 25% | Vage Verbindung zum Stack | Nützlich aber nicht essenziell | Direkt auf den Stack zugeschnitten |
| **Qualität** | 25% | Kein Frontmatter, vage Instructions | Funktional, basic Docs | Sauberes SKILL.md, Beispiele, progressive Disclosure |
| **Wartung** | 15% | Letzter Commit >6 Monate | Commits in letzten 3 Monaten | Aktive Entwicklung, Issues werden beantwortet |
| **Sicherheit** | 15% | Keine Sicherheitsprüfung, verdächtige Patterns | `allowed-tools` im Frontmatter, kein Shell-Zugriff | Offizielle Quelle, Sicherheits-Audit dokumentiert, `allowed-tools` restriktiv |
| **Vertrauen** | 10% | Unbekannter Autor, <50 Stars | Bekannte Community-Quelle, 100+ Stars | Offizielle Quelle (Anthropic, obra) oder 1000+ Stars |
| **Einzigartigkeit** | 10% | Dupliziert vorhandene Skills | Teilweise Überlappung | Füllt eine klare Lücke |

## Gewichteter Score

```
Score = (Relevanz x 0.25) + (Qualität x 0.25) + (Wartung x 0.15) + (Sicherheit x 0.15) + (Vertrauen x 0.10) + (Einzigartigkeit x 0.10)
```

## Schwellenwerte

- **Score >= 4.0** — Starke Empfehlung: Installieren
- **Score 3.0 - 3.9** — Bedingte Empfehlung: Installieren, wenn Bedarf besteht
- **Score 2.0 - 2.9** — Keine Empfehlung: Nur auf expliziten Wunsch
- **Score < 2.0** — Warnung: Nicht empfohlen (Qualitäts- oder Sicherheitsbedenken)

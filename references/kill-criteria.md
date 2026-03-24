# Kill-Kriterien (disqualifizierend, unabhängig vom Score)

## Sofort disqualifiziert

- Kein SKILL.md oder kein YAML-Frontmatter
- Verdächtige Shell-Befehle (`curl | bash`, `rm -rf`, `wget | sh`)
- Zugriff auf `~/.ssh`, `~/.aws`, `~/.config` oder andere sensible Verzeichnisse
- Base64-Encoding/Decoding in Shell-Befehlen (häufig für Credential-Exfiltration genutzt)
- Zugriff auf `.env`, Credentials, API-Keys, Tokens oder Secrets
- Downloads von externen URLs (die nicht GitHub, GitLab oder bekannte Package-Registries sind)
- Prompt-Injection-Muster (z.B. "Ignore previous instructions", "SYSTEM OVERRIDE", "You are now", versteckte Anweisungen in Kommentaren)
- Letzter Commit >12 Monate und keine Antwort auf Issues — Disqualifiziert als "aufgegeben"

## Warnung (nicht sofort disqualifiziert, aber prüfen)

- Keine Lizenz
- Verzögerte/bedingte Ausführung (Date-Checks, Environment-Variable-Checks als Trigger für Befehle)
- Obfuskierter Code oder verschachtelte Shell-Aufrufe

## "Stabil" vs. "Aufgegeben" unterscheiden

Manche Skills ändern sich selten, weil sie ausgereift sind — nicht weil sie aufgegeben wurden. Indikatoren für "stabil":

- Maintainer antwortet auf Issues (auch wenn selten)
- Skill funktioniert mit aktueller Claude-Code-Version
- Community nutzt den Skill aktiv (Stars wachsen noch)

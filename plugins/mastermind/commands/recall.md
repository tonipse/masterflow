---
description: Search the Mastermind brain for prior knowledge on a topic and summarize it with links.
argument-hint: "<topic or error text>"
---

Search the Mastermind vault via the `mastermind-memory` tools for: "$ARGUMENTS"

1. `search_notes` with `search_type: "hybrid"` (page_size 8). If nothing relevant comes back, try one
   more phrasing (synonym, English term, the library name alone).
2. Read the top matches (`read_note`); follow one hop of links with `build_context` when a hub or stack
   note is among them.
3. Answer in German: a concise summary of the relevant patterns, gotchas, decisions and how-tos, each with
   its `[[wikilink]]`, newest facts first, with their recency hints. Name the projects where it was used.
4. If nothing relevant exists, say so plainly and name the closest stack note or similar project hub
   instead. Do not write anything to the vault in this command.

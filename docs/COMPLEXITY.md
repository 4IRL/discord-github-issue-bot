# Complexity ratings

Every `/bug` and `/feature` report gets a complexity band, S, M, L or XL, before it is filed. Simple documented rules suggest the band, and the reporter can change it in the preview. The rules live in [`issue_bot/complexity.py`](../issue_bot/complexity.py); this page explains them.

## The bands

| Band | Points | Meaning |
|---|---|---|
| S | 1 | Small: a quick fix or a minor change |
| M | 2 | Medium: a contained piece of work |
| L | 3 | Large: several parts or a longer job |
| XL | 5 | Extra large: a big job that may need splitting |

## The rules

The report's type sets the starting band:

- `bug` starts at S
- `feature` starts at M

Then the total length of the answers raises it. The total counts the characters of every answer with leading and trailing whitespace (spaces, tabs, line breaks) trimmed; spaces and line breaks inside an answer count, the Title doesn't, and a blank answer counts 0.

- A total of at least 800 characters raises the band one step.
- A total of at least 2000 characters raises it two steps.
- The band never goes past XL.

Two examples:

- A `/bug` whose answers add up to 900 characters starts at S and is raised one step to M.
- A `/feature` whose answers add up to 2100 characters starts at M and is raised two steps to XL. With 5000 characters it is still XL.

## Changing the band before filing

The private preview shows a **Complexity** field with the suggested band, and four buttons, S, M, L and XL, with the current band highlighted. Press one to choose a different band; the field then says it is your choice and which band the rules suggested. Your choice sticks when you press **Edit** and change the text. Until you press a band, **Edit** re-rates the report from the new answers.

## On GitHub

The filed issue carries its type's label plus exactly one `complexity:<band>` label, such as `complexity:M`, and the thread's link message names the band (its wording is in the README's [Status](../README.md#status)).

- The bot creates a missing `complexity:<band>` label itself, on each route's repo, the first time a report with that band is filed there.
- The bot remembers each label it created or found until it restarts, so it re-creates a `complexity:<band>` label deleted on GitHub only after a restart. Until then, an issue filed with that band may lose the label or GitHub may create it itself _(unverified)_.
- If GitHub refuses to create the label, that issue is still filed, with its type label only, and the bot logs a warning. The next report filed with that band tries again.
- To stop using the labels, delete them on the repo's **Labels** page. An older build of the bot doesn't apply them and needs no config change.

The preview is private to the reporter, so other members can't change the band before filing. Anyone with access to the repo can change the `complexity:<band>` label on GitHub after filing.

# veil

**Redact sensitive data before it reaches an AI model, then put it back in the answer.**

Zero dependencies · ~400 lines of Python · runs offline · reversible · MIT

<p align="center">
  <img src="docs/before-after.svg" alt="A support ticket before and after veil scrub: names, email, phone, IBAN, card, SSN, IP, credentials and keys replaced with placeholders like [EMAIL_1]" width="880">
</p>

---

## The problem

People paste real data into AI assistants every day. A support agent pastes a ticket to get help with a reply. An engineer pastes a stack trace that has a database URL in it. A nurse pastes a note to have it summarised. Each paste can send **customer PII, credentials and regulated data** to a third party. It may be logged, kept, read by reviewers or used for training, depending on the provider and plan.

The usual fixes don't work well in practice:

| Approach | Why it falls short |
|---|---|
| "Just don't paste sensitive stuff" | People are busy. Policies don't stop copy-paste. |
| Ban AI tools | People use them anyway, on personal accounts with less protection. |
| Heavy DLP / NER platforms | Expensive, need a server or ML models, and often too slow to sit in front of every prompt. |
| One-way redaction (`***`) | The model's answer comes back full of `***`, so people stop using it. |

**veil takes a different approach: reversible pseudonymisation on your machine.** Sensitive values become stable placeholders such as `[EMAIL_1]`. The model can still reason about them ("reply to [PERSON_3] about the charge on [CREDIT_CARD_1]"). veil then swaps the real values back into the answer. The mapping stays in a local vault file that never leaves your machine.

## How it works

<p align="center">
  <img src="docs/how-it-works.svg" alt="Your text goes through veil scrub, the model sees only placeholders, and veil restore uses the local vault to rebuild the real answer" width="880">
</p>

1. **Detect.** Regexes find candidates. **Validators** confirm them: Luhn for cards, mod-97 for IBANs, SSA rules for SSNs, `ipaddress` for IPs, and Shannon entropy for unknown keys. This keeps false positives low without an ML model.
2. **Resolve overlaps.** Each detector has a priority. A leaked key beats an email, and an email beats a custom term, so a term like `northwind` never splits `ops@northwind.com`.
3. **Pseudonymise.** Each distinct value gets one stable placeholder for the whole conversation. The same email is always `[EMAIL_1]`.
4. **Restore.** Placeholders in the model's reply are swapped back. Restore still works if the model reformats a token, for example `[ email_1 ]` or `[Email_1]`. Unknown tokens are left as they are.

## Quick start

```bash
cd veil
pip install .            # or skip install and use: python -m veil ...

veil scan    examples/support_ticket.txt                  # what's in here? (exit 1 if anything)
veil scrub   examples/support_ticket.txt -o safe.txt      # safe to paste anywhere
veil restore reply.txt                                    # put the real values back
```

Names can't be found reliably with regexes alone, so list the people, clients and codenames you care about:

```bash
veil scrub ticket.txt -T examples/terms.txt               # one term per line
veil scrub ticket.txt -t "PERSON: Dana Whitfield" -t "ORG: Northwind"
```

`veil scan` output (colourised in a terminal):

```
     1:30   PERSON          Da…ld
     3:11   PERSON          Ma…an
     3:28   EMAIL           m.…om
     3:60   PHONE           +4…58
     4:15   IBAN            GB…32
     5:15   CREDIT_CARD     41…11
     6:32   SSN             12…89
     8:1    PERSON          ••••••
     8:74   IP_ADDRESS      10…17
    10:24   URL_CREDENTIAL  Wi…g!
    10:48   ORG             no…nd
    11:21   AWS_KEY         AK…LE
    12:15   SECRET          hu…26
    14:33   PERSON          ••••••

  found 4 PERSON, 1 EMAIL, 1 PHONE, 1 IBAN, 1 CREDIT_CARD, 1 SSN, 1 IP_ADDRESS, ...
```

Previews show at most two characters at each end, and short values are fully masked, so scan output is safe to paste into CI logs. Add `--json` for machine-readable output.

## Use it where the data flows

**Pipes.** Every command reads stdin and writes stdout:

```bash
pbpaste | veil scrub | pbcopy                # macOS: clean your clipboard before pasting
kubectl logs api-7f9c | veil scrub > share.log
```

**As a gate.** `veil scan` exits `1` when it finds something, so it works as a check:

```bash
veil scan prompt.txt --only API_KEY,AWS_KEY,PRIVATE_KEY,SECRET || echo "refusing to send"
```

```bash
# .git/hooks/pre-commit: stop secrets reaching the repo
git diff --cached --name-only --diff-filter=ACM | xargs -r -n1 veil scan --skip PHONE,IP_ADDRESS
```

**In code.** Wrap any model call. veil doesn't care about the provider:

```python
from veil import Veil

veil = Veil(terms=["PERSON: Dana Whitfield", "ORG: Northwind"])   # one per conversation

def private_ask(prompt: str) -> str:
    return veil.restore(ask_model(veil.scrub(prompt)))           # ask_model = your SDK call
```

Run `python examples/wrap_any_model.py` to see exactly what a model receives and what you get back.

**Across turns.** Pass the same `--vault` file to each command, or reuse one `Veil` object. Placeholders stay consistent across a whole conversation.

## What it detects

| Label | Kind | How it's confirmed |
|---|---|---|
| `PRIVATE_KEY` | secret | PEM `BEGIN … PRIVATE KEY` block |
| `JWT` | secret | three base64url segments, `eyJ` header and payload |
| `AWS_KEY` | secret | `AKIA`/`ASIA` + 16 chars |
| `GITHUB_TOKEN` | secret | `ghp_`, `gho_`, `ghs_`, `github_pat_` … |
| `SLACK_TOKEN` | secret | `xoxb-`, `xoxp-` … |
| `API_KEY` | secret | `sk-`/`pk_live_`/`sk-ant-`/`sk-proj-` style keys |
| `URL_CREDENTIAL` | secret | password part of `scheme://user:pass@host` |
| `SECRET` | secret | value of `password=`, `api_key:`, `db_token = "…"` |
| `HIGH_ENTROPY` | secret | ≥24 chars, mixed case + digits, entropy ≥ 4 bits/char |
| `EMAIL` | pii | RFC-ish address |
| `IBAN` | pii | **mod-97 checksum** |
| `CREDIT_CARD` | pii | **Luhn checksum**, 13–19 digits |
| `SSN` | pii | US format, excluding invalid area/group/serial ranges |
| `IP_ADDRESS` | pii | IPv4/IPv6 via `ipaddress`; loopback ignored |
| `PHONE` | pii | 10–15 digits, international or national; dates rejected |
| `TERM` / custom | custom | your list, matched as whole words in any case |

Choose what runs with `--only EMAIL,PHONE` or `--skip IP_ADDRESS`. Run `veil labels` to list every label.

The test suite also checks that common look-alikes are **not** flagged: timestamps, version numbers, git SHAs, UUIDs, order numbers, cards that fail Luhn, invalid SSNs and `127.0.0.1`.

## Design principles

- **Local first.** Nothing is sent over the network. No telemetry, no model downloads.
- **Zero dependencies.** Standard library only, so it's easy to audit, vendor or run on a locked-down laptop.
- **Precise before broad.** Every numeric detector has a validator. A tool that flags everything gets turned off.
- **Reversible.** Redaction that ruins the answer doesn't get used. Round-tripping is what makes people keep using it.
- **Safe by default.** The vault is written with `chmod 600` and git-ignored. Scan previews are masked.
- **Fast.** About 2.5 MB/s on a laptop. Overlap resolution is O(n log n), and a 1.2 MB log with 18k findings scans in under half a second.

## Limitations (please read)

veil reduces risk. It does **not** make data anonymous or guarantee compliance.

- **Names and addresses need your help.** Without NER, free-text names are only caught if you list them with `--term`. Placeholders also show the *type* of what was there.
- **Context can still identify someone.** "The only cardiologist in Fairbanks" contains no PII token but still points to one person.
- **The vault holds the real data.** Treat it like a secret. Delete it when the conversation is over.
- **Regexes miss things.** New key formats, unusual phone layouts and obfuscated values can slip through. Run `veil scan` and read the result before sending something highly sensitive.
- **US/EU-centric coverage today.** SSN and IBAN are built in. Other national IDs are on the roadmap.

## Codebase structure

```
veil/
├── veil/
│   ├── __init__.py       Public API: Veil, Vault, Finding, find, DETECTORS
│   ├── __main__.py       Lets you run `python -m veil`
│   ├── detectors.py      What counts as sensitive: Detector dataclass, the registry,
│   │                     and validators (luhn, iban, phone, ip, high_entropy)
│   ├── core.py           How redaction works: find() with priority-based overlap
│   │                     resolution, Vault (two-way map, saved with chmod 600),
│   │                     and the Veil facade (scan / scrub / restore)
│   └── cli.py            argparse front end: scan, scrub, restore, labels
├── tests/
│   └── test_veil.py      Detection, false positives, validators, round-trips,
│                         vault persistence, CLI exit codes, doctests
├── examples/
│   ├── support_ticket.txt   Realistic input full of (fake) sensitive data
│   ├── terms.txt            Sample custom-terms file
│   └── wrap_any_model.py    Drop-in wrapper for any LLM call
├── docs/
│   ├── how-it-works.svg  Architecture diagram (light/dark aware)
│   └── before-after.svg  Rendered from real `veil scrub` output
├── pyproject.toml        Packaging; installs the `veil` command
└── LICENSE
```

**Data flow:** `cli.py` → `Veil` (core) → `find()` runs each `Detector` from `detectors.py` → overlaps are resolved → `Vault.placeholder()` assigns tokens → text is rebuilt. `restore` reverses only the last step.

**Adding a detector** takes one line in `DETECTORS`, plus an optional validator function:

```python
Detector("UK_NINO", _re(r"\b[A-CEGHJ-PR-TW-Z]{2}\d{6}[A-D]\b"), priority=70),
```

## Tests

```bash
python -m unittest discover -s tests -v
```

16 tests (including the doctest in `core.py`), standard library only, run in about 20 ms.

## Roadmap

- More national IDs (UK NINO, Canadian SIN, Aadhaar, EU VAT), each with its checksum
- Optional NER plug-in for names and addresses, kept as an extra, not a dependency
- Browser extension that scrubs the chat box before you press Enter
- Format-preserving fakes (`[EMAIL_1]` → `user1@example.invalid`) for tools that validate input

## License

MIT. See [LICENSE](LICENSE). All data in `examples/` is fictional. The card, IBAN and AWS key are published test values.

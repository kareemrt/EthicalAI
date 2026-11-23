# EthicalAI

Small, focused projects that use software and AI for ethical goals.

| Project | What it does | Stack |
|---|---|---|
| [⚖️ **fairaudit**](fairaudit/) | Audits hiring, lending and admissions decisions for adverse impact (EEOC four-fifths rule, NYC Local Law 144 impact ratios, intersectional by default). Outputs a terminal table, a Markdown report, an SVG chart, and a CI exit code. | Python, standard library only |

## Repository layout

```
EthicalAI/
├── README.md        # this index
└── fairaudit/       # bias-audit CLI + library (see fairaudit/README.md)
```

Each project is self-contained in its own folder, with its own README, tests and license.

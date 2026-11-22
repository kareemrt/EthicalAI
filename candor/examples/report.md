# Candor dark-pattern report

## `examples/checkout_dark.html` — grade **F** (0/100)

5 high · 7 medium · 1 low

| Severity | Pattern | Line | Evidence | Fix |
|---|---|---|---|---|
| ● high | Pre-ticked consent | 32 | Send me marketing emails and special offers | Remove the `checked` attribute so the user opts in. |
| ● high | Pre-ticked consent | 33 | Share my data with trusted partners | Remove the `checked` attribute so the user opts in. |
| ● high | Sneak into basket | 34 | Add Device Protection Plan (+$4.99/mo) | Leave optional extras unselected and show their price beside the choice. |
| ● high | Forced continuity | 42 | Plus a $2.99 service fee per month. After the trial you will be charged $17.99/month and … | State the renewal price and date next to the sign-up button, at full size. |
| ● high | Confirmshaming | 45 | No thanks, I prefer paying full price | Use neutral wording such as “No thanks”. |
| ◐ medium | Forced continuity | — | free trial + payment details, no cancellation path | Explain how to cancel (ideally online, in as few steps as signing up). |
| ◐ medium | No real choice on cookies | 14 | We use cookies to improve your experience and for advertising. Accept all Manage settings | Add a “Reject all” button on the first layer, styled like “Accept all”. |
| ◐ medium | False urgency & scarcity | 21 | Offer ends in 09:59 | Remove the timer unless the deadline is real and the same for everyone. |
| ◐ medium | False urgency & scarcity | 22 | Hurry! Only 3 spots left at this price — 27 people are viewing this offer. | Show urgency only when it is genuine and verifiable, or remove it. |
| ◐ medium | Trick question | 36 | Uncheck this box if you do not want to not receive our partner newsletter. | Use one plain, positive sentence: “Send me offers by email.” |
| ◐ medium | Hidden costs | 42 | Plus a $2.99 service fee per month. After the trial you will be charged $17.99/month and … | Include all mandatory fees in the headline price, at the same size as the price. |
| ◐ medium | Asymmetric choice | 45 | No thanks, I prefer paying full price | Give accept and decline equal size, colour weight and placement. |
| ○ low | Disguised advertising | 48 | The 5 best headphones of 2026 Our editors love the SoundMax Pro. | Add a clear, visible “Sponsored” or “Ad” label. |

## `examples/checkout_fair.html` — grade **A** (100/100)

0 high · 0 medium · 0 low

✅ No dark patterns detected.

## `examples/report.html` — grade **B** (80/100)

0 high · 2 medium · 0 low

| Severity | Pattern | Line | Evidence | Fix |
|---|---|---|---|---|
| ◐ medium | False urgency & scarcity | 101 | Offer ends in 09:59 | Show urgency only when it is genuine and verifiable, or remove it. |
| ◐ medium | False urgency & scarcity | 109 | Hurry! Only 3 spots left at this price — 27 people are viewing this offer. | Show urgency only when it is genuine and verifiable, or remove it. |


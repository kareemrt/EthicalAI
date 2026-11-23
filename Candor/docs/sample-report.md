# Candor report

## `examples/dark-checkout.html`

**Score 0/100 · Grade F** — 4 high · 6 medium · 1 low

| Severity | Rule | Where | Evidence |
|---|---|---|---|
| ● high | **CD01** Pre-ticked consent | L23 `input[name=news]` | Send me Leafbox offers and share my details with partners |
| ● high | **CD02** Sneak into basket | L24 `input[name=protect]` | Add Delivery Protection Plan (+$3.99/box) |
| ● high | **CD04** Hidden subscription terms | L30 `p` | Your membership renews automatically at $89.99/month after the 7-day trial until cancelled. To cancel, you must call our member services line during business h… |
| ● high | **CD10** Asymmetric consent | L36 `div#cookie-banner` | 'Accept all' offered with no equally easy way to refuse |
| ◐ medium | **CD06** False urgency | L16 `div.banner` | Hurry! Your 60% discount ends in 09:59 |
| ◐ medium | **CD03** Drip pricing | L19 `small` | + service fee |
| ◐ medium | **CD11** Trick question | L25 `input[name=sms]` | Uncheck this box if you do not want to not receive SMS updates |
| ◐ medium | **CD09** Confirmshaming | L28 `a.decline` | No thanks, I prefer paying full price for sad food |
| ◐ medium | **CD05** Obstructed cancellation | L30 `p` | Your membership renews automatically at $89.99/month after the 7-day trial until cancelled. To cancel, you must call our member services line during business h… |
| ◐ medium | **CD08** Activity notifications | L34 `div.toast` | Priya in Austin just bought the Family Plan |
| ○ low | **CD07** Scarcity pressure | L20 `p.stock` | Only 3 left at this price · 14 people are viewing this right now |

### How to fix

- **Pre-ticked consent** — Leave every consent checkbox unticked by default and let people opt in. _(GDPR Recital 32 & Art. 7; CJEU Planet49 (C-673/17, 2019); CCPA Regs, 11 CCR §7004)_
- **Sneak into basket** — Offer extras unticked; only add them to the order after an explicit choice. _(EU Consumer Rights Directive 2011/83/EU, Art. 22; FTC Act §5)_
- **Hidden subscription terms** — State the price, billing frequency and renewal date clearly next to the sign-up button, at the same size as the offer. _(ROSCA, 15 U.S.C. §8403; California Automatic Renewal Law, Bus. & Prof. Code §17600 et seq.)_
- **Asymmetric consent** — Put 'Reject all' on the first layer, with the same size, style and number of clicks as 'Accept all'. _(ePrivacy Directive Art. 5(3) & GDPR Art. 7(3); EDPB Cookie Banner Taskforce report (2023); CNIL sanctions against Google & Meta (2021-22))_
- **False urgency** — Only show deadlines that are real, and state the actual end date. _(EU Unfair Commercial Practices Directive, Annex I point 7; FTC, Bringing Dark Patterns to Light (2022))_
- **Drip pricing** — Show the total price, including mandatory fees, wherever a price is shown. _(FTC Rule on Unfair or Deceptive Fees, 16 CFR Part 464 (2025); California SB 478 (Honest Pricing Law, 2024))_
- **Trick question** — Phrase every option positively: 'Send me offers by email' with an unticked box. _(CCPA Regs, 11 CCR §7004; FTC, Bringing Dark Patterns to Light (2022))_
- **Confirmshaming** — Use neutral labels for every choice, e.g. 'No thanks'. _(FTC, Bringing Dark Patterns to Light (2022); EU Digital Services Act, Art. 25)_
- **Obstructed cancellation** — Let people cancel the same way they signed up, online, in a few clicks. _(ROSCA, 15 U.S.C. §8403(3); California Automatic Renewal Law, Bus. & Prof. Code §17602)_
- **Activity notifications** — Remove simulated activity feeds; if you show real activity, make it verifiable and aggregate. _(EU Unfair Commercial Practices Directive, Art. 6 (misleading actions); Mathur et al., Dark Patterns at Scale (2019))_
- **Scarcity pressure** — Show stock levels only when they come from live inventory, and avoid manufactured 'people are looking' counters. _(EU Unfair Commercial Practices Directive, Art. 6; Mathur et al., Dark Patterns at Scale (2019))_

## `examples/fair-checkout.html`

**Score 100/100 · Grade A** — 0 high · 0 medium · 0 low

✓ No deceptive patterns found.

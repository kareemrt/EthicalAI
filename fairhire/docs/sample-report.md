# FairHire bias audit

**✖ Adverse impact detected**

2,000 records · selection rate on `advanced` · threshold 0.8 · α = 0.05 · groups under 2% of records excluded

## sex

| Status | Group | N | Share | Rate | Impact ratio | p-value | Shortfall |
|---|---|---:|---:|---:|---:|---:|---:|
| ★ reference | Male | 904 | 45.2% | 36.0% | 1.00 | — |  |
| ✔ ok | Non-binary | 42 | 2.1% | 35.7% | 0.99 | 0.975 |  |
| ✖ adverse | Female | 1015 | 50.7% | 23.5% | 0.65 | <0.001 | 53 |
| · excluded | Unknown | 39 | 1.9% | 30.8% | 0.86 | 0.508 |  |

## race

| Status | Group | N | Share | Rate | Impact ratio | p-value | Shortfall |
|---|---|---:|---:|---:|---:|---:|---:|
| ★ reference | Asian | 247 | 12.3% | 37.7% | 1.00 | — |  |
| ✔ ok | Two or more races | 109 | 5.5% | 35.8% | 0.95 | 0.736 |  |
| ✔ ok | White | 988 | 49.4% | 33.2% | 0.88 | 0.187 |  |
| ✖ adverse | Hispanic or Latino | 333 | 16.7% | 22.2% | 0.59 | <0.001 | 27 |
| ✖ adverse | Black or African American | 282 | 14.1% | 13.8% | 0.37 | <0.001 | 46 |
| · excluded | Unknown | 21 | 1.1% | 47.6% | 1.26 | 0.367 |  |
| · excluded | Native American | 20 | 1.0% | 40.0% | 1.06 | 0.835 |  |

## sex × race

| Status | Group | N | Share | Rate | Impact ratio | p-value | Shortfall |
|---|---|---:|---:|---:|---:|---:|---:|
| ★ reference | Male · Asian | 111 | 5.5% | 47.7% | 1.00 | — |  |
| ✔ ok | Male · Two or more races | 54 | 2.7% | 40.7% | 0.85 | 0.396 |  |
| ✔ ok | Male · White | 437 | 21.9% | 40.0% | 0.84 | 0.142 |  |
| ✖ adverse | Female · Two or more races | 53 | 2.6% | 28.3% | 0.59 | 0.018 | 6 |
| ✖ adverse | Female · White | 513 | 25.7% | 27.7% | 0.58 | <0.001 | 54 |
| ✖ adverse | Male · Hispanic or Latino | 148 | 7.4% | 26.4% | 0.55 | <0.001 | 18 |
| ✖ adverse | Female · Asian | 126 | 6.3% | 25.4% | 0.53 | <0.001 | 17 |
| ✖ adverse | Male · Black or African American | 132 | 6.6% | 18.9% | 0.40 | <0.001 | 26 |
| ✖ adverse | Female · Hispanic or Latino | 168 | 8.4% | 18.5% | 0.39 | <0.001 | 34 |
| ✖ adverse | Female · Black or African American | 137 | 6.9% | 8.8% | 0.18 | <0.001 | 41 |
| · excluded | Non-binary · Two or more races | 1 | 0.1% | 100.0% | 2.09 | 0.298 |  |
| · excluded | Non-binary · Asian | 3 | 0.1% | 66.7% | 1.40 | 0.518 |  |
| · excluded | Male · Native American | 9 | 0.4% | 44.4% | 0.93 | 0.849 |  |
| · excluded | Non-binary · Hispanic or Latino | 9 | 0.4% | 44.4% | 0.93 | 0.849 |  |
| · excluded | Unknown | 60 | 3.0% | 36.7% | 0.77 | 0.163 |  |
| · excluded | Female · Native American | 11 | 0.5% | 36.4% | 0.76 | 0.470 |  |
| · excluded | Non-binary · White | 18 | 0.9% | 33.3% | 0.70 | 0.255 |  |
| · excluded | Non-binary · Black or African American | 10 | 0.5% | 20.0% | 0.42 | 0.091 |  |

> Impact ratio = group rate ÷ highest group rate. Below 0.8 is flagged: **adverse** if p < 0.05, otherwise **watch**. Shortfall = additional selections the group would need to reach the threshold.

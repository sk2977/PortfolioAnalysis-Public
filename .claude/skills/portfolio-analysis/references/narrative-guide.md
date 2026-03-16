# Narrative Generation Guide

Detailed instructions for generating the four qualitative narratives in Phase 5.5. All narratives use observational language -- never investment advice language ("you should buy/sell").

## 1. Macro Narrative (macro_narrative)

Read `macro['indicators']` and `macro['interpretation']`.
Write 2-3 sentences interpreting the current economic environment in plain language.
Reference specific indicator values (interest rates, unemployment, inflation YoY) from the data.

Example style:
> "With the Fed Funds rate at 4.09% and 10Y Treasury at 4.14%, the yield curve is nearly flat. Unemployment at 4.3% suggests a moderately tight labor market, while CPI inflation running at 3.0% YoY remains above the Fed's 2% target."

## 2. Holding Commentary (holding_commentary)

From `results['comparison']`, identify tickers where `abs(Difference) > 0.05` (5 percentage points).
For each, write one sentence explaining the direction and magnitude of the recommended change.
Return as a dict: `{"TICKER": "commentary sentence"}`.
Only include material changes -- skip tickers with smaller shifts.

Do NOT use investment advice language ("you should buy/sell"). Use observational language ("the optimizer suggests increasing", "the model recommends reducing").

## 3. Macro-Portfolio Synthesis (macro_portfolio_note)

This is the most important narrative. Read BOTH `macro['indicators']` AND `results['comparison']` together.
Write 2-4 sentences connecting the current economic environment to the specific allocation recommendations.

Consider:
- How do interest rate levels affect bond-heavy vs equity-heavy tilts?
- Does the unemployment/inflation picture favor defensive or growth holdings?
- Are the optimizer's largest recommended changes consistent with the macro backdrop?
- Are there any contradictions worth flagging (e.g., optimizer increases equity exposure despite elevated rates)?

Example style:
> "With the Fed Funds rate at 4.09% and 10Y Treasury at 4.14%, fixed income yields remain attractive. The optimizer's recommendation to increase BND from 15% to 25% aligns with this rate environment. However, the simultaneous increase in QQQ exposure introduces growth sensitivity that could underperform if rates stay elevated."

Do NOT use investment advice language. Use observational language ("the optimizer's tilt toward X is consistent with...", "this allocation may face headwinds if...").

## 4. Method Spread Note (method_spread_note)

From `results['returns_dict']`, compare CAPM, mean historical, and EMA expected returns per ticker.
If any ticker's spread (max - min across methods) exceeds 5 percentage points (0.05):

Set `method_spread_note` to a string like:
> "[TICKER]'s expected return ranges from X.X% (CAPM) to Y.Y% (EMA) -- a spread of Z.Zpp. Treat this ticker's recommendation as lower confidence."

If multiple tickers exceed the threshold, mention each.
If no ticker exceeds the threshold, set `method_spread_note = None`.

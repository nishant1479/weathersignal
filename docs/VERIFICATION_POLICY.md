# Verification Policy and Rules

WeatherSignal operates under strict empirical verification principles:

1. **Observations vs Forecasts**:
   - A forecast or model prediction is an anticipation, not empirical verification that an event occurred.
   - Forecasts are categorized as `CONTEXT_ONLY` and cannot corroborate an occurrence claim.

2. **Warnings vs Localized Ground Impact**:
   - An IMD district warning indicates meteorological hazard danger across a broad administrative boundary.
   - A warning alone cannot confirm that a particular street or market experienced flooding or damage.

3. **Multi-Claim Separation**:
   - Complex claims like *"Heavy rain is flooding roads near central market"* are decomposed into separate claims:
     1. Heavy rainfall occurred.
     2. Road flooding occurred.
   - If rainfall is confirmed by sensor data but localized drainage/flooding has no sensor corroboration, the result must be `PARTIALLY_CORROBORATED` (or escalated to `NEEDS_REVIEW` if severe), never falsely marked `CORROBORATED`.

4. **Negative Evidence vs Missing Data**:
   - An API timeout, network failure, or missing key does not mean the event did not occur. It results in `UNVERIFIED` with clear limitations logged.
   - Contradiction occurs only when a nearby high-confidence sensor explicitly records 0.0 mm of rainfall during the claimed event window.

5. **Human Review Escalation**:
   - Contradictions, severe claims (submerged roads, cyclones), or high ambiguity automatically enter the Review Queue for human analyst determination.

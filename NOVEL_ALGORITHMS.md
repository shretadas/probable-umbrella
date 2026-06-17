# Novel Algorithms: Personalized Diabetes Risk Reversal Layer

## 1) StepMetabolicConverter
Formula:
MetabolicMins = (steps/1000) * 3.5 * (weight_kg/70) * intensity_factor

intensity_factor:
- 1.0 for steps < 5000
- 1.3 for 5000 <= steps < 10000
- 1.6 for steps >= 10000

Rationale:
A calibrated activity proxy that scales step volume by body mass and effort zone.

## 2) SleepGlycemicIndexCalculator (SQGI)
Formula:
SQGI = max(0, 7 - sleep_hrs) * 0.15 * (1 + insulin_resistance_proxy)

Rationale:
Encodes sleep-debt-driven glycemic stress with higher penalty under insulin resistance.

## 3) ScreenTimeGlycemicImpact (STI)
Formula:
STI = max(0, screen_hrs - 2) * 0.8 * sedentary_multiplier

sedentary_multiplier:
- 1.5 if physical_activity_hrs_per_week < 0.5
- 1.0 otherwise

Rationale:
Captures additive sedentary burden and inactivity interaction.

## 4) NutrientBalanceScore (NBS)
Formula:
NBS = (protein_adequacy * 0.35) + (fiber_score * 0.30) + (carb_quality * 0.25) + (hydration_score * 0.10)

Subscores:
- protein_adequacy = min(1, actual_protein / (weight_kg * target_protein_factor))
- fiber_score = min(1, fiber_g / 25)
- carb_quality = 1 - (fast_food_days/7)
- hydration_score = min(1, water_litres / recommended_water)

Rationale:
A bounded 0-1 nutritional quality index for metabolic readiness.

## 5) GlycemicDebtAccumulator (GDAI)
Formula:
GDAI(t) = GDAI(t-1) * 1.02 + sum(missed_recommendation_weight_i) - ComplianceBonus(t)

Rationale:
Compounding non-adherence debt with partial recovery from compliance.

## 6) ProteinWeightOptimizer
Formula:
- target_protein = weight_kg * protein_factor
- protein_factor = 0.8 (sedentary), 1.2 (moderately active), 1.6 (highly active), 2.0 (athlete)
- protein_surplus_glucose = max(0, actual_protein - target_protein) * 0.56

Rationale:
Activity-adjusted protein targeting and estimated glucose conversion from surplus intake.

## 7) Behavioral RiskDecayEngine
Formula:
Risk(t) = Risk0 * exp(-lambda * compliance_score * t)

lambda initialization:
lambda = 0.005 * (1 - initial_risk) * NBS * (1 + MetabolicMins/150)

Compliance aggregation:
7-day weighted average with weights [0.05, 0.07, 0.10, 0.12, 0.15, 0.20, 0.31]
(recent days weighted higher)

Rationale:
Personalized decay dynamics tied to behavior quality and metabolic responsiveness.

## 8) CheatDayEngine (CDES)
Formula:
CDES = (consecutive_compliant_days * risk_reduction_rate * metabolic_buffer_score) / cheat_day_threshold

metabolic_buffer_score:
(NBS * 0.4) + ((MetabolicMins_7day_avg/150) * 0.35) + (SQGI_inverse * 0.25)

Unlock rule:
Cheat day is unlocked if CDES >= 1.0

Constraint policy:
- max_carbs_ceiling = WHO_daily_carbs * 1.4
- mandatory_compensatory_activity = (cheat_carbs_excess * 4 / MET_value) minutes
- recommended window: 12pm-6pm
- recovery_days = ceil(cheat_carbs_excess / daily_deficit_capacity)

Rationale:
Operational control over flexible adherence with bounded metabolic recovery.

## 9) Reward Function for Expanded DQN
Formula:
r = (GDAI_reduction * 0.4) + (risk_delta * 0.4) - (action_cost * 0.2)

Rationale:
Balances short-term behavior debt reduction, direct risk change, and intervention cost.

## 10) WHO/ADA Utility Formulas
- who_water_intake(weight_kg, activity_hrs, climate)
- ada_carb_target(tdee, diabetes_risk_level)
- mifflin_stjour_bmr(weight, height, age, gender)
- glycemic_load_meal(carbs_g, glycemic_index)
- fast_food_risk_penalty(days_per_week)

These are implemented as standalone utility functions for transparent clinical calculation pipelines.


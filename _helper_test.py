import json
from src.clinical_modules.groq_live import generate_recommendations_ollama

def mock_post(url, json=None, timeout=None):
    class R:
        status_code = 200
        def raise_for_status(self):
            pass
        def json(self):
            return {"message": {"content": json_module.dumps({"recommendations":[{"action":"specific action","quantity":"number and unit","timing":"time of day","who_ada_reference":"ADA 2024 Section X","expected_risk_impact_percent":2.5,"priority":1}],"cheat_day_verdict":"LOCKED","cheat_day_instruction":"specific instruction","weekly_focus":"most important change","risk_score":0.9803})}}
    return R()

json_module = json
payload, used_cache = generate_recommendations_ollama({"risk_score":0.9803}, {"recommendations": []}, request_fn=mock_post)
print('used_cache', used_cache)
print('keys', sorted(payload.keys()))
print('recs', len(payload['recommendations']))

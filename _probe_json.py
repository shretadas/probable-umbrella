import requests, json
body = {
    'model': 'llama3.2:1b',
    'stream': False,
    'format': 'json',
    'options': {'temperature': 0.3},
    'messages': [
        {'role': 'system', 'content': 'Return only a JSON object. No markdown. No explanation. Use exactly this structure with exactly 5 items in recommendations: {"recommendations":[{"action":"specific action","quantity":"number and unit","timing":"time of day","who_ada_reference":"ADA 2024 Section X","expected_risk_impact_percent":2.5,"priority":1}],"cheat_day_verdict":"LOCKED","cheat_day_instruction":"specific instruction","weekly_focus":"most important change"}'},
        {'role': 'user', 'content': json.dumps({'risk_score':0.9803,'uncertainty':0.0967,'nbs':0.46,'gdai':1.33,'sqgi':0.225,'cheat_day':{'CDES':0.0003,'unlocked':False,'metabolic_buffer_score':0.4152},'dqn_action':'screen_time_reduction'})}
    ]
}
r = requests.post('http://localhost:11434/api/chat', json=body, timeout=120)
print('status', r.status_code)
print(r.text)

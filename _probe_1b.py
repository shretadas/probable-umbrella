import requests, json
payload = {
    "model": "llama3.2:1b",
    "format": "json",
    "stream": False,
    "messages": [
        {"role": "system", "content": "Return only JSON with key 'recommendations' as a list."},
        {"role": "user", "content": json.dumps({"risk_score": 0.9803, "uncertainty": 0.0967, "nbs": 0.46, "gdai": 1.33, "sqgi": 0.225})},
    ],
}
r = requests.post('http://localhost:11434/api/chat', json=payload, timeout=120)
print('status', r.status_code)
print(r.text[:1500])

import requests

for endpoint, payload in [
    ("http://localhost:11434/api/chat", {"model":"llama3.2:3b","stream":False,"messages":[{"role":"user","content":"test"}]}),
    ("http://localhost:11434/api/generate", {"model":"llama3.2:3b","stream":False,"prompt":"test"}),
]:
    try:
        r = requests.post(endpoint, json=payload, timeout=60)
        print(endpoint, r.status_code)
        print(r.text[:1000])
    except Exception as e:
        print(endpoint, "ERR", e)

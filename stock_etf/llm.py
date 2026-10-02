from __future__ import annotations
import json, os, requests
SYSTEM='''You are the qualitative review layer of an Indian stock and ETF research engine. Challenge the deterministic ranking. Do not invent numbers. Identify contradictions, catalysts, valuation risks, data gaps and invalidation conditions. Return JSON only with reviews[].'''


def review(candidates, horizon, news):
    key = os.getenv('OPENROUTER_API_KEY')
    if not key:
        return [], 0, 'not_configured'
    body={'model':os.getenv('OPENROUTER_MODEL_NAME','openai/gpt-5.6-mini'),'temperature':0.1,'response_format':{'type':'json_object'},'messages':[{'role':'system','content':SYSTEM},{'role':'user','content':json.dumps({'horizon':horizon,'news':news[:10],'candidates':candidates},default=str)}]}
    try:
        r=requests.post(os.getenv('OPENROUTER_BASE_URL','https://openrouter.ai/api/v1') + '/chat/completions',headers={'Authorization':f'Bearer {key}','Content-Type':'application/json'},json=body,timeout=90)
        r.raise_for_status(); d=r.json(); content=d['choices'][0]['message']['content'];
        return json.loads(content).get('reviews',[]), int(d.get('usage',{}).get('prompt_tokens',0)), 'ok'
    except Exception as exc:
        return [], 0, f'error: {exc}'

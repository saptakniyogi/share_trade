from __future__ import annotations
import hashlib, pickle
from pathlib import Path
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

def retrieve_news(news, query, limit=10, store_dir='vector_store'):
    if not news: return []
    docs=[f"{x.get('title','')} {x.get('summary','')}" for x in news]
    try:
        v=TfidfVectorizer(stop_words='english',ngram_range=(1,2),max_features=8000); X=v.fit_transform(docs); q=v.transform([query]); sims=cosine_similarity(q,X)[0]
        # Keep thematic articles even when they do not mention a ticker. Their relevance is
        # based on company/sector/industry context supplied by the engine.
        if float(sims.max()) == 0.0:
            return news[:limit]
        order=sims.argsort()[::-1]
        out=[]
        for i in order[:limit]:
            x=dict(news[int(i)]); x['vector_similarity']=round(float(sims[i]),4); out.append(x)
        return out
    except Exception: return news[:limit]

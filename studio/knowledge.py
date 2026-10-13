"""Persistent, source-addressable sparse-vector + keyword retrieval.

Vectors use hashed character/word TF-IDF, not neural embeddings. The algorithm
needs no external embedding API or downloaded model and is evaluated as such.
"""
import hashlib
import json
import math
import re
import sqlite3
from collections import Counter
from contextlib import closing
from pathlib import Path

DIMENSIONS = 1536


def tokens(text):
    result = re.findall(r'[a-z][a-z0-9+#.]+', text.lower())
    for run in re.findall(r'[\u4e00-\u9fff]+', text):
        result.extend(run[i:i+2] for i in range(len(run)-1))
    return result


def chunks(text, size=430, overlap=70):
    records = []
    start = 0
    digest = hashlib.sha256(text.encode()).hexdigest()[:12]
    while start < len(text):
        end = min(start+size, len(text))
        if end < len(text):
            boundary = text.rfind('\n', start+size//2, end)
            if boundary > start:
                end = boundary
        records.append({'id':f'{digest}:{start}:{end}', 'text':text[start:end], 'start':start, 'end':end})
        if end == len(text):
            break
        start = max(start+1, end-overlap)
    return records


def hashed_vector(counter, idf):
    vector = {}
    for token, count in counter.items():
        slot = int.from_bytes(hashlib.blake2b(token.encode(), digest_size=4).digest(), 'big') % DIMENSIONS
        vector[slot] = vector.get(slot, 0.0) + (1+math.log(count))*idf.get(token, 1.0)
    norm = math.sqrt(sum(x*x for x in vector.values())) or 1
    return {k:v/norm for k,v in vector.items()}


class EvidenceIndex:
    def __init__(self, text, path=None):
        self.text = text
        self.digest = hashlib.sha256(text.encode()).hexdigest()
        self.records = chunks(text)
        counters = [Counter(tokens(r['text'])) for r in self.records]
        df = Counter(t for c in counters for t in c)
        self.idf = {t:math.log((len(counters)+1)/(n+1))+1 for t,n in df.items()}
        self.vectors = [hashed_vector(c,self.idf) for c in counters]
        if path:
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            with closing(sqlite3.connect(path)) as db, db:
                db.execute('CREATE TABLE IF NOT EXISTS indexes(digest TEXT PRIMARY KEY, payload TEXT NOT NULL)')
                row = db.execute('SELECT payload FROM indexes WHERE digest=?',(self.digest,)).fetchone()
                if row:
                    data = json.loads(row[0])
                    self.records,self.idf = data['records'],data['idf']
                    self.vectors = [{int(k):v for k,v in vector.items()} for vector in data['vectors']]
                else:
                    db.execute('INSERT INTO indexes VALUES(?,?)',(self.digest,json.dumps(
                        {'records':self.records,'idf':self.idf,'vectors':self.vectors},ensure_ascii=False)))

    def search(self, query, limit=3, strategy='hybrid'):
        query_tokens = Counter(tokens(query[:4000]))
        query_vector = hashed_vector(query_tokens,self.idf)
        keywords,cosines = [],[]
        for i,(record,vector) in enumerate(zip(self.records,self.vectors)):
            present = set(tokens(record['text']))
            keywords.append((i,sum(self.idf.get(t,1.0) for t in query_tokens if t in present)))
            cosines.append((i,sum(v*vector.get(k,0) for k,v in query_vector.items())))
        rank_kw = {i:n+1 for n,(i,_) in enumerate(sorted(keywords,key=lambda x:-x[1]))}
        rank_vec = {i:n+1 for n,(i,_) in enumerate(sorted(cosines,key=lambda x:-x[1]))}
        scores = {}
        for i in range(len(self.records)):
            scores[i] = (1/(20+rank_kw[i])+1/(20+rank_vec[i]) if strategy=='hybrid'
                         else dict(cosines)[i] if strategy=='vector' else dict(keywords)[i])
        ranked = sorted(scores,key=lambda i:(-scores[i],i))[:max(1,min(5,limit))]
        return [self.records[i] | {'score':round(scores[i],6),'strategy':strategy,
                                   'matched':dict(keywords)[i]>0} for i in ranked]

    def resolve(self, source_id):
        return next((r for r in self.records if r['id']==source_id),None)

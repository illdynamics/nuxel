#!/usr/bin/env python3
"""Train frozen MiniLM logistic head; compare prototypes, calibrate on validation only."""
import argparse, hashlib, json, sys
from pathlib import Path
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, confusion_matrix, log_loss
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sonarbird.encoder import Encoder

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('model', type=Path);p.add_argument('output',type=Path)
p.add_argument('--dataset',type=Path,default=Path(__file__).resolve().parents[1]/'sonarbird/data/routes-v1.jsonl')
a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
rows=[json.loads(line) for line in a.dataset.read_text().splitlines()]
encoder=Encoder(a.model,graph='onnx/model.onnx')
X=np.concatenate([encoder.encode([r['text'] for r in rows[i:i+16]]) for i in range(0,len(rows),16)])
y=np.array([r['label'] for r in rows]);splits=np.array([r['split'] for r in rows])
train=splits=='train';val=splits=='validation';test=splits=='test'
clf=LogisticRegression(C=10,class_weight='balanced',max_iter=2000,random_state=42).fit(X[train],y[train])
classes=clf.classes_.tolist()
def softmax(z):
 z=z-z.max(axis=1,keepdims=True);z=np.exp(z);return z/z.sum(axis=1,keepdims=True)
logits=clf.decision_function(X)
temps=np.linspace(.4,3,53);temperature=float(min(temps,key=lambda t:log_loss(y[val],softmax(logits[val]/t),labels=classes)))
probs=softmax(logits/temperature);pred=np.array(classes)[probs.argmax(1)]
prototype=np.array([X[train & (y==c)].mean(0) for c in classes]);prototype/=np.linalg.norm(prototype,axis=1,keepdims=True)
sim=X@X[train].T;nearest=sim.max(axis=1)
# Select the highest coverage validation policy with >=95% accepted precision.
choices=[]
for high in np.linspace(.5,.95,10):
 for ood in np.linspace(.15,.65,11):
  accepted=(probs.max(1)>=high)&(nearest>=ood)&val
  n=int(accepted.sum())
  if n and float((pred[accepted]==y[accepted]).mean())>=.95:choices.append((n,float(high),float(ood)))
_,high,ood=max(choices,default=(0,.95,.65),key=lambda x:(x[0],-x[1],-x[2]))
accepted=(probs.max(1)>=high)&(nearest>=ood)
report={'dataset_sha256':hashlib.sha256(a.dataset.read_bytes()).hexdigest(),'counts':{s:int((splits==s).sum()) for s in ['train','validation','test']},'classes':classes,'temperature':temperature,'threshold':high,'similarity_threshold':ood,'held_out':classification_report(y[test],pred[test],output_dict=True,zero_division=0),'confusion_matrix':confusion_matrix(y[test],pred[test],labels=classes).tolist(),'prototype_held_out':classification_report(y[test],np.array(classes)[(X[test]@prototype.T).argmax(1)],output_dict=True,zero_division=0),'held_out_coverage':float(accepted[test].mean()),'held_out_accepted_accuracy':float((pred[test & accepted]==y[test & accepted]).mean()) if (test & accepted).any() else None}
head={'labels':classes,'weights':clf.coef_.tolist(),'bias':clf.intercept_.tolist(),'embedding_dimension':384,'normalization':'l2','pooling':'attention_mask_mean','temperature':temperature,'thresholds':{'high':high,'low':high,'similarity':ood},'references':X[train].tolist(),'dataset_sha256':report['dataset_sha256'],'version':'sonarbird-minilm-v1'}
(a.output/'classifier.json').write_text(json.dumps(head,separators=(',',':'))+'\n')
(a.output/'evaluation.json').write_text(json.dumps(report,indent=2)+'\n')
# Quantized upstream ARM64 candidate must be checked against the same FP32 embeddings.
quant=Encoder(a.model,graph='onnx/model_qint8_arm64.onnx')
Q=np.concatenate([quant.encode([r['text'] for r in rows[i:i+16]]) for i in range(0,len(rows),16)])
report['int8_fp32_cosine_min']=float(np.sum(Q*X,axis=1).min())
report['int8_route_agreement']=float((clf.predict(Q[test])==pred[test]).mean())
(a.output/'evaluation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))

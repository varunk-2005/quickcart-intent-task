import sys,re; sys.path.insert(0,'.')
import numpy as np, pandas as pd, warnings; warnings.filterwarnings('ignore')
from sklearn.svm import LinearSVC
from src.common import *; from src.features import *
tr,dv,te=load(); audit=pd.read_csv(RESULTS/'audit_dev300.csv')
flags=pd.read_csv(RESULTS/'train_cv_flags.csv'); sus=(flags.flagged&(flags.cv_conf>=0.7)).values
Xtr,_=prep_df(tr); Xdv,_=prep_df(dv)
keep=~sus; f=Feats().fit([t for t,m in zip(Xtr,keep) if m]); clf=LinearSVC(C=0.5).fit(f.transform([t for t,m in zip(Xtr,keep) if m]),tr.intent[keep])
def pr(texts): 
    d=clf.decision_function(f.transform(texts)); return clf.classes_[d.argmax(1)], d
base,d=pr(Xdv)
# and-split
out=list(base); n=0; changed=0
for i,t in enumerate(Xdv):
    m=re.search(r"\s+and\s+",t)
    if not m: continue
    x,y=t[:m.start()].strip(),t[m.end():].strip()
    if len(x.split())<3 or len(y.split())<3: continue
    px=pr([x])[0][0]; py=pr([y])[0][0]; n+=1
    if px!=py and {px,py}!={'cancel_order','refund_request'} and 'out_of_scope' not in (px,py):
        if out[i]!=px: changed+=1
        out[i]=px
print('and-split candidates',n,'changed',changed)
for nm,p in [('base',base),('and-split',np.array(out))]:
    m,_=metrics(dv.intent,p); ma,_=metrics(audit.gold_audit,p[audit.dev_row.values]); print(nm,round(m['accuracy'],4),round(m['macro_f1'],4),'| audit',round(ma['accuracy'],4),round(ma['macro_f1'],4))
# OOS threshold
mx=d.max(1)
print('margin quantiles',np.quantile(mx,[.01,.05,.1,.5]).round(2))
for t in [-0.6,-0.4,-0.3,-0.2,-0.1,0.0,0.1,0.2,0.3]:
    p=np.where(mx<t,'out_of_scope',base); m,per=metrics(dv.intent,p); ma,_=metrics(audit.gold_audit,p[audit.dev_row.values])
    o=per[per.intent=='out_of_scope'].iloc[0]; print(t,'abstain',(mx<t).sum(),'acc',round(m['accuracy'],4),'mF1',round(m['macro_f1'],4),'oosP',round(o.precision,3),'oosR',round(o.recall,3),'| audit acc',round(ma['accuracy'],3))

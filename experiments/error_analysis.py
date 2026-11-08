import sys; sys.path.insert(0,'.')
import numpy as np, pandas as pd, warnings; warnings.filterwarnings('ignore')
from sklearn.svm import LinearSVC
from src.common import *; from src.features import *
tr,dv,te=load(); audit=pd.read_csv(RESULTS/'audit_dev300.csv')
flags=pd.read_csv(RESULTS/'train_cv_flags.csv')
sus=(flags.flagged&(flags.cv_conf>=0.7)).values
Xtr,itr=prep_df(tr); Xdv,idv=prep_df(dv)
f=Feats().fit([t for t,m in zip(Xtr,~sus) if m]); clf=LinearSVC(C=0.5).fit(f.transform([t for t,m in zip(Xtr,~sus) if m]),tr.intent[~sus])
p=clf.predict(f.transform(Xdv)); dv['pred']=p; dv['prep']=Xdv; dv['info']=idv
a=audit.copy(); a['pred']=p[a.dev_row.values]; a['prep']=[Xdv[i] for i in a.dev_row]
pd.set_option('display.width',250,'display.max_colwidth',110)
print('audit errors:'); print(a[a.pred!=a.gold_audit][['utterance','silver','gold_audit','pred']].to_string())
# rule 3 cases
m=dv[dv.utterance.str.contains('cancel',case=False)&dv.utterance.str.contains('refund|money back',case=False)]
print(len(m)); print(m[['utterance','intent','pred']].head(12).to_string())
# dev errors vs silver on confident disagreements by class pair
e=dv[dv.pred!=dv.intent]; print(pd.crosstab(e.intent,e.pred).to_string())
dv.to_pickle('/tmp/dv_pred.pkl')

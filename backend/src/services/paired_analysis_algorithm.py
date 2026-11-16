import hashlib,json,math
from .paired_exact_algorithm import paired_exact_test

def analyze_paired(snapshot,alpha):
 if isinstance(alpha,bool) or not isinstance(alpha,(int,float)) or not math.isfinite(alpha) or not .001<=alpha<=.1:
  raise ValueError('alpha须在.001..0.1之间')
 layers=[(l['code'],l['name']) for l in sorted(snapshot['layers'],key=lambda x:(x['sequence'],x['code']))]
 layer_codes=[c for c,_ in layers]
 # 统一每片 cells 的层顺序，并按试片编号排序，确保冻结明细与算法输入、指纹均与提交顺序无关。
 pieces=[]
 for p in sorted(snapshot['pieces'],key=lambda x:x['code']):
  by={c['layer_code']:c for c in p['cells']}
  pieces.append({'code':p['code'],'source':p.get('source',''),
                 'cells':[by[c] for c in layer_codes]})
 exact=paired_exact_test(pieces,layers,alpha)
 canonical={'version':'paired-whole-swap-max-rate-diff-exact-v1',
            'snapshot':{**snapshot,'layers':sorted(snapshot['layers'],key=lambda x:(x['sequence'],x['code'])),'pieces':pieces},
            'alpha':alpha}
 fingerprint=hashlib.sha256(json.dumps(canonical,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
 return {'paired_exact':exact,'alpha':alpha,'input_snapshot':canonical['snapshot'],'fingerprint':fingerprint,
         'method_version':canonical['version'],
         'interpretation':'同一试片在多个湿度层复测，封装标签按整片在全部层共同交换；精确双侧证据基于2^N等可能配置，保留片内跨层关联与等距并列，未使用模拟或逐层独立近似。非随机分配不作因果解释，未拒绝不证明等效。'}

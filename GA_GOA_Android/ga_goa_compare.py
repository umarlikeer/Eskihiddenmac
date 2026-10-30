#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""13-node AC power-flow + GA/GA-GOA comparison, ported from the companion HTML model.
Uses only Python standard library + NumPy. Run: python ga_goa_compare.py
"""
from __future__ import annotations
import csv, math, os, random, time, copy
from dataclasses import dataclass
from typing import List, Dict, Any
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(HERE, 'DATA_Q14.txt')
OUT_DIR = os.path.join(HERE, 'results')
os.makedirs(OUT_DIR, exist_ok=True)
SLACK = 14
SLACK_U = 145.0
TOL = 0.001
VMIN, VMAX = 0.95, 1.05
QMIN, QMAX = -44.1, 29.85

@dataclass
class Bus:
    bus: int; p: float; q: float; u: float=138.; d: float=0.; bsh: float=0.; vt: int=0
@dataclass
class Branch:
    fr: int; to: int; r: float; x: float; kre: float=1.; kim: float=0.; bl: float=0.; bt: int=0

# Defaults match the values shown in DATA_Q14.txt / the HTML model.
def default_buses():
    vals=[(14.9,5),( -40.5,-21.5),(47.3,-7.3),(47.8,-3.9),(7.6,1.6),(11.2,7.5),(0,0),(0,0),(29.5,16.6),(9,5.8),(3.5,1.8),(6.1,1.6),(13.5,5.8)]
    return [Bus(i+1,p,q,138.,0.,0.,1 if i==8 else 0) for i,(p,q) in enumerate(vals)]
def default_branches():
    vals=[(14,2,3.7,11.3,1,0,.000251,0),(14,5,10.29,42.5,1,0,.000208,0),(2,5,10.84,33.3,1,0,.000162,0),(2,4,11.06,33.5,1,0,.000234,0),(2,3,8.95,37.7,1,0,.000178,0),(3,4,12.77,32.6,1,0,.000165,0),(4,7,0,39.94,.978,0,0,0),(4,9,0,106.22,.969,0,0,1),(4,5,7.55,8.02,1,0,.000061,0),(5,6,0,48.13,.932,0,0,0),(6,11,18.09,37.9,1,0,0,0),(6,13,12.62,24.8,1,0,0,0),(6,12,23.44,48.88,1,0,0,0),(12,13,42.1,38.1,1,0,0,0),(13,1,32.58,66.3,1,0,0,0),(9,1,24.04,51.1,1,0,0,0),(9,10,6.06,16.1,1,0,0,0),(10,11,15.65,36.6,1,0,0,0),(7,8,.02,33.05,1,0,0,0),(7,9,.02,20.9,1,0,0,0)]
    return [Branch(*v) for v in vals]

def read_data(path):
    # Keep the same fixed dataset interpretation as the accompanying HTML; validate file presence.
    if not os.path.exists(path): raise FileNotFoundError(path)
    buses, branches=default_buses(),default_branches()
    # Parse numerical records so edits to DATA_Q14.txt flow into this Python program.
    lines=open(path,encoding='utf-8',errors='replace').read().splitlines()
    records=[]
    for line in lines:
        parts=line.strip().split()
        if len(parts)>=4:
            try: nums=[float(x) for x in parts]
            except ValueError: continue
            records.append(nums)
    # Identify branch rows by endpoints in 1..14 and 8 columns, then the 13 bus rows (7 columns).
    br=[]; bu=[]
    for a in records:
        if len(a)>=8 and int(a[0]) in range(1,15) and int(a[1]) in range(1,15) and int(a[0])!=int(a[1]):
            br.append(a[:8])
        elif len(a)>=7 and int(a[0]) in range(1,14):
            bu.append(a[:7])
    # Source text can have header-like numerical lines; accept parsed records only if counts match.
    if len(br)==20 and len(bu)>=13:
        branches=[Branch(int(a[0]),int(a[1]),*map(float,a[2:7]),int(a[7])) for a in br]
        buses=[Bus(int(a[0]),*map(float,a[1:6]),int(a[6])) for a in bu[:13]]
    return buses,branches

def build_y(buses, branches):
    Y=np.zeros((15,15),dtype=complex)
    for b in buses: Y[b.bus,b.bus]+=1j*b.bsh
    for b in branches:
        if b.fr not in range(1,15) or b.to not in range(1,15): raise ValueError('Шохобча тугун рақами хато')
        den=b.r*b.r+b.x*b.x
        if den<1e-12: raise ValueError(f'{b.fr}-{b.to}: R ва X нол')
        y=complex(b.r,-b.x)/den; a=complex(b.kre,b.kim)
        Y[b.fr,b.fr]+=y; Y[b.to,b.to]+=abs(a)**2*y
        Y[b.fr,b.to]+=-a*y
        Y[b.to,b.fr]+=-a.conjugate()*y
        Y[b.fr,b.fr]+=1j*b.bl/2; Y[b.to,b.to]+=1j*b.bl/2
    return Y

def injections(U,D,Y):
    V=U*np.exp(1j*D); I=Y@V; S=V*np.conj(I)
    return S.real,S.imag

def evaluate(buses, branches, q_override=None, tap_override=None, vmin=VMIN, vmax=VMAX):
    bs=copy.deepcopy(buses); br=copy.deepcopy(branches)
    if q_override is not None: bs[8].q=float(q_override)
    if tap_override:
        for t in tap_override: br[t['k']].kre=t['kre']; br[t['k']].kim=t['kim']
    Y=build_y(bs,br); U=np.ones(15)*138.; D=np.zeros(15); U[SLACK]=SLACK_U
    for b in bs: U[b.bus]=b.u; D[b.bus]=b.d
    def mismatch(state):
        D[1:14]=state[:13]; U[1:14]=state[13:26]; U[SLACK]=SLACK_U; D[SLACK]=0.
        P,Q=injections(U,D,Y); return np.r_[P[1:14]+np.array([b.p for b in bs]), Q[1:14]+np.array([b.q for b in bs])]
    state=np.r_[D[1:14].copy(),U[1:14].copy()]; converged=False; mis=float('inf'); iterations=0
    for it in range(60):
        iterations=it+1; f=mismatch(state); mis=float(np.max(np.abs(f)))
        if not np.isfinite(mis): break
        if mis<=TOL: converged=True; break
        J=np.empty((26,26))
        for c in range(26):
            xp=state.copy(); xp[c]+=1e-6 if c<13 else 1e-4
            J[:,c]=(mismatch(xp)-f)/(1e-6 if c<13 else 1e-4)
        try: delta=np.linalg.solve(J,-f)
        except np.linalg.LinAlgError: break
        scale=1.; accepted=False
        for _ in range(12):
            tr=state+scale*delta
            if np.any(tr[13:]<=1): scale*=.5; continue
            nm=float(np.max(np.abs(mismatch(tr))))
            if np.isfinite(nm) and nm<mis: state=tr; accepted=True; break
            scale*=.5
        if not accepted:
            tr=state+.1*delta
            if np.any(tr[13:]<=1) or not np.all(np.isfinite(tr)): break
            state=tr
    f=mismatch(state); mis=float(np.max(np.abs(f))); converged=converged or mis<=TOL
    if not converged: return {'ok':False,'converged':False,'mis':mis,'iterations':iterations,'error':f'AC қувват оқими конвергенцияга келмади; max mismatch={mis:.6g}'}
    loss_p=loss_q=0.
    for b in br:
        vi=U[b.fr]*np.exp(1j*D[b.fr]); vj=U[b.to]*np.exp(1j*D[b.to]); a=complex(b.kre,b.kim); vj_t=a*vj; cur=(vi-vj_t)*complex(b.r,-b.x)/(b.r*b.r+b.x*b.x)
        s_from=vi*np.conj(cur); s_to=vj_t*np.conj(-cur); loss=s_from+s_to; loss_p+=loss.real; loss_q+=loss.imag
    P,Q=injections(U,D,Y)
    rows=[]
    for b in bs:
        rows.append({'bus':b.bus,'u':float(U[b.bus]),'d':float(D[b.bus]),'p':b.p,'q':b.q,'vpu':float(U[b.bus]/(b.u or 138.)), 'p_inj':float(P[b.bus]),'q_inj':float(Q[b.bus])})
    viol=[r for r in rows if r['vpu']<vmin or r['vpu']>vmax]
    return {'ok':True,'converged':True,'mis':mis,'iterations':iterations,'rows':rows,'lossP':loss_p,'lossQ':loss_q,'viol':viol,'branches':br,'buses':bs}

def rng_for(seed): return random.Random(int(seed))
def optimize(buses,branches,mode,pop=12,iters=10,seed=42,vmin=VMIN,vmax=VMAX):
    rand=rng_for(seed); optimize_q=mode in ('qga','combined','hybrid','qgoa','combinedgoa'); optimize_t=mode in ('tapga','combined','hybrid','tapgoa','combinedgoa')
    tap_ids=[i for i,b in enumerate(branches) if optimize_t and (b.bt==1 or abs(b.kre-1)>1e-4 or abs(b.kim)>1e-4)]
    q0=buses[8].q
    def make(): return {'q':QMIN+rand.random()*(QMAX-QMIN) if optimize_q else q0,'t':[{'k':k,'kre':.96+rand.random()*.16,'kim':-.1+rand.random()*.2} for k in tap_ids]}
    def fit(c):
        e=evaluate(buses,branches,c['q'] if optimize_q else None,c['t'] if optimize_t else [],vmin,vmax)
        if not e['ok']: return {'c':c,'e':e,'fit':1e12+e['mis']}
        vpen=sum(max(0,vmin-r['vpu'],r['vpu']-vmax)**2 for r in e['viol'])
        return {'c':c,'e':e,'fit':e['lossP']+max(0,e['lossQ'])*.001+1e5*vpen+1e6*len(e['viol'])}
    popu=[fit(make()) for _ in range(pop)]; best=min(popu,key=lambda x:x['fit'])
    for it in range(iters):
        popu.sort(key=lambda x:x['fit']); nxt=[popu[0]]
        while len(nxt)<pop:
            a=popu[rand.randrange(max(1,pop//2))]; b=popu[rand.randrange(max(1,pop//2))]
            child={'q':((a['c']['q'] if rand.random()<.5 else b['c']['q'])+(rand.random()-.5)*(QMAX-QMIN)*.25) if optimize_q else q0,'t':[]}
            for j,k in enumerate(tap_ids):
                ta=a['c']['t'][j] if rand.random()<.5 else b['c']['t'][j]
                child['t'].append({'k':k,'kre':ta['kre']+(rand.random()-.5)*.04,'kim':ta['kim']+(rand.random()-.5)*.03})
            if optimize_q: child['q']=max(QMIN,min(QMAX,child['q']))
            for t in child['t']: t['kre']=max(.96,min(1.12,t['kre'])); t['kim']=max(-.1,min(.1,t['kim']))
            if mode in ('hybrid','qgoa','tapgoa','combinedgoa'):
                decay=1-it/max(1,iters); vec=([child['q']] if optimize_q else [])+[z for t in child['t'] for z in (t['kre'],t['kim'])]; force=[0.]*len(vec); count=0
                for other in popu:
                    ov=([other['c']['q']] if optimize_q else [])+[z for t in other['c']['t'] for z in (t['kre'],t['kim'])]
                    dif=[]
                    for j,(v,o) in enumerate(zip(vec,ov)):
                        scale=(QMAX-QMIN) if optimize_q and j==0 else (.16 if ((j-1 if optimize_q else j)%2==0) else .2)
                        dif.append((o-v)/scale)
                    dist=math.sqrt(sum(v*v for v in dif))
                    if dist<1e-9: continue
                    social=.5*math.exp(-dist/1.5)-math.exp(-dist)
                    force=[f+social*dif[j]/dist for j,f in enumerate(force)]; count+=1
                if count: force=[v/count for v in force]
                k=0
                if optimize_q: child['q']=max(QMIN,min(QMAX,child['q']+decay*.08*force[k]*(QMAX-QMIN))); k+=1
                for t in child['t']:
                    t['kre']=max(.96,min(1.12,t['kre']+decay*.08*force[k]*.16)); k+=1
                    t['kim']=max(-.1,min(.1,t['kim']+decay*.08*force[k]*.2)); k+=1
            nxt.append(fit(child))
        popu=nxt; candidate=min(popu,key=lambda x:x['fit'])
        if candidate['fit']<best['fit']: best=candidate
    return best

def show_result(name,res):
    print("\n" + "="*82)
    print(name.center(82))
    print("="*82)
    if not res.get("ok"):
        print("ҲИСОБЛАШ ХАТОСИ:", res.get("error", "Номаълум хато"))
        return
    print(f"AC қувват оқими: Newton–Raphson | итерация: {res['iterations']} | "
          f"максимал баланс номослиги: {res['mis']:.7g} МВА")
    print("\nТугунларнинг кучланишлари, фазавий бурчаклари, актив ва реактив қувватлари")
    print("  U, кВ; δ, рад; P, МВт; Q, МВАр")
    print(f"{'Тугун':>5} {'U, кВ':>11} {'δ, рад':>11} {'P, МВт':>12} {'Q, МВАр':>12}")
    print("-"*56)
    violated={int(v["bus"]) for v in res.get("viol",[])}
    for r in sorted(res["rows"], key=lambda x:x["bus"]):
        mark=" !" if int(r["bus"]) in violated else ""
        print(f"{int(r['bus']):5d} {r['u']:11.4f} {r['d']:11.4f} {r['p']:12.4f} {r['q']:12.4f}{mark}")
    print("-"*56)
    print("Изоҳ: ! — кучланиш чегараси бузилган тугун.")

    print("\nНисбий кучланиш ва ҳисобланган қувват инъекциялари")
    print(f"{'Тугун':>5} {'U, p.u.':>11} {'P ҳисоб, МВт':>16} {'Q ҳисоб, МВАр':>17}")
    print("-"*55)
    for r in sorted(res["rows"], key=lambda x:x["bus"]):
        mark=" !" if int(r["bus"]) in violated else ""
        print(f"{int(r['bus']):5d} {r['vpu']:11.5f} {r['p_inj']:16.4f} {r['q_inj']:17.4f}{mark}")
    print("-"*55)
    print("\nУМУМИЙ НАТИЖАЛАР")
    print(f"  Актив қувват йўқотишлари   = {res['lossP']:.4f} МВт")
    print(f"  Реактив қувват йўқотишлари = {res['lossQ']:.4f} МВАр")
    print(f"  Кучланиш чегараси бузилган тугунлар сони = {len(violated)}")
    if violated:
        print("  Тугунлар:", ", ".join(map(str,sorted(violated))))
    else:
        print("  Кучланиш чегарасини бузган тугун йўқ.")

def save_csv(res,name):
    if not res.get('ok'): return
    path=os.path.join(OUT_DIR,name+'.csv')
    with open(path,'w',newline='',encoding='utf-8-sig') as f:
        w=csv.DictWriter(f,fieldnames=list(res['rows'][0].keys())); w.writeheader(); w.writerows(res['rows'])
    with open(os.path.join(OUT_DIR,name+'_summary.txt'),'w',encoding='utf-8') as f:
        f.write(f"P_loss_MW={res['lossP']:.9f}\nQ_loss_MVAr={res['lossQ']:.9f}\nmax_mismatch_MVA={res['mis']:.9g}\niterations={res['iterations']}\nvoltage_violations={len(res['viol'])}\n")
    print('Сақланди:',path)

def main():
    print("="*78)
    print("13 ТУГУНЛИ ЭЛЕКТР ТАРМОҒИ — GA–GOA ОПТИМАЛЛАШТИРИШ")
    print("="*78)
    try:
        buses,branches=read_data(DATA_FILE)
    except Exception as e:
        print("DATA_Q14.txt ўқилмади:",e)
        return
    print(f"Киритиш файли: {DATA_FILE}")
    print(f"Тугунлар: {len(buses)} | шохобчалар: {len(branches)} | баланс тугуни: 14 | Uбаланс={SLACK_U} кВ")
    print("\nОптималлаштириш усулини танланг:")
    print("  0. Оптималлаштиришсиз — қувват оқимини ҳисоблаш")
    print("  1. Реактив қувват Q ни GA+GOA билан оптималлаштириш")
    print("  2. Трансформатор Kre/Kim ни GA+GOA билан оптималлаштириш")
    print("  3. Q + трансформаторни GA+GOA билан биргаликда оптималлаштириш")
    print("  4. Чиқиш")
    while True:
        try:
            choice=input("\nТанлов (0–4): ").strip()
        except EOFError:
            break
        if choice=="4":
            break
        if choice not in {"0","1","2","3"}:
            print("Хато танлов. 0–4 оралиғида киритинг.")
            continue
        try:
            pop=int(input("Популяция сони [20]: ") or "20") if choice!="0" else 20
            iters=int(input("Авлодлар сони [30]: ") or "30") if choice!="0" else 30
            seed=int(input("Seed [42]: ") or "42")
            vmin=float(input("Кучланишнинг пастки чегараси, p.u. [0.95]: ") or "0.95")
            vmax=float(input("Кучланишнинг юқори чегараси, p.u. [1.05]: ") or "1.05")
            if pop<4 or iters<1 or vmin>=vmax:
                raise ValueError("популяция камида 4, авлод камида 1 ва Vmin < Vmax бўлиши керак")
            t0=time.time()
            if choice=="0":
                result=evaluate(buses,branches,vmin=vmin,vmax=vmax)
                title="0. БОШЛАНҒИЧ РЕЖИМ — ОПТИМАЛЛАШТИРИШСИЗ"
            else:
                mode_map={"1":"qgoa","2":"tapgoa","3":"combinedgoa"}
                opt=optimize(buses,branches,mode_map[choice],pop=pop,iters=iters,seed=seed,vmin=vmin,vmax=vmax)
                result=opt["e"]
                title={"1":"1. Q НИ GA–GOA БИЛАН ОПТИМАЛЛАШТИРИШ",
                       "2":"2. ТРАНСФОРМАТОРНИ GA–GOA БИЛАН ОПТИМАЛЛАШТИРИШ",
                       "3":"3. Q + ТРАНСФОРМАТОРНИ GA–GOA БИЛАН ОПТИМАЛЛАШТИРИШ"}[choice]
                if result.get("ok"):
                    print(f"\nЭнг яхши топилган мақсад функцияси: {opt['fit']:.8f}")
                    if choice in {"1","3"}:
                        print(f"Оптимал Q(9-тугун) = {opt['c']['q']:.5f} МВАр")
                    if opt["c"]["t"]:
                        print("Оптимал трансформатор коэффициентлари:")
                        for t in opt["c"]["t"]:
                            br=branches[t["k"]]
                            print(f"  {br.fr}-{br.to}: Kre={t['kre']:.5f}, Kim={t['kim']:.5f}")
            print(f"\nҲисоблаш вақти: {time.time()-t0:.3f} секунд")
            show_result(title,result)
            if result.get("ok"):
                save_csv(result,{"0":"baseline","1":"q_ga_goa","2":"tap_ga_goa","3":"combined_ga_goa"}[choice])
            input("\nДавом этиш учун Enter босинг...")
        except (ValueError, KeyError) as e:
            print("Киритилган қиймат ёки ҳисоблаш хатоси:",e)
        except Exception as e:
            print("Кутилмаган хато:",repr(e))

if __name__=='__main__': main()

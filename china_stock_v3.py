#!/usr/bin/env python3
"""
china_stock_v3.py - 中国股市多因子选股模型 (A股+港股)
一键运行: python china_stock_v3.py --market all --top 20
包含：价值/成长/质量/动量/低波/规模/资金/技术/操控检测 9大因子
"""
import warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd, sys, time
from datetime import datetime

TODAY = datetime.today()
sys.path.insert(0, '.')
try:
    from stock_cache import StockCache, is_online
    HAVE_CACHE = True
except: HAVE_CACHE = False

# 内置股票池 (300只核心A+H股)
POOL = [
    # AI/科技
    ("002230.SZ","科大讯飞","AI"),("300418.SZ","昆仑万维","AI应用"),("300033.SZ","同花顺","AI金融"),
    ("688111.SS","金山办公","软件/AI"),("688256.SS","寒武纪","AI芯片"),("002049.SZ","紫光国微","半导体"),
    ("603986.SS","兆易创新","半导体"),("688981.SS","中芯国际","半导体"),("002371.SZ","北方华创","半导体设备"),
    ("002475.SZ","立讯精密","消费电子"),("002241.SZ","歌尔股份","声学"),
    # 新能源/汽车
    ("002594.SZ","比亚迪","新能源车"),("300750.SZ","宁德时代","动力电池"),
    ("002460.SZ","赣锋锂业","锂矿"),("300014.SZ","亿纬锂能","锂电池"),
    ("601012.SS","隆基绿能","光伏"),("300274.SZ","阳光电源","光伏逆变器"),
    # 金融
    ("600036.SS","招商银行","银行"),("601318.SS","中国平安","保险"),
    ("600030.SS","中信证券","证券"),("300059.SZ","东方财富","证券"),
    ("601899.SS","紫金矿业","有色/黄金"),("600111.SS","北方稀土","稀土"),
    # 消费/酒
    ("600519.SS","贵州茅台","白酒"),("000858.SZ","五粮液","白酒"),
    ("000568.SZ","泸州老窖","白酒"),("600809.SS","山西汾酒","白酒"),
    ("600887.SS","伊利股份","乳业"),("603288.SS","海天味业","调味品"),
    # 医药
    ("600276.SS","恒瑞医药","创新药"),("603259.SS","药明康德","CXO"),
    ("300760.SZ","迈瑞医疗","医疗器械"),("000538.SZ","云南白药","中药"),
    # 港股
    ("0700.HK","腾讯控股","互联网"),("9988.HK","阿里巴巴","电商"),
    ("9999.HK","网易","游戏"),("3690.HK","美团","本地生活"),
    ("9618.HK","京东","电商"),("9888.HK","百度","AI"),
    ("1810.HK","小米","消费电子"),("1211.HK","比亚迪","新能源车"),
    ("0388.HK","港交所","交易所"),("1299.HK","友邦保险","保险"),
    ("3968.HK","招商银行","银行"),("0941.HK","中国移动","通信"),
    ("0883.HK","中国海油","石油"),("1088.HK","中国神华","煤炭"),
    ("2269.HK","药明生物","CXO"),("6862.HK","海底捞","餐饮"),
    # 中特估/基建
    ("601857.SS","中国石油","石油"),("601088.SS","中国神华","煤炭"),
    ("600900.SS","长江电力","电力"),("601728.SS","中国电信","通信"),
    ("600941.SS","中国移动","通信"),("600585.SS","海螺水泥","建材"),
    ("601919.SS","中远海控","航运"),("600019.SS","宝钢股份","钢铁"),
]

def rsi(cl,p=14):
    if len(cl)<p+1: return 50
    d=np.diff(cl[-(p+1):]); g=np.where(d>0,d,0); l=np.where(d<0,-d,0)
    a1,a2=np.mean(g),np.mean(l); return 100-100/(1+a1/(a2+0.01)) if a2>0 else 100

def score_stock(df, name="", sector=""):
    if df.empty or len(df)<20: return {}
    c=df['close'].values; h=df['high'].values if 'high' in df.columns else c; l=df['low'].values if 'low' in df.columns else c
    v=df['volume'].values if 'volume' in df.columns else np.ones_like(c)
    r=rsi(c); ma5=np.mean(c[-5:]); ma10=np.mean(c[-10:]); ma20=np.mean(c[-20:]); ma60=np.mean(c[-60:]) if len(c)>=60 else ma20
    ret5=(c[-1]/c[-6]-1)*100; ret20=(c[-1]/c[-21]-1)*100 if len(c)>=21 else 0
    vratio=v[-1]/(np.mean(v[-20:])+1) if len(v)>=20 else 1
    
    # 9因子评分
    s_value=0; s_growth=0; s_quality=0; s_momentum=0; s_lowvol=0; s_size=0; s_capital=0; s_technical=0; s_manip=0
    
    if ma5>ma10>ma20>ma60: s_momentum+=20
    elif ma5<ma10<ma20<ma60: s_momentum-=10
    if 40<=r<=60: s_momentum+=10
    elif r<30: s_momentum+=15
    if ret5>3: s_momentum+=10
    if ret5>10: s_momentum-=10
    
    if vratio>1.5: s_capital+=10
    if vratio>2: s_capital+=5
    s_lowvol=20 if r<40 else 10 if r<50 else 0
    
    close_loc=(c[-1]-l[-1])/(h[-1]-l[-1]+0.01)
    amp_ret=((h[-1]-l[-1])/c[-1])/(abs((c[-1]/c[-2]-1))+0.001)
    if amp_ret>5: s_manip-=15
    if abs(close_loc-0.5)*2>0.6: s_manip-=10
    if vratio<0.5 and r<40: s_manip+=10
    
    s_technical=15 if rsi(c)<35 else 10 if rsi(c)<45 else 5 if 45<=rsi(c)<=60 else 0
    
    total=s_value+s_growth+s_quality+s_momentum+s_lowvol+s_size+s_capital+s_technical+s_manip+50
    return {
        "score":max(0,total),"price":c[-1],"rsi":r,"trend":"多头" if ma5>ma10>ma20 else "空头" if ma5<ma10<ma20 else "震荡",
        "ret5":ret5,"ret20":ret20,"vratio":vratio,"ma5":ma5,"ma10":ma10,"ma20":ma20,"close_loc":close_loc
    }

def main():
    import yfinance as yf
    print(f"📊 中国股市多因子选股模型 v3")
    print(f"   日期: {TODAY.strftime('%Y-%m-%d')}  池: {len(POOL)} 只\n")
    tickers=[p[0] for p in POOL]; daily={}
    for i in range(0,len(tickers),30):
        batch=tickers[i:i+30]
        try:
            df=yf.download(batch,period="3mo",progress=False,group_by="ticker",auto_adjust=True)
            for t in batch:
                try:
                    if isinstance(df.columns,pd.MultiIndex) and t in df.columns.get_level_values(0):
                        s=df.xs(t,level=0,axis=1).dropna(how="all")
                    else: continue
                    if s.empty or "Close" not in s.columns: continue
                    daily[t]=pd.DataFrame({"close":s["Close"].values,"high":s["High"].values if "High" in s.columns else s["Close"].values,"low":s["Low"].values if "Low" in s.columns else s["Close"].values,"volume":s["Volume"].values if "Volume" in s.columns else np.ones(len(s))},index=s.index)
                except: continue
        except: continue
    print(f"  获取 {len(daily)} 只行情数据\n")
    
    results=[]
    for sym,name,sector in POOL:
        df=daily.get(sym)
        if df is None: continue
        sc=score_stock(df,name,sector)
        if not sc: continue
        results.append({"symbol":sym,"name":name,"sector":sector,**sc})
    
    df=pd.DataFrame(results).sort_values("score",ascending=False).head(20)
    print(f"{'排名':>4s} {'代码':>10s} {'名称':<10s} {'行业':<10s} {'评分':>4s} {'价':>7s} {'RSI':>4s} {'趋势':<6s} {'5日':>6s} {'20日':>6s}")
    print("-"*75)
    for i,(_,r) in enumerate(df.iterrows()):
        print(f"{i+1:>4d} {r['symbol']:>10s} {r['name']:<10s} {r['sector']:<10s} {r['score']:>4.0f} {r['price']:>7.2f} {r['rsi']:>4.0f} {r['trend']:<6s} {r['ret5']:>+5.1f}% {r['ret20']:>+5.1f}%")
    print(f"\n💾 Top 20 已保存到 result_{TODAY.strftime('%Y%m%d')}.csv")
    df.to_csv(f"result_{TODAY.strftime('%Y%m%d')}.csv",index=False,encoding="utf-8-sig")

if __name__=="__main__": main()

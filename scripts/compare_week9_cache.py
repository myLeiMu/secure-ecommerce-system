"""Compare optimized LocMem vs Redis; do not reinterpret this as old-code improvement."""
import argparse
import json
from pathlib import Path
from compare_week9 import load


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--locmem', type=Path, required=True)
    parser.add_argument('--redis', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    le, lr, lm = load(args.locmem)
    re, rr, rm = load(args.redis)
    for key in ('source_ref', 'source_sha256', 'python', 'platform', 'cpu_logical', 'ram_bytes',
                'mysql', 'java', 'jmeter', 'packages', 'jmx_sha256'):
        if le[key] != re[key]: raise ValueError('Different environment/source: '+key)
    if {k:v for k,v in le['fixed'].items() if k!='cache'} != {k:v for k,v in re['fixed'].items() if k!='cache'}:
        raise ValueError('Non-cache load/environment changed')
    if le['cache_backend']!='locmem' or re['cache_backend']!='redis': raise ValueError('Unexpected cache backends')
    comparisons = {k:{'locmem':lm[k], 'redis':rm[k],
        'redis_p95_change_percent':100*(rm[k]['p95_ms']-lm[k]['p95_ms'])/lm[k]['p95_ms']} for k in lm}
    threads = le['fixed']['threads']
    repeats = le['fixed']['repeats']
    samples = lm['login']['samples']
    rounds=[]
    for backend, folder, results, env in [('locmem',args.locmem,lr,le),('redis',args.redis,rr,re)]:
        for i in range(1,env['fixed']['repeats']+1):
            phase=f'round-{i}'
            data=results[phase]['sql_delta']
            hits,misses=data['cache_hits'],data['cache_misses']
            if data['cache_errors']: raise ValueError('Cache errors')
            item={'backend':backend,'round':i,'hits':hits,'misses':misses,
                  'hit_rate_percent':100*hits/(hits+misses) if hits+misses else 0,
                  'queries':data['queries'],'errors':data['cache_errors']}
            if backend=='redis':
                proof=json.loads((folder/phase/'redis-evidence.json').read_text(encoding='utf-8'))
                cleanup=json.loads((folder/phase/'redis-cleanup.json').read_text(encoding='utf-8'))
                if not proof['ping'] or proof['product_payload_keys']<1 or cleanup['remaining_keys']!=0:
                    raise ValueError('Missing Redis usage or cleanup proof')
                item['redis_evidence']=proof
            rounds.append(item)
    passed=all(rm[k]['error_rate_percent']<=1 for k in ('login','products','order'))
    result={'same_source_and_non_cache_environment':True,'redis':re['redis'],
            'fixed': le['fixed'],
            'redis_error_rate_pass':passed,'comparison':comparisons,'cache_rounds':rounds,
            'scope':'Optimized code with LocMem versus Redis, not old-code versus optimized-code acceptance.'}
    args.output.mkdir(parents=True,exist_ok=False)
    (args.output/'comparison.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    lines=['# Redis 补充实测','',
        '2026-10-28：同一优化后代码，重新执行 LocMem 与 WSL Redis 两组。除缓存后端外，源码摘要、JMX、依赖、MySQL 和负载配置一致。',
        f"Redis {re['redis']['version']}；{threads} 并发、{repeats} 轮，每接口每组 {samples} 正式样本。所有失败均计入统计，冒烟和预热不计入。",
        '限流条件：'+le['fixed']['rate_limit'],'',
        '| 接口 | LocMem p95 ms | Redis p95 ms | Redis p95 变化 | LocMem req/s | Redis req/s | LocMem 错误率 | Redis 错误率 |',
        '| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |']
    for key,item in comparisons.items():
        a,b=item['locmem'],item['redis']
        lines.append(f"| {key} | {a['p95_ms']} | {b['p95_ms']} | {item['redis_p95_change_percent']:+.2f}% | {a['throughput_rps']:.4f} | {b['throughput_rps']:.4f} | {a['error_rate_percent']:.2f}% | {b['error_rate_percent']:.2f}% |")
    lines += ['', '正数表示 Redis p95 更高，负数表示更低。吞吐量包含用户流程等待，不代表饱和 QPS。', '',
        '| 缓存/轮次 | 商品缓存命中 | 未命中 | 命中率 | SQL 数 | 缓存读取异常 |',
        '| --- | ---: | ---: | ---: | ---: | ---: |']
    for r in rounds:
        lines.append(f"| {r['backend']}/{r['round']} | {r['hits']} | {r['misses']} | {r['hit_rate_percent']:.2f}% | {r['queries']} | {r['errors']} |")
    lines += ['', '命中率统计真实商品数据键读取，不包含版本键；每次下单使商品缓存失效，因此该写入频繁流程的命中率不等同只读热点场景。',
        '每轮保存 Redis PING、专属键数量、商品键 TTL 和清理记录；不导出缓存值、口令或 JWT。只清理随机 test_week9_ 前缀，未执行 FLUSHDB/FLUSHALL。', '',
        'Redis 错误率验收：'+('通过。' if passed else '未通过。'),
        'Redis 跨 Windows/WSL 访问有额外通信成本，单进程下不保证比进程内缓存更快；其共享缓存能力适用于多个后端进程，此处未做多进程容量测试。',
        '原第九周旧版→优化版的 20% 改善验收保持不变；本表仅补充缓存后端选择的数据，不混用两种实验计算提升。',
        '两组按顺序实测，机器和 MySQL/Redis 实例与其他服务共享，不能据此断言微小差异具有统计显著性。', '']
    (args.output/'summary.md').write_text('\n'.join(lines),encoding='utf-8')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    labels=['login','products','order']
    fig,axes=plt.subplots(1,2,figsize=(10,4))
    for offset,values,name,color in [(-.18,lm,'LocMem','#9ba9bd'),(.18,rm,'Redis','#287d8e')]:
        axes[0].bar([i+offset for i in range(3)],[values[k]['p95_ms'] for k in labels],.36,label=name,color=color)
        rates=[r['hit_rate_percent'] for r in rounds if r['backend']==name.lower()]
        axes[1].bar([i+offset for i in range(len(rates))],rates,.36,label=name,color=color)
    axes[0].set_xticks(range(3),labels); axes[0].set_title('API p95 (ms)'); axes[0].legend()
    axes[1].set_xticks(range(repeats),[f'Round {i+1}' for i in range(repeats)]); axes[1].set_title('Product cache hit rate (%)')
    axes[1].set_ylim(0,100)
    for ax in axes: ax.spines[['top','right']].set_visible(False)
    fig.suptitle(f'Same optimized code / {threads} users / {samples} samples per API')
    fig.tight_layout(); fig.savefig(args.output/'comparison.png',dpi=160); plt.close(fig)
    print(json.dumps({'redis_error_rate_pass':passed,'comparison':comparisons},indent=2))
    return 0 if passed else 1


if __name__=='__main__': raise SystemExit(main())

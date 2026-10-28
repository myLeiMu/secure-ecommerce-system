"""Compare raw JTLs only after verifying identical experiment settings."""
import argparse
import csv
import json
import math
from pathlib import Path
import statistics


def metrics(rows):
    result = {}
    for label in ('login','products','order','setup_cart'):
        group = [r for r in rows if r['label']==label]
        if not group: raise ValueError('Missing sampler: '+label)
        times = sorted(int(r['elapsed']) for r in group)
        errors = sum(r['success'].lower()!='true' for r in group)
        # Aggregate throughput sums each round's active window, excluding downtime.
        duration = 0
        for phase in sorted({r['_round'] for r in group}):
            current = [r for r in group if r['_round']==phase]
            duration += (max(int(r['timeStamp'])+int(r['elapsed']) for r in current)-min(int(r['timeStamp']) for r in current))/1000
        result[label] = {'samples':len(group),'errors':errors,'error_rate_percent':100*errors/len(group),
                         'p95_ms':times[math.ceil(.95*len(times))-1], 'mean_ms':statistics.mean(times),
                         'throughput_rps':len(group)/duration,
                         'response_codes':{code:sum(r['responseCode']==code for r in group) for code in sorted({r['responseCode'] for r in group})}}
    return result


def load(path):
    env = json.loads((path/'environment.json').read_text(encoding='utf-8'))
    results = json.loads((path/'results.json').read_text(encoding='utf-8'))
    rows = []
    for i in range(1,env['fixed']['repeats']+1):
        phase = f'round-{i}'
        if phase not in results: raise ValueError(f'Missing complete {phase} in {path}')
        with (path/phase/'measurement.jtl').open(encoding='utf-8-sig',newline='') as file:
            rows.extend({**r,'_round':phase} for r in csv.DictReader(file))
    expected = env['fixed']['threads']*env['fixed']['loops_per_thread']*env['fixed']['repeats']
    summary = metrics(rows)
    if any(m['samples']!=expected for m in summary.values()): raise ValueError('Incomplete measurement samples')
    return env,results,summary


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--before',required=True,type=Path)
    p.add_argument('--after',required=True,type=Path)
    p.add_argument('--output',required=True,type=Path)
    args=p.parse_args()
    before,br,bm=load(args.before)
    after,ar,am=load(args.after)
    keys=('fixed','python','platform','cpu_logical','ram_bytes','mysql','java','jmeter','packages','jmx_sha256')
    mismatches=[key for key in keys if before[key]!=after[key]]
    for name in ('scripts/week9_server.py','scripts/week9_settings.py'):
        if before['source_sha256'][name]!=after['source_sha256'][name]: mismatches.append(name)
    if mismatches: raise ValueError('Non-comparable environments: '+', '.join(mismatches))
    args.output.mkdir(parents=True,exist_ok=False)
    comparison={}
    repeats=before['fixed']['repeats']
    for label in bm:
        gain=(bm[label]['p95_ms']-am[label]['p95_ms'])/bm[label]['p95_ms']*100
        comparison[label]={'before':bm[label],'after':am[label],'p95_reduction_percent':gain,
                           'meets_target':gain>=20 and am[label]['error_rate_percent']<=1,
                           'round_p95_before':[br[f'round-{i}']['metrics'][label]['p95_ms'] for i in range(1,repeats+1)],
                           'round_p95_after':[ar[f'round-{i}']['metrics'][label]['p95_ms'] for i in range(1,repeats+1)]}
    passed=all(comparison[label]['meets_target'] for label in ('login','products','order'))
    result={'environment_comparable':True,'target':'Each target API pooled p95 reduction >=20%, error rate <=1%',
            'all_three_targets_pass':passed,'comparison':comparison,
            'limitations':['2 concurrent users, loopback HTTP API, dedicated MySQL; not production capacity.',
                           'JMeter and MySQL share this machine; CPU/RSS and raw JTL remain available.',
                           'Warmup and smoke excluded; failed samples included, no retry removal.']}
    (args.output/'comparison.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    lines=['# 第九周实测前后对比','',
           f"同环境：Windows / WAF / Waitress 4 线程 / 独立 MySQL 测试库 / LocMem；{before['fixed']['threads']} 并发、每轮每用户 {before['fixed']['loops_per_thread']} 次、{repeats} 轮。",
           f"每个目标接口 {bm['login']['samples']} 个正式样本；冒烟和预热另存，错误样本未剔除。吞吐量含用户流程与等待，不是饱和 QPS。",'',
           '| 接口 | 样本/组 | 前 p95 ms | 后 p95 ms | 降幅 | 前吞吐 req/s | 后吞吐 req/s | 前错误率 | 后错误率 |',
           '| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |']
    for label in ('login','products','order','setup_cart'):
        item=comparison[label];b=item['before'];a=item['after']
        lines.append(f"| {label} | {a['samples']} | {b['p95_ms']} | {a['p95_ms']} | {item['p95_reduction_percent']:.2f}% | {b['throughput_rps']:.4f} | {a['throughput_rps']:.4f} | {b['error_rate_percent']:.2f}% | {a['error_rate_percent']:.2f}% |")
    lines+=['','三目标接口验收：'+('通过。' if passed else '未全部通过，不能宣称达标。'),'',
            'setup_cart 是下单准备步骤，单独列出，不冒充第四个任务接口。p95 对三轮原始样本合并后按 nearest-rank 计算，不取分位数的平均值。','',
            '| 接口 | 优化前各轮 p95 ms | 优化后各轮 p95 ms |','| --- | --- | --- |']
    for label in ('login','products','order'):
        item=comparison[label];lines.append(f"| {label} | {item['round_p95_before']} | {item['round_p95_after']} |")
    lines+=['','## SQL 和连接池','', '| 组/轮 | 测量期 SQL 数 | DDL 数 | 连接借出 | 归还 | 峰值占用（含监控） |',
            '| --- | ---: | ---: | ---: | ---: | ---: |']
    for name,data in [('before',br),('after',ar)]:
        for i in range(1,repeats+1):
            record=data[f'round-{i}'];s=record['sql_delta']
            lines.append(f"| {name}/{i} | {s['queries']} | {s['ddl']} | {s['checkouts']} | {s['checkins']} | {record['peak_pool_checked_out_including_monitor']} |")
    lines+=['','SQL 计数排除监控查询；连接池计数包含每秒一次的监控连接。连接池容量前后均为 10+20，优化的是会话归还与请求工作量，不是单纯扩容。','',
            '## 监控','', '| 组/轮 | 后端 CPU 平均/峰值（单核100%） | 后端 RSS 峰值 MiB | 整机 CPU 平均 |',
            '| --- | --- | ---: | ---: |']
    for name,path in [('before',args.before),('after',args.after)]:
        for i in range(1,repeats+1):
            r=[v for v in json.loads((path/f'round-{i}'/'resources.json').read_text()) if v['stage']=='measurement']
            if not r: raise ValueError('Missing monitoring samples')
            cpu=[v['backend_cpu_percent_one_core'] for v in r]
            lines.append(f"| {name}/{i} | {statistics.mean(cpu):.2f}% / {max(cpu):.2f}% | {max(v['backend_rss_bytes'] for v in r)/1024**2:.2f} | {statistics.mean(v['machine_cpu_percent'] for v in r):.2f}% |")
    lines+=['','此结果证明固定课堂负载下的性能改善，不代表 nginx 8443 的 TLS/mTLS 端到端成绩或高并发容量。','']
    (args.output/'summary.md').write_text('\n'.join(lines),encoding='utf-8')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    labels=['login','products','order']; x=range(3)
    fig,axes=plt.subplots(1,3,figsize=(12,4))
    for ax,field,title in zip(axes,['p95_ms','throughput_rps','error_rate_percent'],['p95 (ms, log scale)','Journey throughput (req/s)','Errors (%)']):
        ax.bar([v-.18 for v in x],[bm[k][field] for k in labels],width=.36,label='Before',color='#9ba9bd')
        ax.bar([v+.18 for v in x],[am[k][field] for k in labels],width=.36,label='After',color='#287d8e')
        ax.set_xticks(list(x),labels);ax.set_title(title);ax.spines[['top','right']].set_visible(False)
        if field=='p95_ms':ax.set_yscale('log')
    axes[0].legend();fig.suptitle(f"Week 9 / MySQL / {before['fixed']['threads']} users / {bm['login']['samples']} measured samples per API")
    fig.tight_layout();fig.savefig(args.output/'comparison.png',dpi=180);plt.close(fig)
    print(json.dumps({'all_three_targets_pass':passed,'p95_reduction_percent':{k:v['p95_reduction_percent'] for k,v in comparison.items()}},indent=2))
    return 0 if passed else 1


if __name__=='__main__':raise SystemExit(main())

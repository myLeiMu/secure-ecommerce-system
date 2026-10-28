"""Sequential 10/30-user cache comparison, isolated capacity configuration only."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, MPLCONFIGDIR=str(ROOT/'dist-releases/matplotlib-week9'))
    comparisons = {}
    for threads, backends in [(10,('locmem','redis')),(30,('redis','locmem'))]:
        for backend in backends:
            folder = out/f'{backend}-{threads}'
            command = [sys.executable,str(ROOT/'scripts/week9_perf.py'),'--source-ref','WORKTREE',
                '--threads',str(threads),'--pause-ms','0','--loops','20','--repeats','3',
                '--capacity','--allow-errors','--cache',backend,'--output',str(folder)]
            print(f'START {backend} / {threads} users',flush=True)
            subprocess.run(command,check=True,cwd=ROOT,env=env)
        comparison = out/f'comparison-{threads}'
        done=subprocess.run([sys.executable,str(ROOT/'scripts/compare_week9_cache.py'),
            '--locmem',str(out/f'locmem-{threads}'),'--redis',str(out/f'redis-{threads}'),
            '--output',str(comparison)],cwd=ROOT,env=env,capture_output=True,text=True)
        (out/f'comparison-{threads}-console.txt').write_text(done.stdout+done.stderr,encoding='utf-8')
        if done.returncode not in (0,1) or not (comparison/'comparison.json').exists():
            raise RuntimeError('Comparison failed; see retained console evidence')
        comparisons[str(threads)]=json.loads((comparison/'comparison.json').read_text(encoding='utf-8'))
        print(f'COMPLETE {threads} users',flush=True)
    (out/'summary.json').write_text(json.dumps(comparisons,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    lines=['# 10 / 30 并发补充实测','',
        '同一优化后代码，Waitress 1 进程 4 工作线程、MySQL 池 10+20；10、30 个 JMeter 用户，每用户独立账号，每轮全局分配单库存商品。',
        '每组 3 轮，每线程每轮 20 次正式循环，2 次预热，2 秒升压，无思考等待；两种缓存按级别交替先后顺序串行测试。',
        '**容量实验专用：独立回环 HTTP / 随机测试库中移除每 IP 100 次/分钟限流，其余认证、审计、库存检查保留。生产配置未改变。**',
        '这不代表原生产限流下的可用吞吐量，也不替代第九周原始优化前后验收。失败样本未剔除，429/500/业务失败全部计为错误。','',
        '| 并发 | 接口 | LocMem p95 ms | Redis p95 ms | LocMem req/s | Redis req/s | LocMem 错误率 | Redis 错误率 |',
        '| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |']
    for threads,report in comparisons.items():
        for name in ('login','products','order'):
            a,b=report['comparison'][name]['locmem'],report['comparison'][name]['redis']
            lines.append(f"| {threads} | {name} | {a['p95_ms']} | {b['p95_ms']} | {a['throughput_rps']:.2f} | {b['throughput_rps']:.2f} | {a['error_rate_percent']:.2f}% | {b['error_rate_percent']:.2f}% |")
    lines += ['', '各接口吞吐量来自同一串行交易流程，不能视为独立接口最大吞吐量；p95 按正式样本合并计算。',
        '固定 4 个后端工作线程，高并发会产生排队。每次下单还会使商品缓存失效，命中率见各级比较报告；不据此声称 Redis 在所有场景更快或更慢。',
        '短时固定循环负载用于并发敏感性比较，不是长时间稳定性测试或多进程生产容量承诺。', '']
    (out/'summary.md').write_text('\n'.join(lines),encoding='utf-8')


if __name__=='__main__': main()

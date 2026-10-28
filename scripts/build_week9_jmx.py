"""Build the reproducible two-user JMeter journey, without saved response bodies."""
from pathlib import Path
import xml.etree.ElementTree as E

ROOT = Path(__file__).resolve().parents[1]


def build():
    tree = E.parse(ROOT / 'performance/week8-baseline.jmx')
    root = tree.getroot()
    root.find('.//TestPlan').set('testname', 'Week 9 isolated MySQL comparison')
    group_tree = root.find('.//ThreadGroup/../hashTree')
    # Per-thread usernames prevent token replacement and cart collisions.
    pre = E.SubElement(group_tree, 'JSR223PreProcessor', guiclass='TestBeanGUI',
                       testclass='JSR223PreProcessor', testname='Independent trading users', enabled='true')
    for k, v in [('scriptLanguage', 'groovy'), ('cacheKey', 'true'),
                 ('script', "vars.put('username', 'perf_user_' + (ctx.getThreadNum() + 1))")]:
        E.SubElement(pre, 'stringProp', name=k).text = v
    E.SubElement(group_tree, 'hashTree')
    for prop in root.iter('stringProp'):
        if prop.get('name') == 'ThreadGroup.on_sample_error': prop.text = 'continue'
        if prop.get('name') == 'HTTPSampler.port': prop.text = '${__P(port,8769)}'
        if prop.get('name') == 'HTTPSampler.response_timeout': prop.text = '120000'
        if prop.get('name') == 'CounterConfig.end': prop.text = '10000'
        if prop.get('name') == 'Argument.value' and '"username":"user1"' in (prop.text or ''):
            prop.text = '{"username":"${username}","password":"Week9PerfOnly123!"}'
        if prop.get('name') == 'HTTPSampler.path' and '/api/products?' in (prop.text or ''):
            prop.text = '/api/products?category_id=1'
        if prop.get('name') == 'ThreadGroup.num_threads': prop.text = '${__P(threads,2)}'
        if prop.get('name') == 'ThreadGroup.ramp_time': prop.text = '${__P(ramp,2)}'
    E.indent(root, space='  ')
    tree.write(ROOT / 'performance/week9-comparison.jmx', encoding='UTF-8', xml_declaration=True)


if __name__ == '__main__':
    build()

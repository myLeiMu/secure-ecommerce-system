"""Generate the reviewable JMeter plan, without third-party JMeter plugins."""
from pathlib import Path
import xml.etree.ElementTree as E

ROOT = Path(__file__).resolve().parents[1]


def prop(parent, name, value, kind='stringProp'):
    E.SubElement(parent, kind, name=name).text = str(value)


def element(parent, tag, name, gui, **attrs):
    node = E.SubElement(parent, tag, guiclass=gui, testclass=tag, testname=name, enabled='true', **attrs)
    tree = E.SubElement(parent, 'hashTree')
    return node, tree


def build():
    root = E.Element('jmeterTestPlan', version='1.2', properties='5.0', jmeter='5.6.3')
    tree = E.SubElement(root, 'hashTree')
    plan, tree = element(tree, 'TestPlan', 'Week 8 isolated integration baseline', 'TestPlanGui')
    prop(plan, 'TestPlan.comments', 'Login -> catalog -> cart prerequisite -> order. Fictional users only. No payment.')
    prop(plan, 'TestPlan.serialize_threadgroups', 'true', 'boolProp')
    group, tree = element(tree, 'ThreadGroup', 'Trading user journey', 'ThreadGroupGui')
    prop(group, 'ThreadGroup.on_sample_error', 'stopthread')
    controller = E.SubElement(group, 'elementProp', name='ThreadGroup.main_controller', elementType='LoopController', guiclass='LoopControlPanel', testclass='LoopController', testname='Loop')
    prop(controller, 'LoopController.continue_forever', 'false', 'boolProp')
    prop(controller, 'LoopController.loops', '${__P(loops,1)}')
    prop(group, 'ThreadGroup.num_threads', '${__P(threads,1)}')
    prop(group, 'ThreadGroup.ramp_time', '${__P(ramp,1)}')
    prop(group, 'ThreadGroup.scheduler', 'false', 'boolProp')
    prop(group, 'ThreadGroup.same_user_on_next_iteration', 'true', 'boolProp')
    headers, _ = element(tree, 'HeaderManager', 'JSON requests', 'HeaderPanel')
    collection = E.SubElement(headers, 'collectionProp', name='HeaderManager.headers')
    for name, value in [('Content-Type', 'application/json'), ('Accept', 'application/json')]:
        header = E.SubElement(collection, 'elementProp', name=name, elementType='Header')
        prop(header, 'Header.name', name)
        prop(header, 'Header.value', value)
    counter, _ = element(tree, 'CounterConfig', 'A distinct secondhand item each purchase', 'CounterConfigGui')
    for name, value in [('start', '${__P(product_start,1)}'), ('end', '1000'), ('incr', '1'), ('name', 'product_id')]:
        prop(counter, 'CounterConfig.' + name, value)
    prop(counter, 'CounterConfig.per_user', 'false', 'boolProp')
    timer, _ = element(tree, 'ConstantTimer', 'Pacing: keep real rate limiting enabled', 'ConstantTimerGui')
    prop(timer, 'ConstantTimer.delay', '${__P(pause_ms,1000)}')
    cases = [
        ('login', 'POST', '/api/auth/login', '{"username":"user1","password":"TestPass123!"}', False),
        ('products', 'GET', '/api/products?page=1&page_size=20', None, False),
        ('setup_cart', 'POST', '/api/cart', '{"product_id":${product_id},"quantity":1}', True),
        ('order', 'POST', '/api/orders', '{"shipping_amount":"0.00","discount_amount":"0.00"}', True),
    ]
    for label, method, path, body, authenticated in cases:
        sampler, children = element(tree, 'HTTPSamplerProxy', label, 'HttpTestSampleGui')
        args = E.SubElement(sampler, 'elementProp', name='HTTPsampler.Arguments', elementType='Arguments', guiclass='HTTPArgumentsPanel', testclass='Arguments', testname='Arguments')
        arguments = E.SubElement(args, 'collectionProp', name='Arguments.arguments')
        if body:
            arg = E.SubElement(arguments, 'elementProp', name='', elementType='HTTPArgument')
            prop(arg, 'HTTPArgument.always_encode', 'false', 'boolProp')
            prop(arg, 'Argument.value', body)
            prop(arg, 'Argument.metadata', '=')
        for name, value in [('domain', '${__P(host,127.0.0.1)}'), ('port', '${__P(port,8768)}'),
                            ('protocol', '${__P(protocol,http)}'), ('path', path), ('method', method),
                            ('contentEncoding', 'UTF-8'), ('connect_timeout', '5000'), ('response_timeout', '30000')]:
            prop(sampler, 'HTTPSampler.' + name, value)
        for name, value in [('follow_redirects', 'false'), ('auto_redirects', 'false'), ('use_keepalive', 'true'), ('postBodyRaw', 'true')]:
            prop(sampler, 'HTTPSampler.' + name, value, 'boolProp')
        if authenticated:
            auth, _ = element(children, 'HeaderManager', 'Current login token', 'HeaderPanel')
            headers2 = E.SubElement(auth, 'collectionProp', name='HeaderManager.headers')
            header = E.SubElement(headers2, 'elementProp', name='Authorization', elementType='Header')
            prop(header, 'Header.name', 'Authorization')
            prop(header, 'Header.value', 'Bearer ${token}')
        if label == 'login':
            extractor, _ = element(children, 'JSONPostProcessor', 'Extract fresh JWT', 'JSONPostProcessorGui')
            for name, value in [('referenceNames', 'token'), ('jsonPathExprs', '$.data.token'), ('match_numbers', '1'), ('defaultValues', 'MISSING')]:
                prop(extractor, 'JSONPostProcessor.' + name, value)
        assertion, _ = element(children, 'JSR223Assertion', 'HTTP and business success', 'TestBeanGUI')
        prop(assertion, 'scriptLanguage', 'groovy')
        prop(assertion, 'cacheKey', 'true')
        extra = {'login': 'assert body.data.token instanceof String; assert body.data.token.length() > 30',
                 'order': 'assert body.data.order_id > 0', 'products': 'assert body.data != null', 'setup_cart': ''}[label]
        prop(assertion, 'script', 'try {\n assert prev.getResponseCode() == "200"\n def body = new groovy.json.JsonSlurper().parseText(prev.getResponseDataAsString())\n assert body.code == 0\n ' + extra + '\n} catch (Throwable ex) { AssertionResult.setFailure(true); AssertionResult.setFailureMessage("HTTP/business assertion failed; response omitted to protect credentials") }')
    E.indent(root, space='  ')
    path = ROOT / 'performance/week8-baseline.jmx'
    path.parent.mkdir(parents=True, exist_ok=True)
    E.ElementTree(root).write(path, encoding='UTF-8', xml_declaration=True)
    print(path)


if __name__ == '__main__':
    build()

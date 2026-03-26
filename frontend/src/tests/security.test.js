import { SecurityUtils } from '../utils/security.js'; 

describe('SecurityUtils.sanitizeInput', () => {
  test('keeps plain text unchanged', () => {
    expect(SecurityUtils.sanitizeInput('hello world')).toBe('hello world');
  });

  test('removes simple HTML tags', () => {
    expect(SecurityUtils.sanitizeInput('<b>bold</b> text')).toBe('bold text');
  });

  test('removes event handlers like onclick', () => {
    expect(SecurityUtils.sanitizeInput('<div onclick="do()">click</div>'))
      .toBe('click');
  });

  test('removes javascript: URIs', () => {
    expect(SecurityUtils.sanitizeInput('<a href="javascript:alert(1)">x</a>'))
      .toBe('x');
    expect(SecurityUtils.sanitizeInput('javascript:alert(1)'))
      .toBe('alert(1)');
  });

  test('handles mixed-case dangerous tokens', () => {
    expect(SecurityUtils.sanitizeInput('<IMG SRC=JaVaScRiPt:alert(1)>'))
      .toBe('');
    expect(SecurityUtils.sanitizeInput('jAvAsCrIpT:alert(1)'))
      .toBe('alert(1)');
  });

  test('removes eval and expression', () => {
    expect(SecurityUtils.sanitizeInput('eval(alert(1))')).not.toContain('eval');
    expect(SecurityUtils.sanitizeInput('expression(alert(1))')).not.toContain('expression');
  });

  test('returns non-strings unchanged', () => {
    expect(SecurityUtils.sanitizeInput(null)).toBe(null);
    expect(SecurityUtils.sanitizeInput(undefined)).toBe(undefined);
    expect(SecurityUtils.sanitizeInput(123)).toBe(123);
    const obj = { a: 1 };
    expect(SecurityUtils.sanitizeInput(obj)).toBe(obj);
  });

});

describe('SecurityUtils.escapeHtml', () => {
  test('escapes special HTML characters', () => {
    const raw = '<div> & " \'';
    const escaped = SecurityUtils.escapeHtml(raw);
    expect(escaped).toContain('&lt;div&gt;');
    expect(escaped).toContain('&amp;');
  });

  test('does not execute script when used in DOM', () => {
    const raw = '<img src=x onerror=alert(1)>';
    const escaped = SecurityUtils.escapeHtml(raw);
    expect(escaped).toContain('&lt;img');
  });

  test('works with empty string', () => {
    expect(SecurityUtils.escapeHtml('')).toBe('');
  });
});
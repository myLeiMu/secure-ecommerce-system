import { validationRules, validateForm } from '../utils/validation.js';
import { SecurityUtils } from '../utils/security.js';

describe('validationRules unit tests', () => {
  describe('validateUsername', () => {
    test('valid usernames pass', () => {
      expect(SecurityUtils.validateUsername('user_1')).toBe(true);
      expect(SecurityUtils.validateUsername('abcd')).toBe(true);
    });

    test('invalid usernames fail', () => {
      expect(SecurityUtils.validateUsername('a')).toBe(false);
      expect(SecurityUtils.validateUsername('user-name')).toBe(false);
      expect(SecurityUtils.validateUsername('用户')).toBe(false);
    });
  });

  describe('validateEmail', () => {
    test('valid emails pass', () => {
      expect(SecurityUtils.validateEmail('user@example.com')).toBe(true);
      expect(SecurityUtils.validateEmail('a.b+tag@sub.domain.co')).toBe(true);
    });

    test('invalid emails fail', () => {
      expect(SecurityUtils.validateEmail('user@')).toBe(false);
      expect(SecurityUtils.validateEmail('user@@domain.com')).toBe(false);
      expect(SecurityUtils.validateEmail('')).toBe(false);
    });
  });

  describe('validatePassword', () => {
    test('valid passwords pass', () => {
      expect(SecurityUtils.validatePassword('abc12345')).toBe(true);
      expect(SecurityUtils.validatePassword('A1b2C3d4')).toBe(true);
      expect(SecurityUtils.validatePassword('passw0rd!')).toBe(true);
    });

    test('invalid passwords fail', () => {
      expect(SecurityUtils.validatePassword('abcdefg')).toBe(false);
      expect(SecurityUtils.validatePassword('12345678')).toBe(false);
      const long21 = 'a1'.repeat(11);
      expect(SecurityUtils.validatePassword(long21)).toBe(false);
    });
  });
});

describe('validateForm integration', () => {
  test('valid formData returns isValid true', () => {
    const formData = {
      username: 'user_01',
      email: 'user01@example.com',
      password: 'abc12345',
      phone: '13800138000'
    };
    const result = validateForm(formData, validationRules);
    expect(result.isValid).toBe(true);
    expect(result.errors).toEqual({});
  });

  test('missing required field returns error', () => {
    const formData = {
      username: 'user_01',
      email: '',
      password: 'abc12345',
      phone: '13800138000'
    };
    const result = validateForm(formData, validationRules);
    expect(result.isValid).toBe(false);
    expect(result.errors).toHaveProperty('email');
  });

  test('invalid password returns validator message', () => {
    const formData = {
      username: 'user_01',
      email: 'user01@example.com',
      password: 'short1',
      phone: '13800138000'
    };
    const result = validateForm(formData, validationRules);
    expect(result.isValid).toBe(false);
    expect(result.errors.password).toMatch(/密码必须/);
  });

  test('extra fields do not affect validation', () => {
    const formData = {
      username: 'user_01',
      email: 'user01@example.com',
      password: 'abc12345',
      phone: '13800138000',
      extra: 'ignored'
    };
    const result = validateForm(formData, validationRules);
    expect(result.isValid).toBe(true);
  });
});
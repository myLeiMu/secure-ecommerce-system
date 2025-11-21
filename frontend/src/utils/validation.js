import { SecurityUtils } from './security';

export const validationRules = {
  username: {
    required: true,
    validator: (value) => {
      if (!value) return '用户名不能为空';
      if (!SecurityUtils.validateUsername(value)) {
        return '用户名必须为4-20位字母、数字或下划线';
      }
      return true;
    }
  },

  email: {
    required: true,
    validator: (value) => {
      if (!value) return '邮箱不能为空';
      if (!SecurityUtils.validateEmail(value)) {
        return '请输入有效的邮箱地址';
      }
      return true;
    }
  },

  password: {
    required: true,
    validator: (value) => {
      if (!value) return '密码不能为空';
      if (!SecurityUtils.validatePassword(value)) {
        return '密码必须为8-20位，包含字母和数字';
      }
      return true;
    }
  },

  phone: {
    required: true,
    validator: (value) => {
      if (!value) return '手机号不能为空';
      const phoneRegex = /^1[3-9]\d{9}$/;
      if (!phoneRegex.test(value)) {
        return '请输入有效的手机号码';
      }
      return true;
    }
  }
};

export function validateForm(formData, rules) {
  const errors = {};
  
  Object.keys(rules).forEach(field => {
    const rule = rules[field];
    const value = formData[field];
    
    if (rule.required && !value) {
      errors[field] = rule.requiredMessage || `${field}不能为空`;
      return;
    }
    
    if (rule.validator) {
      const result = rule.validator(value);
      if (result !== true) {
        errors[field] = result;
      }
    }
  });
  
  return {
    isValid: Object.keys(errors).length === 0,
    errors
  };
}
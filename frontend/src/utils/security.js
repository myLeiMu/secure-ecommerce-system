export class SecurityUtils {
  static sanitizeInput(input) {
    if (typeof input !== 'string') return input;

    // HTML标签过滤
    const htmlRegex = /<[^>]*>/g;
    input = input.replace(htmlRegex, '');

    // 危险脚本过滤
    const dangerousPatterns = [
      /javascript:/gi,
      /on\w+\s*=/gi,
      /<script[^>]*>.*?<\/script>/gi,
      /eval\s*\(/gi,
      /expression\s*\(/gi
    ];

    dangerousPatterns.forEach(pattern => {
      input = input.replace(pattern, '');
    });

    return input.trim();
  }

  static escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  static validateEmail(email) {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
  }

  static validatePassword(password) {
    // 密码长度8-20字符，必须包含字母和数字
    const passwordRegex = /^(?=.*[A-Za-z])(?=.*\d)[A-Za-z\d@$!%*#?&]{8,20}$/;
    return passwordRegex.test(password);
  }

  static validateUsername(username) {
    // 用户名长度4-20字符，只能包含字母、数字、下划线
    const usernameRegex = /^[a-zA-Z0-9_]{4,20}$/;
    return usernameRegex.test(username);
  }
}
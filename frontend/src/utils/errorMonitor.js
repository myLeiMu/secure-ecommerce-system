class ErrorMonitor {
  constructor() {
    this.initialized = false;
  }

  init() {
    if (this.initialized || typeof window === 'undefined') {
      return;
    }
    window.addEventListener('error', this.handleGlobalError.bind(this));
    window.addEventListener('unhandledrejection', this.handlePromiseRejection.bind(this));
    this.initialized = true;
  }

  handleGlobalError(event) {
    const payload = {
      type: 'javascript',
      message: event.message,
      filename: event.filename,
      lineno: event.lineno,
      colno: event.colno,
      stack: event.error?.stack || ''
    };
    this.report(payload);
  }

  handlePromiseRejection(event) {
    const payload = {
      type: 'promise',
      message: event.reason?.message || String(event.reason),
      stack: event.reason?.stack || ''
    };
    this.report(payload);
  }

  report(errorInfo) {
    // 这里可以接入后端日志服务或第三方监控，我们先打印日志
    console.error('前端错误捕获：', errorInfo);
    try {
      const endpoint = process.env.VUE_APP_ERROR_WEBHOOK;
      if (endpoint) {
        navigator.sendBeacon?.(endpoint, JSON.stringify(errorInfo));
      }
    } catch {
      // 忽略上报异常
    }
  }
}

export const errorMonitor = new ErrorMonitor();


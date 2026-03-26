async function completeWorkflowTest() {
  console.log('开始完整工作流测试...');
  
  // 1. 先测试公开接口
  console.log('测试公开接口...');
  const publicEndpoints = [
    '/api/categories',
    '/api/products?page=1&limit=5'
  ];
  
  for (const endpoint of publicEndpoints) {
    const response = await fetch(endpoint);
    console.log(`${endpoint}: ${response.status}`);
  }
  
  // 2. 测试认证
  console.log('测试认证...');

  const loginData = {
    username: 'testuser',  
    password: 'TestPass123!'     
  };
  
  const authResponse = await fetch('/api/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(loginData)
  });
  
  if (authResponse.ok) {
    const authResult = await authResponse.json();
    const token = authResult.data?.token;
    localStorage.setItem('access_token', token);
    console.log('登录成功，token已保存');
    
    // 3. 测试需要认证的接口
    console.log('测试受保护接口...');
    const profileResponse = await fetch('/api/users/profile', {
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      }
    });
    console.log('用户信息:', profileResponse.status);
  } else {
    console.log('登录失败，状态:', authResponse.status);
  }
}
completeWorkflowTest();
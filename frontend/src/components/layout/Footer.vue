<template>
  <footer class="app-footer">
    <div class="footer-container">
      <div class="footer-content">
        <div class="footer-section">
          <h3>电商系统</h3>
          <p>安全、便捷的电子商务平台</p>
        </div>
        
        <div class="footer-section">
          <h4>快速链接</h4>
          <ul>
            <li><router-link to="/">首页</router-link></li>
            <li><router-link to="/products">商品浏览</router-link></li>
            <li><router-link to="/about">关于我们</router-link></li>
          </ul>
        </div>
        
        <div class="footer-section">
          <h4>客户服务</h4>
          <ul>
            <li><a href="/help">帮助中心</a></li>
            <li><a href="/contact">联系我们</a></li>
            <li><a href="/privacy">隐私政策</a></li>
          </ul>
        </div>
        
        <div class="footer-section">
          <h4>联系我们</h4>
          <p>📧 service@ecommerce.com</p>
          <p>📞 400-123-4567</p>
        </div>
      </div>
      
      <div class="footer-bottom">
        <p>&copy; 2024 电商系统. 保留所有权利.</p>
      </div>
    </div>
  </footer>
</template>

<script>
export default {
  name: 'AppFooter'
};
</script>

<style scoped>
.app-footer {
  background: #343a40;
  color: white;
  margin-top: auto;
}

.footer-container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 2rem 1rem;
}

.footer-content {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 2rem;
  margin-bottom: 2rem;
}

.footer-section h3,
.footer-section h4 {
  margin-bottom: 1rem;
  color: #fff;
}

.footer-section h3 {
  font-size: 1.5rem;
}

.footer-section h4 {
  font-size: 1.1rem;
}

.footer-section ul {
  list-style: none;
  padding: 0;
}

.footer-section li {
  margin-bottom: 0.5rem;
}

.footer-section a {
  color: #adb5bd;
  text-decoration: none;
  transition: color 0.3s;
}

.footer-section a:hover {
  color: #fff;
}

.footer-bottom {
  border-top: 1px solid #495057;
  padding-top: 1rem;
  text-align: center;
  color: #adb5bd;
}

@media (max-width: 768px) {
  .footer-content {
    grid-template-columns: 1fr;
    text-align: center;
  }
}
</style>
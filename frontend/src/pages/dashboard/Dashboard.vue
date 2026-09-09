<template>
  <div class="console">
    <aside class="console-nav" aria-label="控制台功能导航">
      <p class="nav-caption">{{ roleLabels[role] }}功能</p>
      <button v-for="item in tabs" :key="item.id" :class="{ selected: tab === item.id }" :aria-current="tab === item.id ? 'page' : undefined" @click="selectTab(item.id)"><span aria-hidden="true">{{ item.icon }}</span>{{ item.label }}</button>
    </aside>
    <section class="workspace">
      <header class="page-heading"><div><p class="eyebrow">工作台 / {{ activeTab.label }}</p><h1>{{ activeTab.label }}</h1><p class="subtitle">{{ activeTab.description }}</p></div><button class="button secondary" :disabled="loading" @click="load">{{ loading ? '刷新中…' : '刷新数据' }}</button></header>
      <p v-if="error" class="alert error" role="alert">{{ error }}</p><p v-if="notice" class="alert success" role="status">{{ notice }}</p>
      <div v-if="loading" class="loading" role="status">正在获取最新数据…</div>
      <template v-else-if="tab === 'overview'">
        <div class="metrics"><article v-for="metric in metrics" :key="metric.key"><span>{{ metric.label }}</span><strong>{{ metric.money ? '¥' : '' }}{{ overview[metric.key] ?? '—' }}</strong><small>{{ metric.note }}</small></article></div>
        <div class="overview-grid"><article class="panel"><h2>待处理事项</h2><button class="task-row" @click="selectTab('orders')"><span><strong>订单发货</strong><small>查看付款状态并录入物流单号</small></span><b>{{ overview.pending_shipments || 0 }} →</b></button><button class="task-row" @click="selectTab('products')"><span><strong>低库存商品</strong><small>库存不足 10 件，及时补充库存</small></span><b>{{ overview.low_stock || 0 }} →</b></button></article><article class="panel"><h2>管理与安全</h2><p class="explanation">账号权限变更即时生效；关键操作会记录操作者、时间、对象和结果。</p><button class="button secondary" @click="selectTab('audit')">查看审计记录 →</button></article></div>
      </template>
      <MfaSettings v-else-if="tab === 'security'" />
      <article v-else-if="tab === 'permissions'" class="panel"><h2>角色权限矩阵</h2><div class="table-scroll"><table><thead><tr><th>角色</th><th>允许的资源与操作</th><th>登录验证</th></tr></thead><tbody><tr v-for="(permissions, name) in visibleMatrix" :key="name"><td>{{ roleLabels[name] }}</td><td><span v-for="permission in permissions" :key="permission" class="permission">{{ permissionLabels[permission] || permission }}</span></td><td>{{ ['admin', 'auditor'].includes(name) ? '密码 / 证书 + TOTP' : '密码 / 证书' }}</td></tr></tbody></table></div></article>
      <article v-else class="panel records">
        <div class="toolbar"><form class="filters" @submit.prevent="search"><input v-if="tab !== 'categories'" v-model.trim="q" :placeholder="searchPlaceholder" aria-label="搜索" /><select v-if="Object.keys(filterOptions).length" v-model="filter" aria-label="状态筛选"><option value="">全部</option><option v-for="(label, key) in filterOptions" :key="key" :value="key">{{ label }}</option></select><input v-if="tab === 'audit'" v-model="since" type="date" aria-label="开始日期" /><button v-if="tab !== 'categories'" class="button secondary">查询</button></form><button v-if="['products', 'categories'].includes(tab)" class="button" @click="edit()">+ {{ tab === 'products' ? '新增商品' : '新增分类' }}</button><button v-if="tab === 'audit'" class="button" :disabled="saving" @click="exportAudit">导出审计报告</button></div>
        <div class="table-scroll"><table><thead><tr><th v-for="column in columns" :key="column.key">{{ column.label }}</th><th v-if="tab !== 'audit'">操作</th></tr></thead><tbody v-if="rows.length"><tr v-for="row in rows" :key="rowId(row)"><td v-for="column in columns" :key="column.key" :class="{ resource: column.key === 'resource' }"><span :class="cellClass(column.key, row[column.key])">{{ display(column.key, row[column.key]) }}</span><small v-if="column.key === 'product_name'">{{ row.sku }}</small><small v-if="column.key === 'username' && tab === 'users'">ID {{ row.user_id }}</small></td><td v-if="tab !== 'audit'"><button class="text-button" :disabled="!canEdit(row)" @click="edit(row)">{{ tab === 'orders' ? '发货' : tab === 'users' ? '管理权限' : '编辑' }}</button></td></tr></tbody><tbody v-else><tr><td :colspan="columns.length + 1" class="empty"><strong>暂无符合条件的记录</strong><p>尝试调整筛选条件，或刷新数据。</p></td></tr></tbody></table></div>
        <footer v-if="tab !== 'categories'" class="pagination"><span>共 {{ total }} 条记录 · 第 {{ page }} / {{ Math.max(1, Math.ceil(total / 20)) }} 页</span><div><button class="button secondary" :disabled="page <= 1" @click="changePage(-1)">上一页</button><button class="button secondary" :disabled="page * 20 >= total" @click="changePage(1)">下一页</button></div></footer>
      </article>
      <p class="footer-note">{{ roleLabels[role] }}工作空间 · 关键管理操作与审计访问均有记录</p>
    </section>
    <div v-if="dialog" class="modal-backdrop" @click.self="closeDialog" @keydown.esc="closeDialog" @keydown.tab="trapFocus">
      <section class="admin-dialog" :class="{ 'product-dialog': tab === 'products' }" role="dialog" aria-modal="true" aria-labelledby="dialog-title"><header><h2 id="dialog-title">{{ dialogTitle }}</h2><button class="close" :disabled="saving" aria-label="关闭" @click="closeDialog">×</button></header>
        <form class="dialog-form" @submit.prevent="save"><div class="dialog-body">
          <template v-if="tab === 'users'"><p class="hint">正在管理 {{ form.username }}。保存后该用户的旧会话将失效。</p><label>角色<select v-model="form.role"><option v-for="(label, name) in assignableRoles" :key="name" :value="name">{{ label }}</option></select></label><label>账号状态<select v-model="form.is_active"><option :value="true">正常</option><option :value="false">停用</option></select></label></template>
          <template v-if="tab === 'products'"><label>商品名称<input v-model.trim="form.product_name" required maxlength="200" /></label><div class="form-grid"><label>SKU<input v-model.trim="form.sku" required maxlength="50" /></label><label>分类<select v-model.number="form.category_id" aria-label="分类" required><option disabled value="">请选择分类</option><option v-for="category in categories" :key="category.category_id" :value="category.category_id">{{ category.category_name }}</option></select></label><label>售价（元）<input v-model.number="form.sale_price" type="number" min="0.01" max="99999999.99" step="0.01" required /></label><label>库存<input v-model.number="form.stock_quantity" type="number" min="0" max="100000000" step="1" required /></label></div><label>商品描述<textarea v-model="form.description" rows="3" maxlength="10000"></textarea></label><label>网络图片 URL（可选）<textarea v-model.trim="form.image_urls_text" rows="3" placeholder="粘贴图片直链，每行一个，最多 8 张"></textarea></label><p class="hint">支持 HTTP / HTTPS 图片直链，建议使用 HTTPS。</p><ImageUrlPreview :value="form.image_urls_text" /><div class="form-grid"><label v-if="role === 'admin'">所属卖家 ID（可选）<input v-model.number="form.seller_id" type="number" min="1" /></label><label>上架状态<select v-model="form.status"><option value="active">上架</option><option value="inactive">下架</option></select></label></div></template>
          <template v-if="tab === 'categories'"><label>分类名称<input v-model.trim="form.category_name" required maxlength="100" /></label><label>排序<input v-model.number="form.sort_order" type="number" min="0" step="1" required /></label><label>状态<select v-model="form.is_active"><option :value="true">启用</option><option :value="false">停用</option></select></label><p class="hint">停用前需先下架该分类下的商品。</p></template>
          <template v-if="tab === 'orders'"><p class="hint">订单 {{ form.order_number }} · ¥{{ form.total_amount }}</p><label>物流单号<input v-model.trim="form.tracking_number" required maxlength="100" /></label><p class="hint">确认后订单变为“已发货”，请核对单号。</p></template>
          <p v-if="dialogError" class="alert error" role="alert">{{ dialogError }}</p></div><footer><button type="button" class="button secondary" :disabled="saving" @click="closeDialog">取消</button><button class="button" :disabled="saving">{{ saving ? '保存中…' : tab === 'orders' ? '确认发货' : '保存修改' }}</button></footer>
        </form>
      </section>
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, ref } from 'vue';
import { useStore } from 'vuex';
import { apiClient } from '../../services/http';
import ImageUrlPreview from '../../components/common/ImageUrlPreview.vue';
import { parseImageUrls, isImageUrl } from '../../utils/productImages';
import MfaSettings from '../../components/forms/MfaSettings.vue';
const store = useStore();
const currentUser = computed(() => store.getters['auth/currentUser']);
const role = computed(() => String(currentUser.value?.role || currentUser.value?.user_role || '').toLowerCase());
const roleLabels = { admin: '管理员', merchant: '交易用户', normal: '交易用户', auditor: '审计员' };
const assignableRoles = { normal: '交易用户（买家 / 卖家）', admin: '管理员', auditor: '审计员' };
const orderLabels = { pending: '待处理', confirmed: '已确认', processing: '处理中', shipped: '已发货', delivered: '已送达', cancelled: '已取消', refunded: '已退款' };
const paymentLabels = { pending: '未支付', paid: '已支付', failed: '支付失败', refunded: '已退款' };
const permissionLabels = { 'catalog.read':'浏览商品', 'profile.self':'个人资料', 'cart.self':'自己的购物车', 'orders.self':'自己的订单', 'payment.self':'自己的支付', 'products.own':'自己的商品', 'users.manage':'用户管理', 'products.manage':'全部商品管理', 'categories.manage':'分类管理', 'orders.manage':'订单管理', 'audit.read':'查看审计', 'audit.export':'导出审计', 'security.read':'安全事件查询' };
const allTabs = [
  { id: 'security', label: '账号安全', icon: '◇', description: '更换身份验证器，恢复设备访问。', roles: ['admin','auditor'] },
  { id: 'overview', label: '运营概览', icon: '◫', description: '查看经营数据与当前待办事项。', roles: ['admin'] },
  { id: 'users', label: '用户管理', icon: '◎', description: '分配用户角色，管理账号访问状态。', roles: ['admin'] },
  { id: 'products', label: '商品管理', icon: '▣', description: '维护商品信息、库存和上架状态。', roles: ['admin','normal','merchant'] },
  { id: 'categories', label: '分类管理', icon: '≡', description: '维护商品分类与展示顺序。', roles: ['admin'] },
  { id: 'orders', label: '订单管理', icon: '▤', description: '查看订单付款状态，处理已付款订单的发货。', roles: ['admin'] },
  { id: 'audit', label: '日志与安全事件', icon: '◷', description: '追溯管理操作，查询访问拒绝和身份验证事件。', roles: ['admin','auditor'] },
  { id: 'permissions', label: '角色权限', icon: '◇', description: '查看各角色可访问的资源与操作。', roles: ['admin','auditor'] }
];
const tabs = computed(() => allTabs.filter(t => t.roles.includes(role.value)));
const tab = ref(role.value === 'auditor' ? 'audit' : ['normal', 'merchant'].includes(role.value) ? 'products' : 'overview');
const activeTab = computed(() => allTabs.find(t => t.id === tab.value));
const rows = ref([]), overview = ref({}), matrix = ref({}), categories = ref([]), total = ref(0), page = ref(1);
// 旧 merchant 与 normal 是同一种交易身份，矩阵只展示三个业务角色。
const visibleMatrix = computed(() => Object.fromEntries(
  ['normal', 'admin', 'auditor']
    .map(name => [name, matrix.value[name] ?? (name === 'normal' ? matrix.value.merchant : undefined)])
    .filter(([, permissions]) => permissions !== undefined)
));
const q = ref(''), filter = ref(''), since = ref(''), error = ref(''), notice = ref(''), loading = ref(false), saving = ref(false);
const dialog = ref(false), form = ref({}), dialogError = ref('');
let requestSequence = 0, previousFocus;
const metrics = [{key:'paid_total',label:'已支付订单金额',note:'当前支付状态为已支付的订单合计',money:true},{key:'orders',label:'订单总数',note:'累计创建的订单'},{key:'users',label:'注册用户',note:'系统内全部角色账号'},{key:'products',label:'在售商品',note:'当前已上架的商品数量'}];
const columnMap = {users:{username:'用户',email:'邮箱',user_role:'角色',is_active:'状态',last_login:'最近登录'},products:{product_name:'商品 / SKU',sale_price:'售价',stock_quantity:'库存',seller_id:'卖家 ID',status:'状态'},categories:{category_id:'ID',category_name:'分类名称',sort_order:'排序',is_active:'状态'},orders:{order_number:'订单',total_amount:'金额',order_status:'订单状态',payment_status:'支付状态',tracking_number:'物流单号'},audit:{created_at:'时间',username:'操作人',action:'事件',resource:'资源',result:'结果',ip:'来源 IP'}};
const columns = computed(() => Object.entries(columnMap[tab.value] || {}).map(([key,label])=>({key,label})));
const filterOptions = computed(() => ({users:roleLabels,products:{active:'已上架',inactive:'已下架'},orders:orderLabels,audit:{success:'成功',denied:'拒绝'}}[tab.value] || {}));
const searchPlaceholder = computed(() => ({users:'搜索用户名或邮箱',products:'搜索商品名或 SKU',orders:'搜索订单编号',audit:'搜索资源路径'}[tab.value] || '搜索'));
const dialogTitle = computed(() => ({users:'管理用户权限',products:form.value.product_id ? '编辑商品' : '新增商品',categories:form.value.category_id ? '编辑分类' : '新增分类',orders:'订单发货'}[tab.value]));
const productBase = computed(() => role.value !== 'admin' ? '/merchant/products' : '/admin/products');
const rowId = row => row.event_id || row.product_id || row.order_id || row.category_id || row.user_id;
const canEdit = row => tab.value === 'users' ? row.user_id !== currentUser.value.user_id : tab.value !== 'orders' || (row.payment_status === 'paid' && ['pending','confirmed','processing'].includes(row.order_status));
function display(key,val) {
  if (val === null || val === undefined || val === '') return '—';
  if (['last_login','created_at'].includes(key)) return new Date(val).toLocaleString('zh-CN',{hour12:false});
  if (['sale_price','total_amount'].includes(key)) return '¥' + val;
  if (key === 'is_active') return val ? '正常' : '停用';
  return ({user_role:roleLabels,order_status:orderLabels,payment_status:paymentLabels,status:{active:'已上架',inactive:'已下架'},result:{success:'成功',denied:'拒绝'}}[key] || {})[val] || val;
}
function cellClass(key,val) { if (['is_active','status','result','user_role','order_status'].includes(key)) return ['badge', [true,'active','success'].includes(val)?'green':[false,'denied'].includes(val)?'red':'']; return key === 'stock_quantity' && val < 10 ? 'low' : ''; }
const params = () => ({page:page.value,page_size:20,q:q.value,...(tab.value === 'users' ? {role:filter.value} : tab.value === 'audit' ? {result:filter.value,since:since.value} : {status:filter.value})});
async function load() {
  if (tab.value === 'security') { ++requestSequence; loading.value = false; return; }
  const sequence = ++requestSequence; loading.value = true; error.value = '';
  try {
    const url = tab.value === 'audit' ? '/audit/events' : tab.value === 'permissions' ? '/audit/permissions' : tab.value === 'products' ? productBase.value : '/admin/' + tab.value;
    const response = await apiClient.request('GET', url, null, {params:params()});
    if (sequence !== requestSequence) return;
    if (response.code !== 0) throw new Error(response.message);
    if (tab.value === 'overview') overview.value = response.data;
    else if (tab.value === 'permissions') matrix.value = response.data;
    else if (tab.value === 'categories') rows.value = response.data;
    else { rows.value = response.data.items; total.value = response.data.total; }
  } catch (e) { if (sequence === requestSequence) { error.value = e.message; rows.value = []; } }
  finally { if (sequence === requestSequence) loading.value = false; }
}
function selectTab(id) { tab.value=id;page.value=1;q.value='';filter.value='';since.value='';notice.value='';load(); }
function search() {page.value=1;load();}
function changePage(delta) {page.value+=delta;load();}
async function edit(row = {}) {
  previousFocus=document.activeElement;form.value={product_name:'',sku:'',category_id:'',sale_price:'',stock_quantity:0,description:'',status:'active',sort_order:0,is_active:true,...row,role:row.user_role === 'merchant' ? 'normal' : row.user_role,image_urls_text:(row.image_urls || []).join('\n')};dialogError.value='';dialog.value=true;
  if(tab.value==='products') {try {const response=await apiClient.request('GET',role.value==='admin'?'/admin/categories':'/categories');categories.value=(response.data || []).filter(c=>c.is_active!==false);} catch(e){dialogError.value=e.message;}}
  await nextTick();document.querySelector('.admin-dialog input, .admin-dialog select')?.focus();
}
function closeDialog(){if(!saving.value){dialog.value=false;previousFocus?.focus();}}
function trapFocus(event){const nodes=[...document.querySelectorAll('.admin-dialog button:not(:disabled),.admin-dialog input,.admin-dialog select,.admin-dialog textarea')];if(!nodes.length)return;const first=nodes[0],last=nodes[nodes.length-1];if(event.shiftKey&&document.activeElement===first){event.preventDefault();last.focus();}else if(!event.shiftKey&&document.activeElement===last){event.preventDefault();first.focus();}}
async function save() {
  saving.value=true;dialogError.value='';
  try {
    const f=form.value;let url,method,data;
    if(tab.value==='users'){url=`/admin/users/${f.user_id}`;method='PATCH';data={role:f.role,is_active:f.is_active};}
    if(tab.value==='products'){const images=parseImageUrls(f.image_urls_text);if(images.length>8 || images.some(url=>!isImageUrl(url)))throw new Error('请填写有效的 HTTP / HTTPS 图片链接，最多 8 张');url=productBase.value+(f.product_id?`/${f.product_id}`:'');method=f.product_id?'PUT':'POST';data={sku:f.sku,product_name:f.product_name,description:f.description,sale_price:f.sale_price,stock_quantity:f.stock_quantity,category_id:f.category_id,status:f.status,image_urls:images};if(f.seller_id&&role.value==='admin')data.seller_id=f.seller_id;}
    if(tab.value==='categories'){url='/admin/categories'+(f.category_id?`/${f.category_id}`:'');method=f.category_id?'PUT':'POST';data={category_name:f.category_name,sort_order:f.sort_order,is_active:f.is_active};}
    if(tab.value==='orders'){url=`/admin/orders/${f.order_id}/ship`;method='POST';data={tracking_number:f.tracking_number};}
    const response=await apiClient.request(method,url,data);if(response.code!==0)throw new Error(response.message);
    dialog.value=false;notice.value=response.message||'已保存';previousFocus?.focus();await load();
  }catch(e){dialogError.value=e.message;}finally{saving.value=false;}
}
async function exportAudit(){saving.value=true;error.value='';try{const data=await apiClient.request('GET','/audit/export',null,{params:params()});const url=URL.createObjectURL(new Blob([JSON.stringify(data,null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download='audit-report.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);notice.value='已导出筛选范围内最近 10000 条记录';await load();}catch(e){error.value=e.message;}finally{saving.value=false;}}
onMounted(load);
</script>

<style scoped>
.console{display:flex;min-height:calc(100vh - 160px);background:#f5f6fa;color:#333;font-family:inherit}.console-nav{width:240px;flex-shrink:0;background:#1f2937;color:#d1d5db;padding:32px 16px;display:flex;flex-direction:column}.nav-caption{font-size:14px;color:#d1d5db;padding:0 16px;margin-bottom:16px}.console-nav>button{border:0;text-align:left;font:inherit;font-size:16px;background:transparent;color:#d1d5db;padding:12px 16px;border-radius:4px;margin-bottom:8px;cursor:pointer}.console-nav>button span{display:inline-block;width:28px;font-size:19px;vertical-align:middle}.console-nav>button.selected{background:#2563eb;color:#fff}.console-nav>button:hover:not(.selected){background:#374151}.workspace{flex:1;min-width:0;padding:24px}.page-heading{display:flex;justify-content:space-between;align-items:center;gap:16px;margin-bottom:28px}.eyebrow{font-size:14px;color:#6c757d;margin-bottom:14px}h1{font-size:28px;margin:0 0 8px;font-weight:600}.subtitle{font-size:14px;color:#6c757d}.button{border:1px solid transparent;background:#007bff;color:white;padding:9px 16px;border-radius:4px;font:inherit;font-size:14px;cursor:pointer;white-space:nowrap}.button.secondary{background:white;border-color:#ddd;color:#6c757d}.button:hover{filter:brightness(.96)}button:disabled{opacity:.45;cursor:not-allowed}.metrics{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:18px;margin-bottom:24px}.metrics article{background:white;border:1px solid #e9ecef;border-radius:8px;padding:24px}.metrics span{font-size:14px;color:#6c757d}.metrics strong{display:block;font-size:29px;color:#333;margin:19px 0 13px;overflow-wrap:anywhere;font-variant-numeric:tabular-nums}.metrics small{font-size:12px;color:#6c757d}.panel{background:white;border:1px solid #e9ecef;border-radius:8px;padding:24px}h2{font-size:20px;margin:0 0 24px;font-weight:600}.overview-grid{display:grid;grid-template-columns:1.4fr 1fr;gap:24px}.task-row{display:flex;justify-content:space-between;align-items:center;width:100%;padding:18px 0;border:0;border-top:1px solid #e9ecef;background:white;text-align:left;color:#333;cursor:pointer}.task-row strong{font-size:14px}.task-row small{display:block;color:#6c757d;font-size:14px;margin-top:7px}.task-row b{font-size:18px;font-weight:500;color:#007bff}.explanation{font-size:14px;line-height:1.9;color:#6c757d;margin-bottom:24px}.toolbar{display:flex;justify-content:space-between;gap:14px;flex-wrap:wrap;margin-bottom:24px}.filters{display:flex;gap:10px;flex-wrap:wrap}input,select,textarea{font:inherit;font-size:14px;border:1px solid #ddd;padding:9px 11px;border-radius:4px;background:white;color:#333;min-width:0}.filters input{max-width:220px}input:focus,select:focus,textarea:focus{outline:2px solid #81a9ef;outline-offset:1px}.table-scroll{overflow:auto}.table-scroll table{min-width:760px}table{width:100%;border-collapse:collapse;text-align:left;font-size:14px;white-space:nowrap}th{font-weight:500;color:#6c757d;background:#f8f9fa;padding:14px}td{padding:19px 14px;border-bottom:1px solid #e9ecef;color:#333}td small{display:block;font-size:12px;color:#6c757d;margin-top:7px}.resource{max-width:300px;overflow-wrap:anywhere;white-space:normal}.badge{display:inline-block;background:#f0f3f7;color:#6d7b90;font-size:12px;padding:5px 9px;border-radius:4px}.green{background:#eaf6f0;color:#319169}.red{background:#fff0ef;color:#be5049}.low{color:#d08a27;font-weight:600}.text-button{border:0;background:transparent;color:#007bff;font:inherit;cursor:pointer;padding:5px 0}.pagination{display:flex;justify-content:space-between;align-items:center;margin-top:22px;font-size:14px;color:#6c757d;gap:15px}.pagination>div{display:flex;gap:8px}.empty{text-align:center;padding:70px 20px}.empty p{color:#6c757d;margin-top:12px}.footer-note{font-size:12px;color:#6c757d;margin-top:25px}.alert{font-size:14px;padding:13px 16px;border-radius:4px;margin-bottom:18px}.error{background:#fff0ef;color:#aa3e35}.success{background:#e9f6ef;color:#247a56}.loading{padding:70px;text-align:center;color:#6c757d}.permission{display:inline-block;margin:3px 5px 3px 0;padding:5px 8px;background:#f1f5fb;border-radius:4px}.hint{font-size:14px;line-height:1.8;color:#6c757d}@media(max-width:1200px){.metrics{grid-template-columns:repeat(2,minmax(0,1fr))}}@media(max-width:760px){.console{display:block}.console-nav{width:100%;padding:16px;display:flex;flex-direction:row;flex-wrap:wrap;gap:4px}.nav-caption,.console-nav>button{padding:8px;font-size:14px;margin:0}.console-nav>button span{display:none}.workspace{padding:16px}.page-heading{align-items:flex-start}h1{font-size:23px}.metrics{gap:10px}.metrics article{padding:18px 14px}.metrics strong{font-size:24px}.overview-grid{grid-template-columns:1fr}.panel{padding:16px}.pagination{flex-wrap:wrap}.form-grid{grid-template-columns:1fr}.subtitle{line-height:1.7}.records{padding:12px}}

.metrics article,.panel{box-shadow:0 2px 8px rgba(0,0,0,.06)}
.button:hover:not(:disabled){background:#0056b3;filter:none}
.button.secondary:hover:not(:disabled){background:#f8f9fa}
.console-nav>button:focus-visible,.button:focus-visible,.text-button:focus-visible{outline:2px solid #80bdff;outline-offset:3px}
@media(min-width:769px){.console-nav{align-self:flex-start;position:sticky;top:80px;min-height:calc(100vh - 80px)}}
@media(max-width:768px){.console{display:block}.console-nav{width:100%;min-height:0;flex-direction:row;flex-wrap:wrap;gap:4px;padding:16px}.nav-caption{display:none}.console-nav>button{padding:8px;font-size:14px;margin:0}.workspace{padding:16px}.filters{width:100%}.filters input{max-width:100%;flex:1 1 160px}}

/* Dedicated dialog classes avoid the shared full-screen .modal rules. */
.modal-backdrop{position:fixed;inset:0;z-index:1100;background:rgba(0,0,0,.45);display:flex;align-items:center;justify-content:center;padding:24px}
.admin-dialog{width:520px;max-width:100%;max-height:calc(100dvh - 48px);display:flex;flex-direction:column;overflow:hidden;background:white;border:1px solid #e9ecef;border-radius:12px;box-shadow:0 20px 60px rgba(0,0,0,.2)}
.admin-dialog.product-dialog{width:800px}
.admin-dialog>header{display:flex;flex:none;align-items:center;justify-content:space-between;gap:16px;padding:20px 24px;border-bottom:1px solid #e9ecef}
.admin-dialog h2{margin:0;font-size:20px}
.admin-dialog .close{width:36px;height:36px;flex:none;border:0;border-radius:6px;background:#f8f9fa;color:#6c757d;font-size:26px;cursor:pointer}
.dialog-form{display:flex;flex-direction:column;min-height:0;overflow:hidden}
.dialog-body{display:grid;gap:20px;padding:24px;overflow-y:auto;min-height:0;overscroll-behavior:contain}
.admin-dialog label{display:grid;gap:8px;min-width:0;font-size:14px;font-weight:500;color:#333}
.admin-dialog input,.admin-dialog select,.admin-dialog textarea{width:100%;min-width:0;min-height:42px;padding:10px 12px;font-size:14px;line-height:1.5;box-sizing:border-box}
.admin-dialog textarea{resize:vertical;min-height:90px;max-height:240px}
.admin-dialog .form-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:20px}
.admin-dialog .hint{margin:0;overflow-wrap:anywhere;line-height:1.7}
.admin-dialog .alert{margin:0}
.dialog-form>footer{display:flex;flex:none;justify-content:flex-end;gap:12px;padding:16px 24px;background:#f8f9fa;border-top:1px solid #e9ecef}
.dialog-form>footer .button{min-width:100px;min-height:42px}
@media(max-width:576px){.modal-backdrop{padding:12px}.admin-dialog{max-height:calc(100dvh - 24px);border-radius:10px}.admin-dialog>header{padding:16px}.dialog-body{padding:16px;gap:16px}.admin-dialog .form-grid{grid-template-columns:1fr;gap:16px}.dialog-form>footer{padding:12px 16px}.dialog-form>footer .button{flex:1;min-width:0}}
</style>

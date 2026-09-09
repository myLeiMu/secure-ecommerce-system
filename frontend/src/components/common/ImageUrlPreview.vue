<template>
  <div class="image-previews" aria-label="商品图片预览">
    <figure v-for="url in urls" :key="url">
      <img v-if="isImageUrl(url) && !failed[url]" :src="url" alt="商品图片预览" referrerpolicy="no-referrer" @error="failed[url] = true" />
      <p v-else role="status">图片无法加载，请检查是否为可公开访问的图片直链。</p>
    </figure>
  </div>
</template>
<script setup>
import { computed, ref, watch } from 'vue';
import { parseImageUrls, isImageUrl } from '../../utils/productImages';
const props = defineProps({ value: { type: String, default: '' } });
const urls = computed(() => parseImageUrls(props.value));
const failed = ref({});
watch(() => props.value, () => { failed.value = {}; });
</script>
<style scoped>
.image-previews{display:flex;flex-wrap:wrap;gap:12px}.image-previews figure{margin:0;width:120px;min-height:90px;border:1px solid #ddd;border-radius:8px;overflow:hidden;background:#f8f9fa}.image-previews img{display:block;width:100%;height:100px;object-fit:contain}.image-previews p{padding:10px;font-size:12px;color:#6c757d}
</style>

// Preserve commas in CDN transformation parameters; retain old comma-separated URLs.
export function parseImageUrls(text = '') {
  return text.split(/\r?\n|,\s*(?=https?:\/\/)/i).map(url => url.trim()).filter(Boolean);
}

export function isImageUrl(url) {
  if (/^\/(?!\/)/.test(url)) return true;
  try { return ['http:', 'https:'].includes(new URL(url).protocol); }
  catch { return false; }
}

import { parseImageUrls, isImageUrl } from '../utils/productImages';

test('preserves commas and signed query strings in image URLs', () => {
  const url = 'https://cdn.example.com/image?resize=width,800&signature=a%2Bb%3D';
  expect(parseImageUrls(url)).toEqual([url]);
  expect(parseImageUrls(`${url}\nhttps://example.com/second.png`)).toEqual([url, 'https://example.com/second.png']);
});

test('supports legacy URL separators and ignores empty lines', () => {
  expect(parseImageUrls(' https://example.com/a.jpg,https://example.com/b.jpg\n\n'))
    .toEqual(['https://example.com/a.jpg', 'https://example.com/b.jpg']);
});

test('allows network images without file extensions and rejects executable schemes', () => {
  expect(isImageUrl('https://example.com/image?id=123')).toBe(true);
  expect(isImageUrl('http://example.com/photo.png')).toBe(true);
  expect(isImageUrl('/products/cat.jpg')).toBe(true);
  expect(isImageUrl('javascript:alert(1)')).toBe(false);
  expect(isImageUrl('not a URL')).toBe(false);
});

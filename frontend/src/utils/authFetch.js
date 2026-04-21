export function authFetch(url, options = {}) {
  const token = sessionStorage.getItem('adminToken');
  
  const headers = {
    'Authorization': `Bearer ${token}`,
    ...(options.headers || {}),
  };

  // 🟢 บังคับใส่ Content-Type เป็น JSON ถ้ามีการส่งข้อมูล (body)
  if (options.body && !(options.body instanceof FormData)) {
    if (!headers['Content-Type']) {
      headers['Content-Type'] = 'application/json';
    }
  }

  return fetch(url, {
    ...options,
    headers,
  });
}
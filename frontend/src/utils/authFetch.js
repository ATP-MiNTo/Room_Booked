export function authFetch(url, options = {}) {
  const token = sessionStorage.getItem('adminToken');
  return fetch(url, {
    ...options,
    headers: {
      ...(options.headers || {}),
      'Authorization': `Bearer ${token}`,
    },
  });
}
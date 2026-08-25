export const apiFetch = async (input: RequestInfo | URL, init?: RequestInit) => {
  const token = localStorage.getItem('token');
  const headers = new Headers(init?.headers);
  
  if (token) {
    headers.set('Authorization', `Bearer ${token}`);
  }
  
  const response = await fetch(input, {
    ...init,
    headers,
  });
  
  if (response.status === 401) {
    // Optionally trigger a logout event here if the token expired
    console.error('Unauthorized request - token may be expired');
    // localStorage.removeItem('token');
    // window.location.href = '/login';
  }
  
  return response;
};

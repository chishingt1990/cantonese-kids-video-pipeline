(function (root) {
  'use strict';
  function createClient(fetchImpl, onError = () => {}) {
    let session;
    async function checked(url, options) {
      const response = await fetchImpl(url, options);
      if (!response.ok) {
        let detail;
        try { detail = (await response.clone().json()).detail; } catch (_) {}
        const message = typeof detail === 'string' ? detail
          : typeof detail?.message === 'string' ? detail.message
          : `Request failed (HTTP ${response.status})`;
        const error = new Error(message);
        error.status = response.status;
        const code = detail?.code || response.headers?.get('X-Studio-Error-Code');
        if (code) error.code = code;
        throw error;
      }
      return response;
    }
    return async function request(url, options = {}) {
      try {
        const headers = new Headers(options.headers || {});
        if (!['GET', 'HEAD', 'OPTIONS'].includes((options.method || 'GET').toUpperCase())) {
          if (!session) {
            session = checked('/api/session', { credentials: 'same-origin' })
              .then(r => r.json()).then(data => {
                if (!data.csrf_token) throw new Error('Studio session unavailable. Reload the page.');
                return data.csrf_token;
              }).catch(error => { session = null; throw error; });
          }
          headers.set('X-Studio-Token', await session);
        }
        return await checked(url, { ...options, headers, credentials: 'same-origin' });
      } catch (error) {
        if (error.status === 403) session = null;
        onError(error);
        throw error;
      }
    };
  }
  const escapeHTML = value => String(value ?? '').replace(/[&<>"']/g, c => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  }[c]));
  // For a string inside a quoted inline handler: JS escaping must precede HTML escaping.
  const handlerArg = value => escapeHTML(JSON.stringify(String(value ?? ''))
    .slice(1, -1).replace(/'/g, '\\u0027'));
  function safeURL(value) {
    const url = String(value || '');
    return !/[\\\u0000-\u0020]/.test(url) && /^(\/(?!\/)|https?:\/\/)/i.test(url) ? url : '';
  }
  const api = { createClient, escapeHTML, handlerArg, safeURL };
  if (typeof module !== 'undefined') module.exports = api;
  else {
    root.StudioAPI = api;
    root.studioFetch = createClient(root.fetch.bind(root), error => {
      if (typeof root.showToast === 'function') root.showToast(error.message);
      else {
        let notice = document.getElementById('studio-api-error');
        if (!notice) {
          notice = document.createElement('div');
          notice.id = 'studio-api-error';
          notice.className = 'fixed bottom-6 right-6 bg-rose-100 text-rose-800 rounded-xl p-4 z-50';
          notice.setAttribute('role', 'alert');
          document.body.appendChild(notice);
        }
        notice.textContent = error.message;
      }
    });
  }
})(typeof window === 'undefined' ? globalThis : window);

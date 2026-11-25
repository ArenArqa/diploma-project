let token = null;
export let account = null;
export function setSession(accessToken, user) {
  token = accessToken; account = user;
  document.dispatchEvent(new CustomEvent('sessionchange', {detail: user}));
}
export class ApiError extends Error {
  constructor(status, code, message) { super(message); this.status = status; this.code = code; }
}
export async function api(path, options = {}) {
  const headers = {...options.headers};
  if (token) headers.Authorization = `Bearer ${token}`;
  let body = options.body;
  if (body && !(body instanceof URLSearchParams) && !(body instanceof FormData)) { headers['Content-Type'] = 'application/json'; body = JSON.stringify(body); }
  const response = await fetch(`/api/v1${path}`, {...options, headers, body});
  const data = await response.json();
  if (!response.ok) {
    if (response.status === 401 && token) setSession(null, null);
    const error = data.error || {};
    const details = error.details?.map?.(x => x.message).join('; ');
    throw new ApiError(response.status, error.code, details || error.message || 'The request could not be completed.');
  }
  return data;
}
export function esc(value) { return String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }
export function amd(value) { return `${new Intl.NumberFormat('en-US', {maximumFractionDigits: 0}).format(Number(value))} ֏`; }
let toastTimer;
export function notify(message, error = false) {
  const toast = document.querySelector('#toast'); toast.textContent = message; toast.classList.toggle('error', error); toast.hidden = false;
  clearTimeout(toastTimer); toastTimer = setTimeout(() => toast.hidden = true, 6500);
}
export function handleError(error) { console.error(error); notify(error.message || 'Check your connection and try again.', true); }
export function on(element, event, handler) {
  if (typeof element === 'string') element = document.querySelector(element);
  element.addEventListener(event, e => Promise.resolve().then(() => handler(e)).catch(handleError));
}
export function tab(name) {
  document.querySelectorAll('.tab-panel').forEach(el => el.hidden = el.id !== name);
  document.querySelectorAll('[data-tab]').forEach(el => el.classList.toggle('active', el.dataset.tab === name));
}
export function businessToday() {
  const parts = new Intl.DateTimeFormat('en-CA', {timeZone:'Asia/Yerevan', year:'numeric', month:'2-digit', day:'2-digit'}).formatToParts(new Date());
  const values = Object.fromEntries(parts.map(p => [p.type,p.value])); return `${values.year}-${values.month}-${values.day}`;
}
export function addDays(date, days) { const d = new Date(`${date}T12:00:00Z`); d.setUTCDate(d.getUTCDate()+days); return d.toISOString().slice(0,10); }
document.querySelectorAll('[data-tab]').forEach(button => on(button, 'click', () => tab(button.dataset.tab)));
document.querySelectorAll('[data-close]').forEach(button => on(button, 'click', () => document.getElementById(button.dataset.close).close()));
export const references = Promise.all([api('/brands'), api('/models')]).then(([brands, models]) => ({brands, models}));
references.catch(handleError);

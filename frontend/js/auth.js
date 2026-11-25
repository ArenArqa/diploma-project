import {api, on, setSession, notify} from './api.js';
const dialog = document.querySelector('#auth-dialog'); let registering = false;
on('#login-open','click', () => dialog.showModal());
on('#logout','click', () => { setSession(null,null); notify('You have signed out.'); });
on('#auth-toggle','click', () => {
  registering = !registering;
  document.querySelector('#register-name-label').hidden = !registering;
  document.querySelector('[name=full_name]').required = registering;
  document.querySelector('#auth-submit').textContent = registering ? 'Create account ↗' : 'Sign in ↗';
  document.querySelector('#auth-toggle').textContent = registering ? 'Already registered? Sign in' : 'New here? Create an account';
});
on('#auth-form','submit', async e => {
  e.preventDefault(); const values = Object.fromEntries(new FormData(e.target));
  const button = document.querySelector('#auth-submit'); button.disabled = true;
  try {
    if (registering) await api('/auth/register', {method:'POST',body:values});
    const auth = await api('/auth/token', {method:'POST',body:new URLSearchParams({username:values.email,password:values.password})});
    setSession(auth.access_token,null);
    const user = await api('/users/me'); setSession(auth.access_token,user);
    dialog.close(); e.target.reset(); notify(`Welcome, ${user.full_name}.`);
  } finally { button.disabled = false; }
});
document.addEventListener('sessionchange', e => {
  const user = e.detail;
  document.querySelector('#account-name').textContent = user ? `${user.full_name} · ${user.role}` : '';
  document.querySelector('#login-open').hidden = !!user; document.querySelector('#logout').hidden = !user;
});

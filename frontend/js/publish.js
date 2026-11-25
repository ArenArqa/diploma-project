import {api, account, references, on, esc, businessToday, notify, handleError} from './api.js';
const form = document.querySelector('#publish-form');
const fileInput = document.querySelector('#publish-image');
const preview = document.querySelector('#publish-preview');
let previewUrl = null, carId = null, uploadedFile = null;
const year = document.querySelector('#publish-year');
year.value = Number(businessToday().slice(0, 4)) - 5;
year.max = Number(businessToday().slice(0, 4)) + 1;
references.then(({models, brands}) => {
  document.querySelector('#publish-model').innerHTML = models.map(m =>
    `<option value="${m.id}">${esc(brands.find(b => b.id === m.brand_id)?.name)} ${esc(m.name)}</option>`).join('');
}).catch(handleError);
function selectedFile() {
  const file = fileInput.files[0];
  if (file && (!['image/jpeg', 'image/png', 'image/webp'].includes(file.type) ||
      !/\.(jpe?g|png|webp)$/i.test(file.name) || file.size > 5 * 1024 * 1024)) {
    throw new Error('Choose a JPG, PNG, or WebP file of at most 5 MB.');
  }
  return file;
}
on(fileInput, 'change', () => {
  if (previewUrl) URL.revokeObjectURL(previewUrl);
  preview.hidden = true; preview.removeAttribute('src'); previewUrl = null;
  try {
    const file = selectedFile();
    if (file) { previewUrl = URL.createObjectURL(file); preview.src = previewUrl; preview.hidden = false; }
  } catch (error) { fileInput.value = ''; throw error; }
});
on('#publish-open', 'click', () => {
  if (!account) { document.querySelector('#auth-dialog').showModal(); return; }
  document.querySelector('#publish-type option[value=rent]').disabled = account.role === 'user';
  if (account.role === 'user') document.querySelector('#publish-type').value = 'sale';
  document.querySelector('#publish-dialog').showModal();
});
document.addEventListener('sessionchange', () => {
  document.querySelector('#publish-dialog').close();
  form.reset(); carId = null; uploadedFile = null;
  document.querySelector('#vehicle-fields').disabled = false;
  document.querySelector('#publish-status').textContent = '';
  if (previewUrl) URL.revokeObjectURL(previewUrl);
  previewUrl = null; preview.hidden = true; preview.removeAttribute('src');
});
on(form, 'submit', async e => {
  e.preventDefault();
  if (!account) throw new Error('Sign in to publish a listing.');
  const file = selectedFile();
  const values = Object.fromEntries(new FormData(form));
  const button = form.querySelector('[type=submit]'); button.disabled = true;
  const status = document.querySelector('#publish-status');
  try {
    if (!carId) {
      status.textContent = 'Saving car details…';
      const car = await api('/cars', {method:'POST', body:{
        model_id: values.model_id, vin: values.vin, year: Number(values.year),
        mileage_km: Number(values.mileage_km), fuel_type: values.fuel_type,
        transmission: values.transmission, condition: values.condition,
      }});
      carId = car.id;
      document.querySelector('#vehicle-fields').disabled = true;
    }
    if (file && file !== uploadedFile) {
      status.textContent = 'Uploading image…';
      const data = new FormData(); data.append('file', file);
      await api(`/cars/${carId}/image`, {method:'POST', body:data});
      uploadedFile = file;
    }
    status.textContent = 'Publishing listing…';
    await api('/listings', {method:'POST', body:{car_id:carId, listing_type:values.listing_type,
      title:values.title, description:values.description, city:values.city, price_amd:values.price_amd}});
    document.querySelector('#publish-dialog').close();
    form.reset(); carId = null; uploadedFile = null;
    document.querySelector('#vehicle-fields').disabled = false; status.textContent = '';
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    previewUrl = null; preview.hidden = true; preview.removeAttribute('src');
    notify('Your listing is published.'); document.dispatchEvent(new Event('listingpublished'));
  } catch (error) {
    status.textContent = carId ? 'Car details saved. Correct the issue and retry to continue with this car.' : '';
    throw error;
  } finally { button.disabled = false; }
});

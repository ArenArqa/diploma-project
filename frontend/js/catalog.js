import {api, references, on, esc, amd, tab, handleError} from './api.js';
const form = document.querySelector('#search-form'); let offset = 0; const limit = 9;
const carSvg = `<svg viewBox="0 0 360 160" fill="none" aria-hidden="true"><ellipse cx="180" cy="131" rx="135" ry="9" fill="#172d39" opacity=".09"/><path d="M35 103l24-17 27-7 35-42c9-8 23-11 37-11h58c15 0 28 7 39 17l38 37 26 9 10 20-6 12H37l-7-8 5-10Z" fill="#587681"/><path d="M126 40h38v36H99l27-36Zm48 0h39c9 0 17 5 24 12l25 24h-88V40Z" fill="#c7e1e6"/><path d="M42 103h273M169 81v33m-72-33-7 30" stroke="#395461" stroke-width="2"/><rect x="181" y="84" width="16" height="4" rx="2" fill="#d5e4e8"/><circle cx="96" cy="117" r="25" fill="#263c48"/><circle cx="96" cy="117" r="13" fill="#bac9cf"/><circle cx="270" cy="117" r="25" fill="#263c48"/><circle cx="270" cy="117" r="13" fill="#bac9cf"/><path d="M39 97h21v9H36m270-13h14l4 12h-18" fill="#e8f1d0"/></svg>`;
function carImage(car, detail = false) {
  const fallback = `<span class="car-image-fallback">${carSvg}</span>`;
  return `<div class="car-photo${detail ? ' detail-photo' : ''}">${fallback}${car.image_url ? `<img src="${esc(car.image_url)}" alt="${esc(car.brand.name)} ${esc(car.model.name)}" loading="${detail ? 'eager' : 'lazy'}" decoding="async">` : ''}</div>`;
}
// Capture resource errors: keep the existing vector illustration beneath failed images.
document.addEventListener('error', e => {
  if (e.target.matches?.('.car-photo img')) { e.target.hidden = true; e.target.parentElement.classList.remove('has-image'); }
}, true);
document.addEventListener('load', e => {
  if (e.target.matches?.('.car-photo img')) e.target.parentElement.classList.add('has-image');
}, true);
document.addEventListener('listingpublished', () => { offset = 0; search().catch(handleError); });
export function modelOptions(models, brands, blank = true) {
  return (blank ? '<option value="">All models</option>' : '') + models.map(m => `<option value="${m.id}">${esc(brands.find(b=>b.id===m.brand_id)?.name)} ${esc(m.name)}</option>`).join('');
}
async function refreshModels() {
  const {models,brands} = await references;
  document.querySelector('#search-model').innerHTML = modelOptions(models.filter(m => !form.brand_id.value || m.brand_id===form.brand_id.value),brands);
}
async function search() {
  document.querySelector('#results-count').textContent = 'Finding your next move…';
  const params = new URLSearchParams();
  for (const [key,value] of new FormData(form)) if (value !== '') params.set(key,value);
  params.set('limit',limit); params.set('offset',offset);
  const result = await api(`/listings?${params}`);
  document.querySelector('#results-count').textContent = `${result.total} cars to explore`;
  document.querySelector('#listing-grid').innerHTML = result.items.length ? result.items.map((l,i) => `<article class="listing-card"><div class="car-art ${['','blue','sand'][i%3]}"><span class="listing-badge">${l.listing_type==='rent'?'For rent':'For sale'}</span>${carImage(l.car)}</div><div class="listing-body"><h3 class="listing-title">${esc(l.title)}</h3><p class="car-specs">${l.car.year} <span>·</span> ${Number(l.car.mileage_km).toLocaleString()} km <span>·</span> ${esc(l.car.fuel_type)}</p><p class="car-specs">${esc(l.city)} · ${esc(l.car.transmission)}</p><div class="listing-bottom"><span class="price">${amd(l.price_amd)}${l.listing_type==='rent'?'<small> / day base</small>':''}</span><button class="card-action" data-listing="${l.id}" aria-label="View ${esc(l.title)}">↗</button></div></div></article>`).join('') : '<p class="empty">No cars match these filters. Try a wider search.</p>';
  document.querySelector('#previous-page').disabled = offset === 0;
  document.querySelector('#next-page').disabled = offset + limit >= result.total;
  document.querySelector('#page-label').textContent = `Page ${Math.floor(offset/limit)+1} of ${Math.max(1,Math.ceil(result.total/limit))}`;
}
on(form,'submit', e => { e.preventDefault(); offset=0; return search(); });
on(form,'reset', () => setTimeout(() => { offset=0; refreshModels().then(search).catch(handleError); },0));
on('#search-brand','change', refreshModels);
on('#previous-page','click', () => { offset = Math.max(0,offset-limit); return search(); });
on('#next-page','click', () => { offset += limit; return search(); });
on('#listing-grid','click', async e => {
  const button = e.target.closest('[data-listing]'); if (!button) return;
  const [listing,history] = await Promise.all([api(`/listings/${button.dataset.listing}`),api(`/listings/${button.dataset.listing}/price-history`)]);
  document.querySelector('#listing-detail').innerHTML = `${carImage(listing.car, true)}<p class="eyebrow">${esc(listing.city)} · ${esc(listing.listing_type)}</p><h2>${esc(listing.title)}</h2><p class="result-price">${amd(listing.price_amd)}${listing.listing_type==='rent'?' / day base':''}</p><p class="muted">${listing.car.year} · ${listing.car.mileage_km.toLocaleString()} km · ${esc(listing.car.condition)} condition</p><p class="listing-description">${esc(listing.description)}</p><h3>Price history</h3><div class="table-wrap"><table><thead><tr><th>Observed</th><th>Price</th></tr></thead><tbody>${history.items.map(h=>`<tr><td>${new Date(h.changed_at).toLocaleDateString()}</td><td>${amd(h.new_price_amd)}</td></tr>`).join('')}</tbody></table></div>${listing.listing_type==='rent'?`<button class="button" id="detail-rent">Check rental dates ↗</button>`:''}`;
  document.querySelector('#listing-dialog').showModal();
  if (listing.listing_type==='rent') on('#detail-rent','click', () => { document.querySelector('#listing-dialog').close(); tab('rental'); document.dispatchEvent(new CustomEvent('selectrental',{detail:listing.id})); });
});
references.then(async ({brands}) => { document.querySelector('#search-brand').innerHTML += brands.map(b=>`<option value="${b.id}">${esc(b.name)}</option>`).join(''); await refreshModels(); await search(); }).catch(handleError);

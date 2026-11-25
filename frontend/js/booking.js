import {api,account,on,esc,amd,businessToday,addDays,notify,handleError} from './api.js';
const select = document.querySelector('#rental-listing'), start = document.querySelector('#rental-start'), end = document.querySelector('#rental-end');
const today = businessToday(), latest = addDays(today,365); start.min=end.min=today; start.max=end.max=latest;
start.value=end.value=addDays(today,1);
let month = new Date(`${today.slice(0,7)}-01T12:00:00Z`), blocked=[], choosingEnd=false, quote=null;
function clearQuote() { quote=null; document.querySelector('#quote-result').innerHTML='<span class="large-symbol">↗</span><h3>Your journey, priced clearly.</h3><p class="muted">Choose your dates, then request a quote. Availability is checked again when you book.</p>'; }
function renderCalendar() {
  document.querySelector('#calendar-month').textContent = month.toLocaleDateString('en-US',{month:'long',year:'numeric',timeZone:'UTC'});
  const first = (month.getUTCDay()+6)%7, count = new Date(Date.UTC(month.getUTCFullYear(),month.getUTCMonth()+1,0)).getUTCDate();
  let html = '<span></span>'.repeat(first);
  for(let n=1;n<=count;n++) { const date=`${month.toISOString().slice(0,7)}-${String(n).padStart(2,'0')}`; const unavailable=blocked.some(b=>date>=b.start_date&&date<=b.end_date); html+=`<button type="button" data-date="${date}" ${date<today||date>latest||unavailable?'disabled':''} class="${unavailable?'blocked ':''}${date===start.value||date===end.value?'selected':date>start.value&&date<end.value?'in-range':''}" aria-label="${date}${unavailable?' unavailable':''}">${n}</button>`; }
  document.querySelector('#calendar-days').innerHTML=html;
}
async function refreshCalendar() {
  if(!select.value)return;
  const result=await api(`/listings/${select.value}/availability?start_date=${today}&end_date=${latest}`); blocked=result.blocked_intervals; renderCalendar();
}
async function loadRentals() {
  const result=await api('/listings?listing_type=rent&limit=100'); select.innerHTML=result.items.map(l=>`<option value="${l.id}">${esc(l.title)} · ${amd(l.price_amd)}/day base</option>`).join('');
  await refreshCalendar();
}
const rentalsReady=loadRentals(); rentalsReady.catch(handleError);
on('#calendar-prev','click',()=>{month.setUTCMonth(month.getUTCMonth()-1);renderCalendar();});
on('#calendar-next','click',()=>{month.setUTCMonth(month.getUTCMonth()+1);renderCalendar();});
on('#calendar-days','click',e=>{const b=e.target.closest('[data-date]');if(!b||b.disabled)return;if(!choosingEnd){start.value=end.value=b.dataset.date;choosingEnd=true;}else{end.value=b.dataset.date;if(end.value<start.value)[start.value,end.value]=[end.value,start.value];choosingEnd=false;}clearQuote();renderCalendar();});
on(select,'change',async()=>{clearQuote();await refreshCalendar();});
for(const input of [start,end]) on(input,'change',()=>{clearQuote();renderCalendar();});
document.addEventListener('selectrental',e=>rentalsReady.then(async()=>{select.value=e.detail;clearQuote();await refreshCalendar();}).catch(handleError));
on('#quote-form','submit',async e=>{
  e.preventDefault();if(!account){document.querySelector('#auth-dialog').showModal();return;}
  try {quote=await api('/rental-quotes',{method:'POST',body:Object.fromEntries(new FormData(e.target))});}
  catch(error){if(error.status===409)await refreshCalendar();throw error;}
  document.querySelector('#quote-result').innerHTML=`<p class="eyebrow">YOUR RENTAL QUOTE · ${quote.days} DAYS</p><div class="result-price">${amd(quote.total_price_amd)}</div><p class="muted">Average ${amd(quote.effective_daily_rate_amd)} / day · Base ${amd(quote.base_daily_rate_amd)} / day</p><div class="factor-list"><span>Demand adjustment</span><strong>× ${Number(quote.demand_multiplier).toFixed(3)}</strong><span>Quote valid until</span><strong>${new Date(quote.expires_at).toLocaleTimeString()}</strong></div><div class="table-wrap"><table><thead><tr><th>Date</th><th>Season</th><th>Duration</th><th>AMD</th></tr></thead><tbody>${quote.daily_breakdown.map(d=>`<tr><td>${d.date}</td><td>×${d.season_multiplier}</td><td>×${d.duration_multiplier}</td><td>${amd(d.daily_price_amd)}</td></tr>`).join('')}</tbody></table></div><button id="confirm-booking" class="button">Confirm reservation ↗</button><p class="muted">Instant confirmation. No payment. A quote does not hold dates. Statistics: ${esc(quote.snapshot_status)}.</p>`;
  on('#confirm-booking','click',async e=>{if(!quote)return;e.target.disabled=true;try{const booking=await api('/bookings',{method:'POST',body:{quote_id:quote.id}});notify(`Reservation confirmed: ${booking.start_date} to ${booking.end_date}.`);clearQuote();await Promise.all([refreshCalendar(),loadBookings()]);}catch(error){if(error.status===409){clearQuote();await refreshCalendar();}else e.target.disabled=false;throw error;}});
});
async function loadBookings(){
  const host=document.querySelector('#my-bookings');if(!account){host.innerHTML='<p class="muted">Sign in to see your reservations.</p>';return;}
  const result=await api('/me/bookings?limit=100');host.innerHTML=result.items.length?result.items.map(b=>`<div class="booking-row"><div><strong>${b.start_date} → ${b.end_date}</strong><p class="muted">${b.days} days · ${amd(b.total_price_amd)} · ${esc(b.phase)} · ${esc(b.id.slice(0,8))}</p></div>${b.status==='confirmed'&&b.start_date>today?`<button class="button secondary small" data-cancel="${b.id}">Cancel reservation</button>`:''}</div>`).join(''):'<p class="empty">Your next journey starts here. No reservations yet.</p>';
}
on('#my-bookings','click',async e=>{const button=e.target.closest('[data-cancel]');if(!button)return;await api(`/bookings/${button.dataset.cancel}/cancel`,{method:'POST',body:{reason:'Cancelled from demo calendar'}});notify('Reservation cancelled. Dates are available again.');clearQuote();await Promise.all([loadBookings(),refreshCalendar()]);});
on('#refresh-bookings','click',loadBookings);
document.addEventListener('sessionchange',()=>{clearQuote();loadBookings().catch(handleError);});

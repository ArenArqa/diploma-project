const host = document.querySelector('#photo-credits');
fetch('/uploads/cars/credits.json').then(response => {
  if (!response.ok) throw new Error('Unable to load local image credits.');
  return response.json();
}).then(credits => {
  for (const [filename, credit] of Object.entries(credits)) {
    const article = document.createElement('article'); article.className = 'listing-card';
    const image = document.createElement('img'); image.src = `/uploads/cars/${filename}`;
    image.alt = `${credit.brand_slug} ${credit.model_slug}`; image.loading = 'lazy';
    image.style.cssText = 'display:block;width:100%;height:200px;object-fit:cover';
    const body = document.createElement('div'); body.className = 'listing-body';
    const title = document.createElement('h2'); title.className = 'listing-title';
    title.textContent = `${credit.brand_slug} · ${credit.model_slug}`;
    const author = document.createElement('p'); author.textContent = `Photo: ${credit.author}`;
    const source = document.createElement('a'); source.href = credit.source;
    source.textContent = 'Original photograph on Wikimedia Commons ↗'; source.className = 'text-button';
    const license = document.createElement('a'); license.href = credit.license_url;
    license.textContent = credit.license; license.className = 'text-button';
    const changes = document.createElement('p'); changes.className = 'muted'; changes.textContent = credit.changes;
    body.append(title, author, source, license, changes); article.append(image, body); host.append(article);
  }
}).catch(error => document.querySelector('#credits-error').textContent = error.message);

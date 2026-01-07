let lastResults = [];

document.getElementById('scrapeForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const form = e.target;
    const startBtn = document.getElementById('startBtn');
    const btnText = startBtn.querySelector('.btn-text');
    const btnLoader = startBtn.querySelector('.loader');
    const resultsPanel = document.getElementById('resultsPanel');
    const resultsContainer = document.getElementById('resultsContainer');
    const downloadBtn = document.getElementById('downloadBtn');
    const resultCount = document.getElementById('resultCount');
    const loadingOverlay = document.getElementById('loadingOverlay');

    // UI State: Loading
    startBtn.disabled = true;
    btnText.textContent = 'Processing...';
    // Clear previous results smoothly
    resultsContainer.innerHTML = '';
    resultsPanel.classList.remove('hidden');
    loadingOverlay.classList.remove('hidden');
    downloadBtn.classList.add('hidden');
    resultCount.textContent = 'Scanning...';
    
    // Scroll to results
    resultsPanel.scrollIntoView({ behavior: 'smooth', block: 'start' });

    // Collect data
    const formData = new FormData(form);
    const data = {};
    for (let [key, value] of formData.entries()) {
        if (!key.startsWith('scrape_')) {
            data[key] = value;
        }
    }
    
    // Checkboxes
    const checkboxes = form.querySelectorAll('input[type="checkbox"]');
    checkboxes.forEach(cb => {
        data[cb.name] = cb.checked;
    });

    try {
        const response = await fetch('/scrape', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });

        const result = await response.json();

        if (!response.ok) {
            throw new Error(result.error || 'Scraping failed');
        }

        // Success
        loadingOverlay.classList.add('hidden');
        lastResults = Array.isArray(result.data) ? result.data : [];
        setupResultsToolbar();
        renderResults(applyFiltersSort(lastResults));
        resultCount.textContent = `${result.count} Pages Extracted`;
        
        downloadBtn.onclick = () => downloadJSON(lastResults);
        downloadBtn.classList.remove('hidden');

    } catch (error) {
        loadingOverlay.classList.add('hidden');
        resultsContainer.innerHTML = `
            <div class="result-card" style="border-left: 4px solid #ef4444;">
                <h3 style="color: #ef4444;">Extraction Error</h3>
                <p>${error.message}</p>
            </div>
        `;
        resultCount.textContent = 'Failed';
    } finally {
        startBtn.disabled = false;
        btnText.textContent = 'Start Extraction';
    }
});

function renderResults(data) {
    const container = document.getElementById('resultsContainer');
    
    if (!data || data.length === 0) {
        container.innerHTML = `
            <div class="result-card" style="text-align: center; padding: 3rem;">
                <div style="font-size: 3rem; margin-bottom: 1rem;">🔍</div>
                <h3>No Results Found</h3>
                <p style="color: #64748b;">We couldn't extract any data matching your criteria.</p>
                <div style="margin-top: 1rem; font-size: 0.9rem; color: #94a3b8;">
                    Try adjusting your filters, increasing depth, or checking the URL.
                </div>
            </div>
        `;
        // Animate single card
        setTimeout(() => container.querySelector('.result-card').classList.add('visible'), 50);
        return;
    }

    container.innerHTML = '';
    data.forEach((page, index) => {
        const card = document.createElement('div');
        card.className = 'result-card';
        // Staggered animation delay
        card.style.transitionDelay = `${index * 100}ms`;
        
        const detailsId = `details-${index}`;
        const headingsCount = (page.headings || []).length;
        const paragraphsCount = (page.paragraphs || []).length;
        const linksCount = (page.links || []).length;
        const imagesCount = (page.images || []).length;
        const tablesCount = (page.tables || []).length;

        // Smart Analysis Logic
        let insights = [];
        if (tablesCount > 0) insights.push({ icon: '📊', text: 'Data-Rich' });
        if (imagesCount > 5) insights.push({ icon: '🖼️', text: 'Visual Gallery' });
        if (linksCount > 20) insights.push({ icon: '🔗', text: 'Resource Hub' });
        if (paragraphsCount > 10) insights.push({ icon: '📝', text: 'Long-Form Content' });
        if (headingsCount > 10) insights.push({ icon: '📑', text: 'Well-Structured' });
        
        const insightsHtml = insights.length > 0 ? 
            `<div style="margin-bottom: 0.75rem;">${insights.map(i => `<span class="badge" style="display:inline-block; margin-right:0.5rem; padding: 0.25rem 0.6rem; background: #e0e7ff; color: #4338ca; border-radius: 12px; font-size: 0.75rem; font-weight: 600;">${i.icon} ${i.text}</span>`).join('')}</div>` 
            : '';

        let contentHtml = `
            <h3>${escapeHtml(page.title || 'Untitled Page')}</h3>
            <a href="${page.url}" target="_blank" class="result-url">${page.url}</a>
            ${insightsHtml}
            <div class="summary-row">
                <span class="chip">🧭 Headings: ${headingsCount}</span>
                <span class="chip">📝 Paragraphs: ${paragraphsCount}</span>
                <span class="chip">🔗 Links: ${linksCount}</span>
                <span class="chip">🖼️ Images: ${imagesCount}</span>
                <button class="toggle-btn" onclick="toggleDetails('${detailsId}', this)">View details</button>
            </div>
            <div id="${detailsId}" style="display:none;">
        `;

        if (page.meta_description) {
            contentHtml += `
                <div class="result-section">
                    <h4>Meta Description</h4>
                    <p>${escapeHtml(page.meta_description)}</p>
                </div>
            `;
        }

        if (page.headings && page.headings.length > 0) {
            const hasMore = page.headings.length > 5;
            const hiddenId = `headings-${index}`;
            
            contentHtml += `
                <div class="result-section">
                    <h4>Structure (${page.headings.length} Headings)</h4>
                    <ul style="list-style-position: inside; font-size: 0.9rem; margin-bottom: 0.5rem;">
                        ${page.headings.slice(0, 5).map(h => `<li>${escapeHtml(h)}</li>`).join('')}
                    </ul>
                    ${hasMore ? `
                        <ul id="${hiddenId}" style="display:none; list-style-position: inside; font-size: 0.9rem;">
                            ${page.headings.slice(5).map(h => `<li>${escapeHtml(h)}</li>`).join('')}
                        </ul>
                        <button onclick="toggleHeadings('${hiddenId}', this)" style="background:none; border:none; color: var(--primary); cursor:pointer; font-size: 0.85rem; padding:0; text-decoration: underline;">
                            + ${page.headings.length - 5} more...
                        </button>
                    ` : ''}
                </div>
            `;
        }
        
        if (page.paragraphs && page.paragraphs.length > 0) {
            // Show up to 3 paragraphs
            const previewText = page.paragraphs.slice(0, 3).map(p => `<p style="margin-bottom: 0.5rem;">${escapeHtml(p)}</p>`).join('');
            contentHtml += `
                <div class="result-section">
                    <h4>Content Preview</h4>
                    <div style="font-size: 0.9rem; color: #475569; max-height: 300px; overflow-y: auto;">
                        ${previewText}
                    </div>
                </div>
            `;
        }

        if (page.tables && page.tables.length > 0) {
             contentHtml += `
                <div class="result-section">
                    <h4>Data Tables (${page.tables.length})</h4>
                    <div style="overflow-x: auto;">
                        <table style="width:100%; border-collapse: collapse; font-size: 0.9rem; margin-top: 0.5rem;">
                            <thead>
                                <tr style="background: #f1f5f9;">
                                    ${(page.tables[0].headers || []).map(h => `<th style="padding: 0.5rem; text-align: left; border: 1px solid #e2e8f0;">${escapeHtml(h)}</th>`).join('')}
                                </tr>
                            </thead>
                            <tbody>
                                ${(page.tables[0].rows || []).slice(0, 3).map(row => `
                                    <tr>
                                        ${row.map(cell => `<td style="padding: 0.5rem; border: 1px solid #e2e8f0;">${escapeHtml(cell)}</td>`).join('')}
                                    </tr>
                                `).join('')}
                            </tbody>
                        </table>
                        ${page.tables[0].rows.length > 3 ? `<p style="font-size: 0.8rem; color: #64748b; margin-top: 0.5rem;">+ ${page.tables[0].rows.length - 3} more rows...</p>` : ''}
                        ${page.tables.length > 1 ? `<p style="font-size: 0.8rem; color: #64748b; margin-top: 0.25rem;">+ ${page.tables.length - 1} other tables found</p>` : ''}
                    </div>
                </div>
            `;
        }
        
        if (page.links && page.links.length > 0) {
             const internal = page.links.filter(l => l.type === 'internal' && l.context === 'content');
             const external = page.links.filter(l => l.type === 'external' && l.context === 'content');
             const resources = page.links.filter(l => ['email', 'phone'].includes(l.type));
             const allLinks = page.links; // For the modal
             
             // Prioritize content links for the summary view
             const previewLinks = [...internal, ...external].slice(0, 6);
             
             contentHtml += `
                <div class="result-section">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <h4>Links Found (${page.links.length})</h4>
                        <button onclick="showAllLinks(${index})" style="font-size:0.85rem; padding: 4px 12px; border:1px solid #e2e8f0; background:#fff; border-radius:4px; cursor:pointer;">View All</button>
                    </div>
                    
                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin-top:0.5rem;">
                        ${previewLinks.length > 0 ? `
                        <div>
                            <h5 style="font-size: 0.8rem; color: #64748b; margin-bottom: 0.5rem;">Top Content Links</h5>
                            <ul style="font-size: 0.85rem; padding-left: 1rem; color: var(--primary);">
                                ${previewLinks.map(l => `<li><a href="${l.href}" target="_blank" style="color:inherit; text-decoration:none;">${escapeHtml(l.text.substring(0, 30))}${l.text.length > 30 ? '...' : ''}</a> <span style="font-size:0.7em; color:#94a3b8; margin-left:4px;">${l.type}</span></li>`).join('')}
                            </ul>
                        </div>
                        ` : ''}
                        
                        ${resources.length > 0 ? `
                        <div>
                            <h5 style="font-size: 0.8rem; color: #64748b; margin-bottom: 0.5rem;">Contact & Resources</h5>
                            <ul style="font-size: 0.85rem; padding-left: 1rem; color: var(--secondary);">
                                ${resources.slice(0, 5).map(l => `<li><a href="${l.href}" target="_blank" style="color:inherit; text-decoration:none;">${escapeHtml(l.text)}</a></li>`).join('')}
                            </ul>
                        </div>
                        ` : ''}
                    </div>
                </div>
            `;
        }

        if (page.images && page.images.length > 0) {
             // Filter out likely icons/logos for the preview (heuristic: check if 'logo' or 'icon' is in src/alt)
             const heroImages = page.images.filter(img => {
                 const lowerSrc = (img.src || '').toLowerCase();
                 const lowerAlt = (img.alt || '').toLowerCase();
                 return !lowerSrc.includes('logo') && !lowerSrc.includes('icon') && !lowerAlt.includes('logo');
             });
             
             // Fallback to all images if filtering removes too many
             const previewImages = (heroImages.length > 0 ? heroImages : page.images).slice(0, 4);

             contentHtml += `
                <div class="result-section">
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom: 0.5rem;">
                        <h4>Visual Gallery (${page.images.length})</h4>
                        <button onclick="showAllImages(${index})" style="font-size:0.85rem; padding: 4px 12px; border:1px solid #e2e8f0; background:#fff; border-radius:4px; cursor:pointer;">View Gallery</button>
                    </div>
                    
                    <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(120px, 1fr)); gap: 0.75rem;">
                        ${previewImages.map(img => `
                            <div class="gallery-thumb" onclick="showAllImages(${index})" style="cursor:pointer; aspect-ratio: 16/9; background: #f1f5f9; border-radius: 6px; overflow: hidden; border: 1px solid #e2e8f0; position: relative; group">
                                <img src="${img.src}" alt="${escapeHtml(img.alt)}" loading="lazy" style="width: 100%; height: 100%; object-fit: cover; transition: transform 0.3s ease;">
                            </div>
                        `).join('')}
                    </div>
                    ${page.images.length > 4 ? `<p style="font-size: 0.8rem; color: #64748b; margin-top: 0.5rem; cursor:pointer;" onclick="showAllImages(${index})">+ ${page.images.length - 4} more images...</p>` : ''}
                </div>
            `;
        }

        contentHtml += `</div>`;
        card.innerHTML = contentHtml;
        container.appendChild(card);
        
        // Trigger animation
        setTimeout(() => card.classList.add('visible'), 50);
    });
}

function setupResultsToolbar() {
    const filterInput = document.getElementById('resultsFilter');
    const sortSelect = document.getElementById('resultsSort');
    const expandBtn = document.getElementById('expandAllBtn');
    const collapseBtn = document.getElementById('collapseAllBtn');
    if (!filterInput || !sortSelect) return;
    filterInput.onkeyup = () => renderResults(applyFiltersSort(lastResults));
    sortSelect.onchange = () => renderResults(applyFiltersSort(lastResults));
    expandBtn.onclick = () => {
        document.querySelectorAll('[id^="details-"]').forEach(el => el.style.display = 'block');
        document.querySelectorAll('.toggle-btn').forEach(b => b.textContent = 'Show less');
    };
    collapseBtn.onclick = () => {
        document.querySelectorAll('[id^="details-"]').forEach(el => el.style.display = 'none');
        document.querySelectorAll('.toggle-btn').forEach(b => b.textContent = 'View details');
    };
}

function applyFiltersSort(data) {
    const filterInput = document.getElementById('resultsFilter');
    const sortSelect = document.getElementById('resultsSort');
    let filtered = data;
    const q = (filterInput?.value || '').trim().toLowerCase();
    if (q) {
        filtered = data.filter(item => {
            const hay = [
                item.title || '',
                item.meta_description || '',
                ...(item.headings || []),
                ...(item.paragraphs || [])
            ].join(' ').toLowerCase();
            return hay.includes(q);
        });
    }
    const sortKey = sortSelect?.value || 'title';
    const getCount = (arr) => Array.isArray(arr) ? arr.length : 0;
    filtered.sort((a, b) => {
        switch (sortKey) {
            case 'headings':
                return getCount(b.headings) - getCount(a.headings);
            case 'paragraphs':
                return getCount(b.paragraphs) - getCount(a.paragraphs);
            case 'url':
                return String(a.url || '').localeCompare(String(b.url || ''));
            case 'title':
            default:
                return String(a.title || '').localeCompare(String(b.title || ''));
        }
    });
    return filtered;
}

// Link Modal Functions
function showAllLinks(index) {
    const page = lastResults[index];
    if (!page || !page.links) return;
    
    // Create Modal UI
    const modalId = 'links-modal';
    let modal = document.getElementById(modalId);
    
    if (!modal) {
        modal = document.createElement('div');
        modal.id = modalId;
        modal.style.cssText = `
            position: fixed; top: 0; left: 0; width: 100%; height: 100%;
            background: rgba(0,0,0,0.5); z-index: 1000;
            display: flex; justify-content: center; align-items: center;
        `;
        document.body.appendChild(modal);
    }
    
    // Categorize for the view
    const links = page.links;
    
    modal.innerHTML = `
        <div style="background: white; width: 90%; max-width: 800px; max-height: 90vh; border-radius: 12px; display: flex; flex-direction: column; overflow: hidden; box-shadow: 0 10px 25px rgba(0,0,0,0.2);">
            <div style="padding: 1.5rem; border-bottom: 1px solid #e2e8f0; display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <h3 style="margin: 0;">Links Explorer</h3>
                    <p style="margin: 0.25rem 0 0; color: #64748b; font-size: 0.9rem;">Found ${links.length} links on ${escapeHtml(page.title)}</p>
                </div>
                <button onclick="document.getElementById('${modalId}').remove()" style="background: none; border: none; font-size: 1.5rem; cursor: pointer;">&times;</button>
            </div>
            
            <div style="padding: 1rem; background: #f8fafc; border-bottom: 1px solid #e2e8f0;">
                <input type="text" id="linkSearch" placeholder="Filter links..." style="width: 100%; padding: 0.5rem; border: 1px solid #cbd5e1; border-radius: 6px;">
            </div>
            
            <div id="linksList" style="flex: 1; overflow-y: auto; padding: 1rem;">
                <!-- Links will be injected here -->
            </div>
        </div>
    `;
    
    renderLinksList(links, 'linksList');
    
    // Setup search
    const searchInput = document.getElementById('linkSearch');
    searchInput.onkeyup = (e) => {
        const term = e.target.value.toLowerCase();
        const filtered = links.filter(l => 
            (l.text || '').toLowerCase().includes(term) || 
            (l.href || '').toLowerCase().includes(term)
        );
        renderLinksList(filtered, 'linksList');
    };
}

function renderLinksList(links, containerId) {
    const container = document.getElementById(containerId);
    if (!container) return;
    
    if (links.length === 0) {
        container.innerHTML = '<p style="text-align:center; color:#64748b; padding: 2rem;">No links found matching filter.</p>';
        return;
    }
    
    // Group by Context -> Type
    const html = links.map(l => `
        <div style="padding: 0.75rem; border-bottom: 1px solid #f1f5f9; display: flex; align-items: start; gap: 0.75rem;">
            <div style="
                background: ${l.type === 'internal' ? '#e0e7ff' : l.type === 'external' ? '#fef3c7' : '#dcfce7'}; 
                color: ${l.type === 'internal' ? '#4338ca' : l.type === 'external' ? '#b45309' : '#166534'};
                padding: 2px 8px; border-radius: 4px; font-size: 0.7rem; font-weight: 600; text-transform: uppercase; white-space: nowrap; margin-top: 2px;">
                ${l.type}
            </div>
            <div style="flex: 1; min-width: 0;">
                <div style="font-weight: 500; margin-bottom: 0.1rem; color: #1e293b; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
                    ${escapeHtml(l.text || 'No Text')}
                </div>
                <div style="font-size: 0.8rem; color: #64748b; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
                    <a href="${l.href}" target="_blank" style="color: inherit; text-decoration: none; border-bottom: 1px dotted #cbd5e1;">${l.href}</a>
                </div>
                <div style="font-size: 0.7rem; color: #94a3b8; margin-top: 0.2rem;">
                    Context: ${l.context || 'unknown'}
                </div>
            </div>
        </div>
    `).join('');
    
    container.innerHTML = html;
}

// Gallery Modal Functions
function showAllImages(index) {
    const page = lastResults[index];
    if (!page || !page.images) return;
    
    // Create Modal UI
    const modalId = 'gallery-modal';
    let modal = document.getElementById(modalId);
    
    if (!modal) {
        modal = document.createElement('div');
        modal.id = modalId;
        modal.style.cssText = `
            position: fixed; top: 0; left: 0; width: 100%; height: 100%;
            background: rgba(0,0,0,0.85); z-index: 2000;
            display: flex; justify-content: center; align-items: center;
        `;
        document.body.appendChild(modal);
    }
    
    modal.innerHTML = `
        <div style="background: white; width: 95%; max-width: 1200px; height: 90vh; border-radius: 12px; display: flex; flex-direction: column; overflow: hidden; box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);">
            <div style="padding: 1.5rem; border-bottom: 1px solid #e2e8f0; display: flex; justify-content: space-between; align-items: center; background: #fff;">
                <div>
                    <h3 style="margin: 0; font-size: 1.25rem;">Visual Gallery</h3>
                    <p style="margin: 0.25rem 0 0; color: #64748b; font-size: 0.9rem;">${page.images.length} images from ${escapeHtml(page.title)}</p>
                </div>
                <button onclick="document.getElementById('${modalId}').remove()" style="background: #f1f5f9; border: none; font-size: 1.5rem; cursor: pointer; width: 40px; height: 40px; border-radius: 50%; display:flex; align-items:center; justify-content:center;">&times;</button>
            </div>
            
            <div id="galleryGrid" style="flex: 1; overflow-y: auto; padding: 1.5rem; background: #f8fafc; display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 1.5rem; align-content: start;">
                ${page.images.map((img, i) => `
                    <div class="gallery-item" onclick="openLightbox('${modalId}', ${i})" style="
                        background: white; 
                        border-radius: 8px; 
                        overflow: hidden; 
                        box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1); 
                        cursor: zoom-in;
                        transition: transform 0.2s;
                        border: 1px solid #e2e8f0;
                        display: flex; flex-direction: column;
                    " onmouseover="this.style.transform='translateY(-2px)'; this.style.boxShadow='0 4px 6px -1px rgba(0, 0, 0, 0.1)'" onmouseout="this.style.transform='none'; this.style.boxShadow='0 1px 3px 0 rgba(0, 0, 0, 0.1)'">
                        <div style="aspect-ratio: 16/9; overflow: hidden; background: #e2e8f0; display: flex; align-items: center; justify-content: center;">
                            <img src="${img.src}" alt="${escapeHtml(img.alt)}" loading="lazy" style="width: 100%; height: 100%; object-fit: contain;">
                        </div>
                        <div style="padding: 0.75rem; font-size: 0.8rem; color: #475569;">
                            <div style="font-weight: 500; margin-bottom: 0.25rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">${escapeHtml(img.alt || 'Untitled Image')}</div>
                            <div style="color: #94a3b8; font-size: 0.75rem;">${img.width || '?'} × ${img.height || '?'} px</div>
                        </div>
                    </div>
                `).join('')}
            </div>
        </div>
        
        <!-- Lightbox Container (Hidden initially) -->
        <div id="lightbox-${modalId}" style="display: none; position: absolute; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.95); z-index: 2010; justify-content: center; align-items: center; flex-direction: column;">
            <img id="lightbox-img-${modalId}" src="" style="max-width: 90%; max-height: 80vh; object-fit: contain; box-shadow: 0 0 20px rgba(0,0,0,0.5);">
            <p id="lightbox-caption-${modalId}" style="color: white; margin-top: 1rem; font-size: 1rem; text-align: center; max-width: 80%;"></p>
            <button onclick="closeLightbox('${modalId}')" style="position: absolute; top: 20px; right: 30px; background: none; border: none; color: white; font-size: 3rem; cursor: pointer;">&times;</button>
        </div>
    `;
    
    // Store images data on the modal element for lightbox navigation (optional enhancement)
    modal.dataset.images = JSON.stringify(page.images);
}

function openLightbox(modalId, index) {
    const modal = document.getElementById(modalId);
    const lightbox = document.getElementById(`lightbox-${modalId}`);
    const imgEl = document.getElementById(`lightbox-img-${modalId}`);
    const captionEl = document.getElementById(`lightbox-caption-${modalId}`);
    
    if (!modal || !lightbox || !imgEl) return;
    
    const images = JSON.parse(modal.dataset.images || '[]');
    const img = images[index];
    if (!img) return;
    
    imgEl.src = img.src;
    captionEl.textContent = img.alt || 'Untitled Image';
    lightbox.style.display = 'flex';
}

function closeLightbox(modalId) {
    const lightbox = document.getElementById(`lightbox-${modalId}`);
    if (lightbox) lightbox.style.display = 'none';
}

function escapeHtml(text) {
    if (!text) return '';
    return text
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

function downloadJSON(data) {
    const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(data, null, 2));
    const downloadAnchorNode = document.createElement('a');
    downloadAnchorNode.setAttribute("href", dataStr);
    downloadAnchorNode.setAttribute("download", "scraped_data_" + new Date().toISOString().slice(0,10) + ".json");
    document.body.appendChild(downloadAnchorNode);
    downloadAnchorNode.click();
    downloadAnchorNode.remove();
}

window.toggleHeadings = function(id, btn) {
    const el = document.getElementById(id);
    if (el.style.display === 'none') {
        el.style.display = 'block';
        btn.textContent = 'Show less';
    } else {
        el.style.display = 'none';
        btn.textContent = `+ ${el.children.length} more...`;
    }
};

window.toggleDetails = function(id, btn) {
    const el = document.getElementById(id);
    if (!el) return;
    if (el.style.display === 'none') {
        el.style.display = 'block';
        btn.textContent = 'Show less';
    } else {
        el.style.display = 'none';
        btn.textContent = 'View details';
    }
};

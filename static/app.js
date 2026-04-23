document.addEventListener('DOMContentLoaded', () => {

    // --- State ---
    let productContext = "";
    let selectedImageUrl = "";
    let currentProposalId = null;
    let currentData = null;

    // --- Elements ---
    const searchBtn = document.getElementById('search-btn');
    const generateBtn = document.getElementById('generate-btn');
    const loadingOverlay = document.getElementById('loading-overlay');
    const loadingText = document.getElementById('loading-text');
    const imageSelectionArea = document.getElementById('image-selection-area');
    const imageGrid = document.getElementById('image-grid');
    const proposalPreview = document.getElementById('proposal-preview');
    const saveBtn = document.getElementById('save-btn');
    const listBtn = document.getElementById('list-btn');
    const drawer = document.getElementById('proposals-drawer');
    const drawerOverlay = document.getElementById('drawer-overlay');
    const drawerClose = document.getElementById('drawer-close');
    const drawerList = document.getElementById('proposals-drawer-list');
    const toast = document.getElementById('toast');

    const productNameInput = document.getElementById('product_name');
    const priceInput = document.getElementById('price');
    const capacityInput = document.getElementById('capacity');

    // --- Helpers ---
    const showLoading = (msg) => { loadingText.textContent = msg; loadingOverlay.classList.remove('hidden'); };
    const hideLoading = () => loadingOverlay.classList.add('hidden');
    const showToast = (msg) => {
        toast.textContent = msg;
        toast.classList.add('show');
        setTimeout(() => toast.classList.remove('show'), 2000);
    };
    const escapeHtml = (s) => String(s ?? '').replace(/[&<>"']/g, c => (
        { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]
    ));

    // --- 1. Search ---
    searchBtn.addEventListener('click', async () => {
        if (!productNameInput.value) { alert("商品名を入力してください"); return; }
        showLoading("商品情報と画像を検索中...");
        try {
            const [searchRes, imageRes] = await Promise.all([
                fetch('/api/search', {
                    method: 'POST', headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ product_name: productNameInput.value })
                }),
                fetch('/api/images', {
                    method: 'POST', headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ product_name: productNameInput.value, count: 8 })
                })
            ]);
            const searchData = await searchRes.json();
            const imageData = await imageRes.json();
            productContext = searchData.context;

            imageGrid.innerHTML = '';
            selectedImageUrl = '';
            if (imageData.images && imageData.images.length > 0) {
                imageData.images.forEach(url => {
                    const div = document.createElement('div');
                    div.className = 'image-item';
                    div.innerHTML = `<img src="${url}" loading="lazy">`;
                    div.onclick = () => selectImage(div, url);
                    imageGrid.appendChild(div);
                });
                imageSelectionArea.classList.remove('hidden');
                generateBtn.disabled = true;
            } else {
                alert("画像が見つかりませんでした。");
            }
        } catch (e) {
            console.error(e); alert("検索中にエラーが発生しました。");
        } finally { hideLoading(); }
    });

    function selectImage(element, url) {
        document.querySelectorAll('.image-item.selected').forEach(el => el.classList.remove('selected'));
        element.classList.add('selected');
        selectedImageUrl = url;
        generateBtn.disabled = false;
        const mainImage = document.getElementById('main-product-img');
        if (mainImage) mainImage.src = url;
    }

    // --- 2. Generate ---
    generateBtn.addEventListener('click', async () => {
        if (!selectedImageUrl) { alert("画像を選択してください"); return; }
        showLoading("提案書を生成中...");
        try {
            const payload = {
                product_name: productNameInput.value,
                price: priceInput.value,
                capacity: capacityInput.value,
                image_url: selectedImageUrl,
                context: productContext
            };
            const response = await fetch('/api/generate', {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            if (!response.ok) throw new Error("Generation Failed");
            const data = await response.json();
            currentProposalId = null;
            currentData = data;
            renderProposal(data, selectedImageUrl);
            saveBtn.disabled = false;
        } catch (e) {
            console.error(e); alert("生成に失敗しました。");
        } finally { hideLoading(); }
    });

    // --- 3. Render (Apple-style layout) ---
    function renderProposal(data, imageUrl) {
        const benefits = (data.benefits || []).map(b => `
            <div class="benefit-card">
                <div class="benefit-title" contenteditable="true">${escapeHtml(b.title)}</div>
                <div class="benefit-detail" contenteditable="true">${escapeHtml(b.detail)}</div>
            </div>`).join('');

        const specs = (data.product_specs || []).map(s => `<li contenteditable="true">${escapeHtml(s)}</li>`).join('');

        proposalPreview.innerHTML = `
            <header class="doc-header">
                <div class="doc-brand">株式会社よつや</div>
                <div class="doc-contact">
                    <div>TEL 045-593-5547 &nbsp; FAX 045-590-1171</div>
                    <div>yotsuya.center@gmail.com</div>
                </div>
            </header>

            <div class="doc-kicker">Product Proposal</div>

            <div class="hero-section hero-split">
                <div class="product-image" id="drop-zone">
                    <img src="${imageUrl}" alt="${escapeHtml(data.product_name)}" id="main-product-img">
                    <div class="image-overlay">クリックで画像を差し替え・ドラッグ&ドロップも可</div>
                </div>
                <div class="hero-meta">
                    <div class="hero-product-name" contenteditable="true">${escapeHtml(data.product_name)}</div>
                    <dl class="hero-attrs">
                        <div><dt>蔵元</dt><dd contenteditable="true">${escapeHtml(data.brewery || '不明')}</dd></div>
                        <div><dt>産地</dt><dd contenteditable="true">${escapeHtml(data.origin || '不明')}</dd></div>
                        <div><dt>容量</dt><dd contenteditable="true">${escapeHtml(data.capacity)}</dd></div>
                    </dl>
                    <div class="catch-copy" contenteditable="true">${escapeHtml(data.catch_copy)}</div>
                </div>
            </div>

            <div class="info-grid">
                <div>
                    <div class="section-title">Benefits</div>
                    ${benefits}
                </div>
                <div>
                    <div class="section-title">Product</div>
                    <div class="specs-box">
                        <ul class="specs-list">${specs}</ul>
                        <div class="price-target-box">
                            <div class="price-group">
                                <span class="price-label">納品価格</span>
                                <span class="price-val" contenteditable="true">${escapeHtml(data.price)}</span>
                                <span class="tax-label">(税別)</span>
                            </div>
                            <div class="target-val" contenteditable="true">ターゲット: ${escapeHtml(data.target)}</div>
                        </div>
                    </div>
                </div>
            </div>

            <div class="comment-section">
                <div class="comment-text" contenteditable="true">${escapeHtml(data.comment)}</div>
            </div>
        `;
        setupAdvancedFeatures();
    }

    function setupAdvancedFeatures() {
        const dropZone = document.getElementById('drop-zone');
        const mainImg = document.getElementById('main-product-img');
        if (!dropZone || !mainImg) return;

        dropZone.addEventListener('click', () => {
            if (selectedImageUrl) mainImg.src = selectedImageUrl;
        });
        dropZone.addEventListener('dragover', (e) => { e.preventDefault(); dropZone.classList.add('drag-over'); });
        dropZone.addEventListener('dragleave', () => dropZone.classList.remove('drag-over'));
        dropZone.addEventListener('drop', (e) => {
            e.preventDefault(); dropZone.classList.remove('drag-over');
            const file = e.dataTransfer.files[0];
            if (file && file.type.startsWith('image/')) {
                const reader = new FileReader();
                reader.onload = (ev) => { mainImg.src = ev.target.result; };
                reader.readAsDataURL(file);
            } else {
                const url = e.dataTransfer.getData('text/plain');
                if (url && (url.startsWith('http') || url.startsWith('data:image'))) mainImg.src = url;
            }
        });
    }

    // --- 4. Save / List / Load ---
    function collectCurrentProposal() {
        const get = (sel) => { const el = proposalPreview.querySelector(sel); return el ? el.innerText.trim() : ''; };
        const catch_copy = get('.catch-copy');
        const comment = get('.comment-text');
        const product_name = get('.specs-box h3') || productNameInput.value;
        const price = get('.price-val') || priceInput.value;
        const imgEl = document.getElementById('main-product-img');
        const image_url = imgEl ? imgEl.src : '';
        const html_content = proposalPreview.innerHTML;
        return {
            title: product_name,
            product_name,
            price,
            capacity: capacityInput.value,
            catch_copy,
            comment,
            image_url,
            html_content
        };
    }

    saveBtn.addEventListener('click', async () => {
        if (!proposalPreview.querySelector('.catch-copy')) return;
        const payload = collectCurrentProposal();
        try {
            const url = currentProposalId ? `/api/proposals/${currentProposalId}` : '/api/proposals';
            const method = currentProposalId ? 'PUT' : 'POST';
            const res = await fetch(url, {
                method, headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            if (!res.ok) throw new Error(await res.text());
            const saved = await res.json();
            currentProposalId = saved.id;
            showToast('保存しました');
        } catch (e) {
            console.error(e); alert('保存に失敗しました: ' + e.message);
        }
    });

    listBtn.addEventListener('click', async () => {
        try {
            const res = await fetch('/api/proposals');
            const { items } = await res.json();
            drawerList.innerHTML = items.length ? items.map(p => `
                <div class="proposal-row" data-id="${p.id}">
                    ${p.image_url ? `<img class="proposal-row-thumb" src="${escapeHtml(p.image_url)}">` : '<div class="proposal-row-thumb"></div>'}
                    <div class="proposal-row-body">
                        <div class="proposal-row-title">${escapeHtml(p.title || p.product_name)}</div>
                        <div class="proposal-row-meta">${new Date(p.created_at).toLocaleString('ja-JP')}</div>
                    </div>
                    <button class="proposal-row-del" data-del="${p.id}" title="削除">×</button>
                </div>
            `).join('') : '<div style="padding:24px;color:var(--ink-4);font-size:13px;text-align:center;">まだ保存された提案書はありません</div>';
            openDrawer();
        } catch (e) {
            console.error(e); alert('一覧の取得に失敗しました');
        }
    });

    drawerList.addEventListener('click', async (e) => {
        const delId = e.target.getAttribute('data-del');
        if (delId) {
            e.stopPropagation();
            if (!confirm('削除しますか？')) return;
            await fetch(`/api/proposals/${delId}`, { method: 'DELETE' });
            listBtn.click();
            return;
        }
        const row = e.target.closest('.proposal-row');
        if (!row) return;
        const id = row.getAttribute('data-id');
        try {
            const res = await fetch(`/api/proposals/${id}`);
            const p = await res.json();
            if (p.html_content) {
                proposalPreview.innerHTML = p.html_content;
                setupAdvancedFeatures();
            }
            currentProposalId = p.id;
            saveBtn.disabled = false;
            productNameInput.value = p.product_name || '';
            priceInput.value = p.price || '';
            capacityInput.value = p.capacity || '';
            closeDrawer();
            showToast('読み込みました');
        } catch (err) { console.error(err); }
    });

    function openDrawer() { drawer.classList.add('open'); drawerOverlay.classList.add('open'); }
    function closeDrawer() { drawer.classList.remove('open'); drawerOverlay.classList.remove('open'); }
    drawerClose.addEventListener('click', closeDrawer);
    drawerOverlay.addEventListener('click', closeDrawer);

});

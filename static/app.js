document.addEventListener('DOMContentLoaded', () => {

    // --- State ---
    let productContext = "";
    let selectedImageUrl = "";

    // --- Elements ---
    const searchBtn = document.getElementById('search-btn');
    const generateBtn = document.getElementById('generate-btn');
    const loadingOverlay = document.getElementById('loading-overlay');
    const loadingText = document.getElementById('loading-text');
    const imageSelectionArea = document.getElementById('image-selection-area');
    const imageGrid = document.getElementById('image-grid');
    const proposalPreview = document.getElementById('proposal-preview');

    // --- Inputs ---
    const productNameInput = document.getElementById('product_name');
    const priceInput = document.getElementById('price');
    const capacityInput = document.getElementById('capacity');


    // --- Helper Functions ---
    const showLoading = (msg) => {
        loadingText.textContent = msg;
        loadingOverlay.classList.remove('hidden');
    };

    const hideLoading = () => {
        loadingOverlay.classList.add('hidden');
    };

    // --- 1. Search Logic ---
    searchBtn.addEventListener('click', async () => {
        if (!productNameInput.value) {
            alert("商品名を入力してください");
            return;
        }

        showLoading("商品情報と画像を検索中...");

        try {
            // Parallel Requests: Context & Images
            const [searchRes, imageRes] = await Promise.all([
                fetch('/api/search', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ product_name: productNameInput.value })
                }),
                fetch('/api/images', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ product_name: productNameInput.value, count: 8 })
                })
            ]);

            const searchData = await searchRes.json();
            const imageData = await imageRes.json();

            // Store Context
            productContext = searchData.context;

            // Render Images
            imageGrid.innerHTML = '';
            selectedImageUrl = ''; // Reset selection

            if (imageData.images && imageData.images.length > 0) {
                imageData.images.forEach(url => {
                    const div = document.createElement('div');
                    div.className = 'image-item';
                    div.innerHTML = `<img src="${url}" loading="lazy">`;
                    div.onclick = () => selectImage(div, url);
                    imageGrid.appendChild(div);
                });

                // Show Selection Area
                imageSelectionArea.classList.remove('hidden');
                generateBtn.disabled = true; // Disable until image is picked
            } else {
                alert("画像が見つかりませんでした。");
            }

        } catch (error) {
            console.error(error);
            alert("検索中にエラーが発生しました。");
        } finally {
            hideLoading();
        }
    });


    // --- 2. Image Selection Logic ---
    function selectImage(element, url) {
        // Remove previous selection
        document.querySelectorAll('.image-item.selected').forEach(el => el.classList.remove('selected'));

        // Add new selection
        element.classList.add('selected');
        selectedImageUrl = url;

        // Enable Generate Button
        generateBtn.disabled = false;

        // NEW: If proposal is already generated, update the image immediately
        const mainImage = document.querySelector('.product-image img');
        if (mainImage) {
            mainImage.src = url;
        }
    }


    // --- 3. Generation Logic ---
    generateBtn.addEventListener('click', async () => {
        if (!selectedImageUrl) {
            alert("画像を選択してください");
            return;
        }

        showLoading("提案書を生成中... (Geminiが考え中)"); // Fun loading message

        try {
            const payload = {
                product_name: productNameInput.value,
                price: priceInput.value,
                capacity: capacityInput.value,
                image_url: selectedImageUrl,
                context: productContext
            };

            const response = await fetch('/api/generate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            if (!response.ok) throw new Error("Generation Failed");

            const data = await response.json();
            renderProposal(data, selectedImageUrl);

        } catch (error) {
            console.error(error);
            alert("生成に失敗しました。もう一度試してください。");
        } finally {
            hideLoading();
        }
    });

    // --- 4. Rendering Logic (HTML Injection) ---
    function renderProposal(data, imageUrl) {
        // This HTML structure must match the one used in create_proposal_v4.py for consistency
        const html = `
            <div class="company-header">
                <div class="company-name">株式会社よつや</div>
                <div>TEL 045-593-5547</div>
                <div>FAX 045-590-1171</div>
                <div>Mail: yotsuya.center@gmail.com</div>
            </div>

            <h1 class="proposal-title" contenteditable="true">商品提案書</h1>
            
            <div class="hero-section">
                <div class="product-image">
                    <img src="${imageUrl}" alt="${data.product_name}">
                </div>
            </div>

            <div class="catch-copy" contenteditable="true">
                ${data.catch_copy}
            </div>

            <div class="info-grid">
                <div>
                    <div class="section-title">お客様への3つのベネフィット</div>
                    ${data.benefits.map(b => `
                    <div class="benefit-card">
                        <div class="benefit-title" contenteditable="true">${b.title}</div>
                        <div class="benefit-detail" contenteditable="true">${b.detail}</div>
                    </div>
                    `).join('')}
                </div>

                <div>
                    <div class="section-title">商品情報</div>
                    <div class="specs-box">
                        <h3 style="margin-top: 0; font-size: 16px;" contenteditable="true">${data.product_name}</h3>
                        <ul class="specs-list">
                        ${data.product_specs.map(spec => `<li contenteditable="true">${spec}</li>`).join('')}
                        </ul>
                        
                        <div class="price-target-box">
                            <div><span contenteditable="true">${data.capacity}</span>　<span class="price-group"><span class="price-label">納品価格</span> <span class="price-val" contenteditable="true">${data.price}</span><span class="tax-label">(税別)</span></span></div>
                            <div class="target-val" contenteditable="true">ターゲット: ${data.target}</div>
                        </div>
                    </div>
                </div>
            </div>

            <div class="comment-section">
                <div class="comment-text" contenteditable="true">
                    "${data.comment}"
                </div>
            </div>
        `;

        proposalPreview.innerHTML = html;

        // Scroll to preview on mobile
        if (window.innerWidth < 1000) {
            proposalPreview.scrollIntoView({ behavior: 'smooth' });
        }
    }

});

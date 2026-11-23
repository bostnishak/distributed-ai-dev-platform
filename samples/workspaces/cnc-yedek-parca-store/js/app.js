(() => {
  let activeCategory = "Tümü";
  const grid = document.getElementById("productGrid");
  const filters = document.getElementById("categoryFilters");
  const search = document.getElementById("searchInput");
  const drawer = document.getElementById("cartDrawer");
  const toast = document.getElementById("toast");

  function showToast(msg) {
    toast.textContent = msg;
    toast.hidden = false;
    setTimeout(() => { toast.hidden = true; }, 2200);
  }

  function renderFilters() {
    const cats = ["Tümü", ...new Set(window.PRODUCTS.map((p) => p.category))];
    filters.innerHTML = "";
    cats.forEach((cat) => {
      const btn = document.createElement("button");
      btn.className = "filter-btn" + (cat === activeCategory ? " active" : "");
      btn.textContent = cat;
      btn.onclick = () => { activeCategory = cat; renderFilters(); renderProducts(); };
      filters.appendChild(btn);
    });
  }

  function renderProducts() {
    const q = search.value.trim().toLowerCase();
    const list = window.PRODUCTS.filter((p) =>
      (activeCategory === "Tümü" || p.category === activeCategory) &&
      (!q || p.name.toLowerCase().includes(q) || p.desc.toLowerCase().includes(q))
    );
    grid.innerHTML = "";
    list.forEach((p) => {
      const card = document.createElement("div");
      card.className = "card";
      card.innerHTML = `
        <div class="card-badge">${p.category}</div>
        <div class="card-icon">${p.icon}</div>
        <h3>${p.name}</h3>
        <p>${p.desc}</p>
        <div class="card-foot">
          <span class="price">${p.price.toLocaleString("tr-TR")} ₺</span>
          <button class="btn-primary">Sepete Ekle</button>
        </div>
      `;
      card.querySelector("button").onclick = () => {
        window.CartStore.add(p);
        renderCart();
        showToast(`${p.name} sepete eklendi`);
      };
      grid.appendChild(card);
    });
  }

  function renderCart() {
    const items = window.CartStore.getItems();
    document.getElementById("cartCount").textContent = items.reduce((s, i) => s + i.qty, 0);
    document.getElementById("cartTotal").textContent = `${window.CartStore.total().toLocaleString("tr-TR")} ₺`;
    const box = document.getElementById("cartItems");
    box.innerHTML = items.length ? "" : '<p style="color:#94a3b8;font-size:13px;">Sepetiniz boş.</p>';
    items.forEach((it) => {
      const row = document.createElement("div");
      row.className = "cart-item";
      row.innerHTML = `
        <div><strong>${it.name}</strong><div style="font-size:12px;color:#94a3b8;">${it.price.toLocaleString("tr-TR")} ₺</div></div>
        <div class="qty-ctrl">
          <button class="minus">−</button><span>${it.qty}</span><button class="plus">+</button>
        </div>
      `;
      row.querySelector(".minus").onclick = () => { window.CartStore.updateQty(it.id, -1); renderCart(); };
      row.querySelector(".plus").onclick = () => { window.CartStore.updateQty(it.id, 1); renderCart(); };
      box.appendChild(row);
    });
  }

  document.getElementById("cartToggle").onclick = () => { drawer.hidden = false; };
  document.getElementById("closeCart").onclick = () => { drawer.hidden = true; };
  document.getElementById("applyCoupon").onclick = () => {
    const ok = window.CartStore.applyCoupon(document.getElementById("couponInput").value);
    renderCart();
    showToast(ok ? "CNC10 kuponu uygulandı (%10 indirim)!" : "Geçersiz kupon kodu (CNC10 deneyin)");
  };
  document.getElementById("checkoutBtn").onclick = () => {
    if (!window.CartStore.getItems().length) return showToast("Sepetiniz boş!");
    window.CartStore.clear();
    renderCart();
    drawer.hidden = true;
    showToast("Siparişiniz başarıyla alındı!");
  };
  search.oninput = renderProducts;

  renderFilters();
  renderProducts();
  renderCart();
})();

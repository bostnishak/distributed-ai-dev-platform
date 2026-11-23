window.CartStore = (() => {
  let items = [];
  let discount = 0;

  function add(product) {
    const existing = items.find((i) => i.id === product.id);
    if (existing) existing.qty += 1;
    else items.push({ ...product, qty: 1 });
  }
  function updateQty(id, delta) {
    const it = items.find((i) => i.id === id);
    if (!it) return;
    it.qty += delta;
    if (it.qty <= 0) items = items.filter((i) => i.id !== id);
  }
  function applyCoupon(code) {
    if (code.trim().toUpperCase() === "CNC10") {
      discount = 0.10;
      return true;
    }
    return false;
  }
  function clear() { items = []; discount = 0; }
  function total() {
    const sub = items.reduce((s, i) => s + i.price * i.qty, 0);
    return Math.round(sub * (1 - discount));
  }
  return { getItems: () => items, add, updateQty, applyCoupon, clear, total };
})();

async function loadProducts() {
  const q = document.getElementById("q").value || "";
  const limit = document.getElementById("limit").value || "20";
  const res = await fetch(`/api/products?q=${encodeURIComponent(q)}&limit=${encodeURIComponent(limit)}`);
  const data = await res.json();

  const div = document.getElementById("products");
  if (!data.items || data.items.length === 0) {
    div.innerHTML = "<p><small>No products found.</small></p>";
    return;
  }

  const rows = data.items.map(p => `
    <tr>
      <td>${p.id}</td>
      <td>${p.sku}</td>
      <td>${p.name}</td>
      <td>${(p.price_cents/100.0).toFixed(2)}</td>
    </tr>
  `).join("");

  div.innerHTML = `
    <table>
      <thead><tr><th>ID</th><th>SKU</th><th>Name</th><th>Price</th></tr></thead>
      <tbody>${rows}</tbody>
    </table>
  `;
}

document.getElementById("searchForm").addEventListener("submit", (e) => {
  e.preventDefault();
  loadProducts();
});

loadProducts();

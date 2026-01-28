function setText(id, text) {
  const el = document.getElementById(id);
  if (el) el.textContent = text;
}

async function loadProducts() {
  const div = document.getElementById("products");
  if (!div) return;

  const qEl = document.getElementById("q");
  const limitEl = document.getElementById("limit");

  const q = (qEl && typeof qEl.value === "string") ? qEl.value : "";
  const limit = (limitEl && limitEl.value) ? limitEl.value : "20";

  div.innerHTML = "<p><small>Loading products…</small></p>";

  let res;
  try {
    res = await fetch(`/api/products?q=${encodeURIComponent(q)}&limit=${encodeURIComponent(limit)}`, {
      headers: { "Accept": "application/json" },
      cache: "no-store",
    });
  } catch (e) {
    div.innerHTML = `<p><small>Failed to fetch /api/products: ${String(e)}</small></p>`;
    return;
  }

  if (!res.ok) {
    div.innerHTML = `<p><small>/api/products returned ${res.status}</small></p>`;
    return;
  }

  const data = await res.json();

  if (!data.items || data.items.length === 0) {
    div.innerHTML = "<p><small>No products found.</small></p>";
    return;
  }

  const rows = data.items.map(p => `
    <tr>
      <td>${p.id}</td>
      <td>${p.sku}</td>
      <td>${p.name}</td>
      <td>${(p.price_cents / 100).toFixed(2)}</td>
    </tr>
  `).join("");

  div.innerHTML = `
    <table>
      <thead><tr><th>ID</th><th>SKU</th><th>Name</th><th>Price</th></tr></thead>
      <tbody>${rows}</tbody>
    </table>
  `;
}

async function loadBadMode() {
  try {
    const res = await fetch("/api/bad/mode", { cache: "no-store" });
    const data = await res.json();
    setText("bad_query_mode", data.bad_query_mode || "unknown");
  } catch {
    setText("bad_query_mode", "unknown");
  }
}

function wireUp() {
  const form = document.getElementById("searchForm");
  if (form) {
    form.addEventListener("submit", (e) => {
      e.preventDefault();
      loadProducts();
    });
  }
  loadBadMode();
  loadProducts();
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", wireUp);
} else {
  wireUp();
}

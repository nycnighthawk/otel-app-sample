package com.example.shop;

import static spark.Spark.*;

import java.sql.*;
import java.util.*;

import com.google.gson.Gson;

public class App {
  static final Gson gson = new Gson();

  static String env(String k, String d) {
    String v = System.getenv(k);
    return (v == null || v.isBlank()) ? d : v;
  }

  static Connection conn() throws SQLException {
    // Example: postgresql://shop:shop@<linux-host>:5432/shop
    String url = env("DATABASE_URL", "postgresql://shop:shop@localhost:5432/shop");
    // Convert URI-like to JDBC URL
    // jdbc:postgresql://host:port/db?user=...&password=...
    if (url.startsWith("postgresql://")) {
      String noScheme = url.substring("postgresql://".length());
      // user:pass@host:port/db
      String[] parts = noScheme.split("@", 2);
      String up = parts[0];
      String hpdb = parts[1];
      String[] upParts = up.split(":", 2);
      String user = upParts[0];
      String pass = upParts.length > 1 ? upParts[1] : "";
      return DriverManager.getConnection("jdbc:postgresql://" + hpdb, user, pass);
    }
    if (url.startsWith("jdbc:")) return DriverManager.getConnection(url);
    return DriverManager.getConnection("jdbc:" + url);
  }

  static String badMode() {
    return env("BAD_QUERY_MODE", "like").toLowerCase(Locale.ROOT).trim();
  }

  public static void main(String[] args) {
    port(Integer.parseInt(env("PORT", "8081"))); // Java app defaults to 8081 to avoid clashing with Python
    threadPool(50);

    get("/api/health", (req, res) -> {
      res.type("application/json");
      return "{\"ok\":true}";
    });

    get("/api/products", (req, res) -> {
      String q = Optional.ofNullable(req.queryParams("q")).orElse("");
      int limitN = 20;
      try { limitN = Integer.parseInt(Optional.ofNullable(req.queryParams("limit")).orElse("20")); } catch (Exception ignored) {}
      limitN = Math.max(1, Math.min(limitN, 100));

      String sql = """
        SELECT id, sku, name, price_cents
        FROM products
        WHERE (? = '' OR name ILIKE ('%' || ? || '%'))
        ORDER BY id DESC
        LIMIT ?
      """;

      List<Map<String,Object>> items = new ArrayList<>();
      try (Connection c = conn(); PreparedStatement ps = c.prepareStatement(sql)) {
        ps.setString(1, q);
        ps.setString(2, q);
        ps.setInt(3, limitN);
        try (ResultSet rs = ps.executeQuery()) {
          while (rs.next()) {
            Map<String,Object> m = new LinkedHashMap<>();
            m.put("id", rs.getLong("id"));
            m.put("sku", rs.getString("sku"));
            m.put("name", rs.getString("name"));
            m.put("price_cents", rs.getInt("price_cents"));
            items.add(m);
          }
        }
      }

      res.type("application/json");
      Map<String,Object> out = new LinkedHashMap<>();
      out.put("items", items);
      out.put("q", q);
      out.put("limit", limitN);
      return gson.toJson(out);
    });

    post("/api/order", (req, res) -> {
      String email = Optional.ofNullable(req.queryParams("customer_email")).orElse("");
      String pidS = Optional.ofNullable(req.queryParams("product_id")).orElse("0");
      String qtyS = Optional.ofNullable(req.queryParams("qty")).orElse("1");

      long pid = 0;
      int qty = 1;
      try { pid = Long.parseLong(pidS); } catch (Exception ignored) {}
      try { qty = Integer.parseInt(qtyS); } catch (Exception ignored) {}
      qty = Math.max(1, Math.min(qty, 50));

      if (email.isBlank() || pid <= 0) {
        res.status(400);
        res.type("application/json");
        return "{\"error\":\"customer_email and product_id required\"}";
      }

      long orderId;
      try (Connection c = conn()) {
        c.setAutoCommit(false);
        try (PreparedStatement insO = c.prepareStatement("INSERT INTO orders (customer_email) VALUES (?) RETURNING id")) {
          insO.setString(1, email);
          try (ResultSet rs = insO.executeQuery()) {
            rs.next();
            orderId = rs.getLong(1);
          }
        }
        try (PreparedStatement insI = c.prepareStatement("INSERT INTO order_items (order_id, product_id, qty) VALUES (?,?,?)")) {
          insI.setLong(1, orderId);
          insI.setLong(2, pid);
          insI.setInt(3, qty);
          insI.executeUpdate();
        }
        c.commit();
      }

      res.type("application/json");
      return "{\"ok\":true,\"order_id\":" + orderId + "}";
    });

    get("/api/orders", (req, res) -> {
      int limitN = 50;
      try { limitN = Integer.parseInt(Optional.ofNullable(req.queryParams("limit")).orElse("50")); } catch (Exception ignored) {}
      limitN = Math.max(1, Math.min(limitN, 200));

      String sql = """
        SELECT
          o.id,
          o.created_at,
          o.customer_email,
          COALESCE(SUM(oi.qty * p.price_cents), 0) AS total_cents,
          COALESCE(SUM(oi.qty), 0) AS total_items
        FROM orders o
        LEFT JOIN order_items oi ON oi.order_id = o.id
        LEFT JOIN products p ON p.id = oi.product_id
        GROUP BY o.id
        ORDER BY o.id DESC
        LIMIT ?
      """;

      List<Map<String,Object>> items = new ArrayList<>();
      try (Connection c = conn(); PreparedStatement ps = c.prepareStatement(sql)) {
        ps.setInt(1, limitN);
        try (ResultSet rs = ps.executeQuery()) {
          while (rs.next()) {
            Map<String,Object> m = new LinkedHashMap<>();
            m.put("id", rs.getLong("id"));
            m.put("created_at", rs.getString("created_at"));
            m.put("customer_email", rs.getString("customer_email"));
            m.put("total_cents", rs.getLong("total_cents"));
            m.put("total_items", rs.getLong("total_items"));
            items.add(m);
          }
        }
      }

      res.type("application/json");
      Map<String,Object> out = new LinkedHashMap<>();
      out.put("items", items);
      return gson.toJson(out);
    });

    get("/api/bad", (req, res) -> {
      String mode = badMode();

      List<Map<String,Object>> rows = new ArrayList<>();

      try (Connection c = conn()) {
        if (mode.equals("like")) {
          try (PreparedStatement ps = c.prepareStatement("""
              SELECT id, sku, name, price_cents
              FROM products
              WHERE description ILIKE '%lorem%'
              ORDER BY id DESC
              LIMIT 50
            """)) {
            try (ResultSet rs = ps.executeQuery()) {
              while (rs.next()) rows.add(Map.of("id", rs.getLong("id")));
            }
          }
        } else if (mode.equals("random_sort")) {
          try (PreparedStatement ps = c.prepareStatement("""
              SELECT id, sku, name, price_cents
              FROM products
              ORDER BY random()
              LIMIT 50
            """)) {
            try (ResultSet rs = ps.executeQuery()) {
              while (rs.next()) rows.add(Map.of("id", rs.getLong("id")));
            }
          }
        } else if (mode.equals("join_bomb")) {
          try (PreparedStatement ps = c.prepareStatement("""
              SELECT p1.id AS a, p2.id AS b, p1.category
              FROM products p1
              JOIN products p2 ON p1.category = p2.category
              WHERE p1.category IN ('alpha','beta','gamma','delta')
              ORDER BY p1.id DESC
              LIMIT 200
            """)) {
            try (ResultSet rs = ps.executeQuery()) {
              while (rs.next()) rows.add(Map.of("a", rs.getLong("a")));
            }
          }
        } else {
          try (PreparedStatement ps = c.prepareStatement("""
              SELECT id, sku, name, price_cents
              FROM products
              WHERE description ILIKE '%lorem%'
              ORDER BY id DESC
              LIMIT 50
            """)) {
            try (ResultSet rs = ps.executeQuery()) {
              while (rs.next()) rows.add(Map.of("id", rs.getLong("id")));
            }
          }
        }
      }

      res.type("application/json");
      return gson.toJson(Map.of("mode", mode, "rows", rows.size()));
    });

    // Minimal landing to avoid needing GUI
    get("/", (req, res) -> {
      res.type("text/plain");
      return "shop-java up. endpoints: /api/health /api/products /api/order /api/orders /api/bad\n";
    });
  }
}

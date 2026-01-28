package com.example.shop;

import static spark.Spark.*;

import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.sql.*;
import java.util.*;
import java.util.concurrent.atomic.AtomicReference;

import com.google.gson.Gson;

public class App {
  static final Gson gson = new Gson();

  static String env(String k, String d) {
    String v = System.getenv(k);
    return (v == null || v.isBlank()) ? d : v;
  }

  static int envInt(String k, String d) {
    try {
      return Integer.parseInt(env(k, d).trim());
    } catch (Exception e) {
      return Integer.parseInt(d);
    }
  }

  static Connection conn() throws SQLException {
    String url = env("DATABASE_URL", "postgresql://shop:shop@localhost:5432/shop");
    if (url.startsWith("postgresql://")) {
      String noScheme = url.substring("postgresql://".length());
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

  static String normalizeMode(String mode) {
    return (mode == null ? "" : mode).trim().toLowerCase(Locale.ROOT);
  }

  static String slurpResource(String path) {
    try (InputStream is = App.class.getResourceAsStream(path)) {
      if (is == null) return null;
      return new String(is.readAllBytes(), StandardCharsets.UTF_8);
    } catch (Exception e) {
      return null;
    }
  }

  public static void main(String[] args) {
    int p = Integer.parseInt(env("PORT", "8081"));
    port(p);
    threadPool(50);

    // Serve SPA files from: src/main/resources/public/*
    staticFiles.location("/public");

    String defaultBadMode = normalizeMode(env("BAD_QUERY_MODE", "like"));
    AtomicReference<String> runtimeBadMode = new AtomicReference<>(defaultBadMode);

    get("/api/health", (req, res) -> {
      res.type("application/json");
      return gson.toJson(Map.of("ok", true));
    });

    get("/api/products", (req, res) -> {
      String q = Optional.ofNullable(req.queryParams("q")).orElse("").trim();
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
      String email = Optional.ofNullable(req.queryParams("customer_email")).orElse("").trim();
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
        return gson.toJson(Map.of("error", "customer_email and product_id required"));
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

      String accept = Optional.ofNullable(req.headers("Accept")).orElse("");
      if (accept.contains("text/html")) {
        res.status(303);
        res.header("Location", "/");
        return "";
      }

      res.type("application/json");
      return gson.toJson(Map.of("ok", true, "order_id", orderId));
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
      return gson.toJson(Map.of("items", items));
    });

    get("/api/bad/mode", (req, res) -> {
      res.type("application/json");
      return gson.toJson(Map.of(
        "bad_query_mode", runtimeBadMode.get(),
        "default", defaultBadMode,
        "allowed", List.of("like", "random_sort", "join_bomb")
      ));
    });

    post("/api/bad/mode", (req, res) -> {
      String mode = normalizeMode(req.queryParams("mode"));
      Set<String> allowed = Set.of("like", "random_sort", "join_bomb");
      if (!allowed.contains(mode)) {
        res.status(400);
        res.type("application/json");
        List<String> sorted = new ArrayList<>(allowed);
        Collections.sort(sorted);
        return gson.toJson(Map.of("error", "invalid mode", "allowed", sorted));
      }
      runtimeBadMode.set(mode);
      res.type("application/json");
      return gson.toJson(Map.of("ok", true, "bad_query_mode", mode));
    });

    get("/api/bad", (req, res) -> {
      String requested = normalizeMode(req.queryParams("mode"));
      String effectiveMode = !requested.isBlank() ? requested : runtimeBadMode.get();

      int LIKE_MIN_COUNT = envInt("BAD_LIKE_MIN_COUNT", "1");
      String LIKE_PATTERN = env("BAD_LIKE_PATTERN", "%lorem%");

      int RANDOM_SORT_POOL = envInt("BAD_RANDOM_POOL", "500000");
      int RANDOM_SORT_KEY_BYTES = envInt("BAD_RANDOM_KEY_BYTES", "256");

      int JOIN_TOP_CATS = envInt("BAD_JOIN_TOP_CATS", "4");
      int JOIN_MAX_ROWS_PER_CAT = envInt("BAD_JOIN_MAX_PER_CAT", "12000");
      int JOIN_FANOUT = envInt("BAD_JOIN_FANOUT", "80");

      List<Map<String,Object>> rows = new ArrayList<>();

      try (Connection c = conn()) {
        if (effectiveMode.equals("like")) {
          String sql = """
            SELECT category, COUNT(*) AS matches
            FROM products
            WHERE description ILIKE ?
            GROUP BY category
            HAVING COUNT(*) >= ?
            ORDER BY matches DESC
          """;
          try (PreparedStatement ps = c.prepareStatement(sql)) {
            ps.setString(1, LIKE_PATTERN);
            ps.setInt(2, LIKE_MIN_COUNT);
            try (ResultSet rs = ps.executeQuery()) {
              while (rs.next()) {
                rows.add(Map.of(
                  "category", rs.getString("category"),
                  "matches", rs.getLong("matches")
                ));
              }
            }
          }
        } else if (effectiveMode.equals("random_sort")) {
          int repeatN = Math.max(1, RANDOM_SORT_KEY_BYTES / 32);
          String sql = """
            WITH pool AS (
              SELECT id, sku, category, description
              FROM products
              LIMIT ?
            ),
            keyed AS (
              SELECT
                id,
                sku,
                category,
                repeat(md5(description), ?) AS sort_key
              FROM pool
            )
            SELECT id, sku, category
            FROM keyed
            ORDER BY sort_key
            LIMIT 50
          """;
          try (PreparedStatement ps = c.prepareStatement(sql)) {
            ps.setInt(1, RANDOM_SORT_POOL);
            ps.setInt(2, repeatN);
            try (ResultSet rs = ps.executeQuery()) {
              while (rs.next()) {
                rows.add(Map.of(
                  "id", rs.getLong("id"),
                  "sku", rs.getString("sku"),
                  "category", rs.getString("category")
                ));
              }
            }
          }
        } else if (effectiveMode.equals("join_bomb")) {
          String sql = """
            WITH topcats AS (
              SELECT category
              FROM products
              GROUP BY category
              ORDER BY COUNT(*) DESC
              LIMIT ?
            ),
            ranked AS (
              SELECT
                id,
                category,
                row_number() OVER (PARTITION BY category ORDER BY id) AS rn
              FROM products
              WHERE category IN (SELECT category FROM topcats)
            ),
            capped AS (
              SELECT * FROM ranked WHERE rn <= ?
            ),
            pairs AS (
              SELECT
                p1.category AS category,
                p1.id AS left_id,
                p2.id AS right_id
              FROM capped p1
              JOIN capped p2
                ON p1.category = p2.category
               AND p2.rn BETWEEN p1.rn AND (p1.rn + ?)
            )
            SELECT
              category,
              COUNT(*) AS pair_count,
              MIN(left_id) AS min_left_id,
              MAX(right_id) AS max_right_id
            FROM pairs
            GROUP BY category
            ORDER BY pair_count DESC
          """;
          try (PreparedStatement ps = c.prepareStatement(sql)) {
            ps.setInt(1, JOIN_TOP_CATS);
            ps.setInt(2, JOIN_MAX_ROWS_PER_CAT);
            ps.setInt(3, JOIN_FANOUT);
            try (ResultSet rs = ps.executeQuery()) {
              while (rs.next()) {
                rows.add(Map.of(
                  "category", rs.getString("category"),
                  "pair_count", rs.getLong("pair_count"),
                  "min_left_id", rs.getLong("min_left_id"),
                  "max_right_id", rs.getLong("max_right_id")
                ));
              }
            }
          }
        } else {
          String sql = """
            SELECT category, COUNT(*) AS matches
            FROM products
            WHERE description ILIKE ?
            GROUP BY category
            ORDER BY matches DESC
          """;
          try (PreparedStatement ps = c.prepareStatement(sql)) {
            ps.setString(1, LIKE_PATTERN);
            try (ResultSet rs = ps.executeQuery()) {
              while (rs.next()) {
                rows.add(Map.of(
                  "category", rs.getString("category"),
                  "matches", rs.getLong("matches")
                ));
              }
            }
          }
        }
      }

      List<Map<String,Object>> sample = rows.size() <= 10 ? rows : rows.subList(0, 10);

      res.type("application/json");
      return gson.toJson(Map.of(
        "mode", effectiveMode,
        "rows", rows.size(),
        "sample", sample
      ));
    });

    // Serve the SPA entrypoint on "/"
    get("/", (req, res) -> {
      String html = slurpResource("/public/index.html");
      if (html == null) {
        res.type("text/plain");
        res.status(500);
        return "index.html missing";
      }
      res.type("text/html; charset=utf-8");
      return html;
    });

    // SPA fallback: send index.html for non-API 404s
    notFound((req, res) -> {
      if (req.pathInfo() != null && req.pathInfo().startsWith("/api/")) {
        res.type("application/json");
        res.status(404);
        return gson.toJson(Map.of("error", "not_found"));
      }
      String html = slurpResource("/public/index.html");
      if (html == null) {
        res.type("text/plain");
        res.status(404);
        return "index.html missing";
      }
      res.type("text/html; charset=utf-8");
      res.status(200);
      return html;
    });
  }
}

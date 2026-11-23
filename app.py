import os
import sqlite3
import uuid
import requests
from flask import Flask, jsonify, render_template_string, request

app = Flask(__name__)

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
MP_ACCESS_TOKEN = os.environ.get("MP_ACCESS_TOKEN", "")
WHATSAPP_NUMBER = os.environ.get("WHATSAPP_NUMBER", "5585999999999")
DB_PATH = "mutacao_store.db"


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT NOT NULL,
            price_basic REAL NOT NULL,
            price_pro REAL NOT NULL,
            delivery_info TEXT NOT NULL
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            payment_id TEXT PRIMARY KEY,
            product_id INTEGER NOT NULL,
            tier TEXT NOT NULL,
            buyer_email TEXT NOT NULL,
            amount REAL NOT NULL,
            status TEXT NOT NULL,
            notified INTEGER DEFAULT 0
        )
    """)
    count = cur.execute("SELECT COUNT(*) AS c FROM products").fetchone()["c"]
    if count == 0:
        cur.execute("""
            INSERT INTO products (name, description, price_basic, price_pro, delivery_info)
            VALUES (?, ?, ?, ?, ?)
        """, (
            "Acesso VIP Mutação",
            "Pacote digital com acesso completo e suporte direto.",
            19.90,
            39.90,
            "Login: mutacao_user | Email: acesso@mutacao.com | Senha: Mudar@123"
        ))
    conn.commit()
    conn.close()


def send_telegram(message: str):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        requests.post(
            url,
            json={"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"},
            timeout=10,
        )
    except Exception:
        pass


def fetch_mp_payment_status(payment_id: str) -> str:
    if not MP_ACCESS_TOKEN:
        return "pending"
    url = f"https://api.mercadopago.com/v1/payments/{payment_id}"
    headers = {"Authorization": f"Bearer {MP_ACCESS_TOKEN}"}
    try:
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code == 200:
            return r.json().get("status", "pending")
    except Exception:
        pass
    return "pending"


HTML_PAGE = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Mutação Store</title>
  <style>
    * { box-sizing: border-box; font-family: Arial, sans-serif; }
    body { margin: 0; background: #0f1117; color: #f5f7fa; }
    header {
      background: #171a24; padding: 16px 20px;
      display: flex; justify-content: space-between; align-items: center;
      border-bottom: 1px solid #262b3d; position: sticky; top: 0; z-index: 10;
    }
    .brand { font-size: 1.25rem; font-weight: bold; color: #00e5a8; }
    .btn {
      background: #00e5a8; color: #0b0e14; border: none; padding: 10px 14px;
      border-radius: 8px; font-weight: bold; cursor: pointer; text-decoration: none;
      display: inline-block;
    }
    .btn-outline {
      background: transparent; color: #f5f7fa; border: 1px solid #39405a;
      padding: 8px 12px; border-radius: 8px; cursor: pointer; text-decoration: none;
    }
    .container { max-width: 1080px; margin: 24px auto; padding: 0 16px; }
    .grid {
      display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 18px;
    }
    .card {
      background: #171a24; border: 1px solid #262b3d; border-radius: 14px;
      overflow: hidden; display: flex; flex-direction: column; justify-content: space-between;
    }
    .card-cover {
      height: 170px; background: linear-gradient(135deg, #1f2538, #122826);
      display: flex; align-items: center; justify-content: center; font-size: 2.2rem;
    }
    .card-body { padding: 16px; }
    .card-title { margin: 0 0 8px; font-size: 1.1rem; }
    .card-desc { margin: 0 0 14px; color: #a7b0c5; font-size: 0.9rem; line-height: 1.4; }
    select, input, textarea {
      width: 100%; padding: 10px; margin-bottom: 10px; border-radius: 8px;
      border: 1px solid #323952; background: #0f1117; color: #fff;
    }
    .price { font-size: 1.25rem; font-weight: bold; color: #00e5a8; margin-bottom: 12px; }
    .modal-bg {
      display: none; position: fixed; inset: 0; background: rgba(0,0,0,0.75);
      align-items: center; justify-content: center; padding: 16px; z-index: 50;
    }
    .modal {
      background: #171a24; border: 1px solid #2c334a; border-radius: 14px;
      max-width: 460px; width: 100%; padding: 20px; max-height: 90vh; overflow-y: auto;
    }
    .pix-box {
      background: #0f1117; border: 1px dashed #00e5a8; padding: 12px;
      border-radius: 10px; word-break: break-all; font-size: 0.85rem; margin: 10px 0;
    }
    .admin-section {
      margin-top: 36px; background: #171a24; border: 1px solid #262b3d;
      border-radius: 14px; padding: 18px;
    }
    .whatsapp-float {
      position: fixed; right: 18px; bottom: 18px; background: #25d366; color: #09130d;
      font-weight: bold; padding: 12px 16px; border-radius: 999px; text-decoration: none;
      box-shadow: 0 6px 20px rgba(0,0,0,0.4);
    }
    .small { font-size: 0.82rem; color: #9aa4bc; }
  </style>
</head>
<body>
  <header>
    <div class="brand">⚡ MUTAÇÃO STORE</div>
    <div>
      <button class="btn-outline" onclick="toggleAudio()">🔊 Som</button>
      <a class="btn-outline" href="#admin">Catálogo</a>
    </div>
  </header>

  <div class="container">
    <p class="small">Escolha um plano, gere o Pix instantâneo e receba seu acesso automaticamente após a confirmação.</p>

    <div class="grid" id="productsGrid"></div>

    <section class="admin-section" id="admin">
      <h3>Gerenciar Catálogo (Adicionar Produto)</h3>
      <form id="addProductForm">
        <input type="text" id="prodName" placeholder="Nome do produto" required />
        <textarea id="prodDesc" rows="2" placeholder="Descrição curta do produto" required></textarea>
        <input type="number" step="0.01" id="priceBasic" placeholder="Preço Plano Básico (ex: 19.90)" required />
        <input type="number" step="0.01" id="pricePro" placeholder="Preço Plano Completo (ex: 39.90)" required />
        <input type="text" id="deliveryInfo" placeholder="Entrega automática (ex: Login: user | Senha: 123)" required />
        <button class="btn" type="submit">Salvar Produto</button>
      </form>
    </section>
  </div>

  <div class="modal-bg" id="checkoutModal">
    <div class="modal">
      <h3 id="checkoutTitle" style="margin-top:0;">Finalizar Compra</h3>
      <label class="small">Seu e-mail para entrega</label>
      <input type="email" id="buyerEmail" placeholder="cliente@email.com" required />
      <div id="pixResult"></div>
      <div style="display:flex; gap:10px; margin-top:12px;">
        <button class="btn" id="generatePixBtn" onclick="generatePix()">Gerar Pix</button>
        <button class="btn-outline" onclick="closeModal()">Fechar</button>
      </div>
    </div>
  </div>

  <a class="whatsapp-float" id="whatsappLink" href="https://wa.me/5585999999999" target="_blank">💬 WhatsApp</a>

  <script>
    let products = [];
    let selectedProduct = null;
    let audioEnabled = false;

    function playEntranceChime() {
      if (!audioEnabled) return;
      const ctx = new (window.AudioContext || window.webkitAudioContext)();
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = "sine";
      osc.frequency.setValueAtTime(523.25, ctx.currentTime);
      osc.frequency.exponentialRampToValueAtTime(783.99, ctx.currentTime + 0.25);
      gain.gain.setValueAtTime(0.08, ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.35);
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start();
      osc.stop(ctx.currentTime + 0.35);
    }

    function toggleAudio() {
      audioEnabled = !audioEnabled;
      if (audioEnabled) playEntranceChime();
      alert(audioEnabled ? "Som da loja ativado!" : "Som desativado.");
    }

    async function loadProducts() {
      const res = await fetch("/api/products");
      const data = await res.json();
      products = data.products;
      if (data.whatsapp_number) {
        document.getElementById("whatsappLink").href = `https://wa.me/${data.whatsapp_number}`;
      }
      renderProducts();
    }

    function renderProducts() {
      const grid = document.getElementById("productsGrid");
      grid.innerHTML = "";
      products.forEach((p, idx) => {
        const card = document.createElement("div");
        card.className = "card";
        card.innerHTML = `
          <div>
            <div class="card-cover">🛒</div>
            <div class="card-body">
              <h3 class="card-title">${p.name}</h3>
              <p class="card-desc">${p.description}</p>
              <label class="small">Escolha o plano:</label>
              <select id="tier-${idx}" onchange="updateCardPrice(${idx})">
                <option value="basico" data-price="${p.price_basic}">Básico - R$ ${Number(p.price_basic).toFixed(2)}</option>
                <option value="completo" data-price="${p.price_pro}">Completo - R$ ${Number(p.price_pro).toFixed(2)}</option>
              </select>
              <div class="price" id="price-${idx}">R$ ${Number(p.price_basic).toFixed(2)}</div>
              <button class="btn" style="width:100%;" onclick="openCheckout(${idx})">Comprar com Pix</button>
            </div>
          </div>
        `;
        grid.appendChild(card);
      });
    }

    function updateCardPrice(idx) {
      const select = document.getElementById(`tier-${idx}`);
      const price = Number(select.selectedOptions[0].dataset.price);
      document.getElementById(`price-${idx}`).innerText = `R$ ${price.toFixed(2)}`;
    }

    function openCheckout(idx) {
      const select = document.getElementById(`tier-${idx}`);
      const tier = select.value;
      const price = Number(select.selectedOptions[0].dataset.price);
      selectedProduct = { ...products[idx], tier, price };
      document.getElementById("checkoutTitle").innerText = `${selectedProduct.name} (${tier})`;
      document.getElementById("pixResult").innerHTML = "";
      document.getElementById("generatePixBtn").disabled = false;
      document.getElementById("checkoutModal").style.display = "flex";
    }

    function closeModal() {
      document.getElementById("checkoutModal").style.display = "none";
    }

    async function generatePix() {
      const email = document.getElementById("buyerEmail").value.trim();
      if (!email) {
        alert("Digite seu e-mail para receber o acesso.");
        return;
      }
      const btn = document.getElementById("generatePixBtn");
      btn.disabled = true;
      btn.innerText = "Gerando Pix...";

      const res = await fetch("/api/create-pix", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          product_id: selectedProduct.id,
          tier: selectedProduct.tier,
          email
        })
      });
      const data = await res.json();
      btn.innerText = "Gerar Pix";

      if (!res.ok) {
        btn.disabled = false;
        alert(data.error || "Erro ao gerar Pix");
        return;
      }

      document.getElementById("pixResult").innerHTML = `
        <p class="small">Valor: <strong>R$ ${Number(selectedProduct.price).toFixed(2)}</strong></p>
        <div class="pix-box">${data.qr_code || "Código Pix gerado."}</div>
        <button class="btn" onclick="checkPayment('${data.payment_id}')">Já paguei — Verificar entrega</button>
        <div id="deliveryBox" style="margin-top:12px;"></div>
      `;
    }

    async function checkPayment(paymentId) {
      const res = await fetch(`/api/check-payment/${paymentId}`);
      const data = await res.json();
      const box = document.getElementById("deliveryBox");
      if (data.status === "approved") {
        box.innerHTML = `<div class="pix-box"><strong>✅ Pagamento aprovado!</strong><br/>Seu acesso: ${data.delivery}</div>`;
      } else {
        box.innerHTML = `<p class="small">Status atual: <strong>${data.status}</strong>. Aguarde a confirmação e clique novamente.</p>`;
      }
    }

    document.getElementById("addProductForm").addEventListener("submit", async (e) => {
      e.preventDefault();
      const payload = {
        name: document.getElementById("prodName").value.trim(),
        description: document.getElementById("prodDesc").value.trim(),
        price_basic: parseFloat(document.getElementById("priceBasic").value),
        price_pro: parseFloat(document.getElementById("pricePro").value),
        delivery_info: document.getElementById("deliveryInfo").value.trim()
      };
      const res = await fetch("/api/products", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      if (res.ok) {
        e.target.reset();
        loadProducts();
        alert("Produto adicionado ao catálogo!");
      }
    });

    loadProducts();
  </script>
</body>
</html>"""


@app.route("/")
def index():
    return render_template_string(HTML_PAGE)


@app.route("/api/products", methods=["GET", "POST"])
def products():
    conn = get_db()
    if request.method == "POST":
        data = request.get_json(force=True)
        conn.execute("""
            INSERT INTO products (name, description, price_basic, price_pro, delivery_info)
            VALUES (?, ?, ?, ?, ?)
        """, (
            data["name"],
            data["description"],
            float(data["price_basic"]),
            float(data["price_pro"]),
            data["delivery_info"],
        ))
        conn.commit()
        conn.close()
        return jsonify({"ok": True}), 201

    rows = [dict(r) for r in conn.execute("SELECT * FROM products ORDER BY id DESC").fetchall()]
    conn.close()
    return jsonify({"products": rows, "whatsapp_number": WHATSAPP_NUMBER})


@app.route("/api/create-pix", methods=["POST"])
def create_pix():
    if not MP_ACCESS_TOKEN:
        return jsonify({"error": "MP_ACCESS_TOKEN não configurado no servidor."}), 400

    data = request.get_json(force=True)
    product_id = int(data["product_id"])
    tier = data.get("tier", "basico")
    buyer_email = data.get("email", "cliente@exemplo.com")

    conn = get_db()
    prod = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
    if not prod:
        conn.close()
        return jsonify({"error": "Produto não encontrado."}), 404

    amount = float(prod["price_pro"] if tier == "completo" else prod["price_basic"])
    idem_key = str(uuid.uuid4())

    payload = {
        "transaction_amount": round(amount, 2),
        "description": f"{prod['name']} ({tier})",
        "payment_method_id": "pix",
        "payer": {"email": buyer_email},
    }
    headers = {
        "Authorization": f"Bearer {MP_ACCESS_TOKEN}",
        "Content-Type": "application/json",
        "X-Idempotency-Key": idem_key,
    }

    r = requests.post("https://api.mercadopago.com/v1/payments", json=payload, headers=headers, timeout=15)
    if r.status_code not in (200, 201):
        conn.close()
        return jsonify({"error": f"Falha no Mercado Pago: {r.text}"}), 400

    mp_data = r.json()
    payment_id = str(mp_data["id"])
    status = mp_data.get("status", "pending")
    qr_code = (
        mp_data.get("point_of_interaction", {})
        .get("transaction_data", {})
        .get("qr_code", "")
    )

    conn.execute("""
        INSERT INTO orders (payment_id, product_id, tier, buyer_email, amount, status, notified)
        VALUES (?, ?, ?, ?, ?, ?, 0)
    """, (payment_id, product_id, tier, buyer_email, amount, status))
    conn.commit()
    conn.close()

    send_telegram(
        f"🆕 <b>Novo Pix gerado — Mutação Store</b>\n"
        f"Produto: {prod['name']} ({tier})\n"
        f"Valor: R$ {amount:.2f}\n"
        f"Cliente: {buyer_email}\n"
        f"ID: <code>{payment_id}</code>"
    )

    return jsonify({"payment_id": payment_id, "qr_code": qr_code, "status": status})


@app.route("/api/check-payment/<payment_id>")
def check_payment(payment_id):
    conn = get_db()
    order = conn.execute("SELECT * FROM orders WHERE payment_id = ?", (payment_id,)).fetchone()
    if not order:
        conn.close()
        return jsonify({"error": "Pedido não encontrado."}), 404

    prod = conn.execute("SELECT * FROM products WHERE id = ?", (order["product_id"],)).fetchone()
    status = fetch_mp_payment_status(payment_id)

    conn.execute("UPDATE orders SET status = ? WHERE payment_id = ?", (status, payment_id))
    notified = order["notified"]

    if status == "approved" and notified == 0:
        conn.execute("UPDATE orders SET notified = 1 WHERE payment_id = ?", (payment_id,))
        send_telegram(
            f"✅ <b>Pagamento Pix APROVADO!</b>\n"
            f"Produto: {prod['name']} ({order['tier']})\n"
            f"Valor: R$ {order['amount']:.2f}\n"
            f"Cliente: {order['buyer_email']}"
        )

    conn.commit()
    conn.close()

    return jsonify({
        "status": status,
        "delivery": prod["delivery_info"] if status == "approved" else None,
    })


init_db()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
                    

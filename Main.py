import datetime as dt

import pandas as pd
import streamlit as st

SHOP = "Bean & Bloom"
CURRENCY = "Rs."
SIZES = {"Small": 0, "Medium": 50, "Large": 100}
TAX = 0.05
MENU = [
    {"name": "Espresso", "cat": "Coffee", "price": 250, "emoji": "☕"},
    {"name": "Americano", "cat": "Coffee", "price": 300, "emoji": "☕"},
    {"name": "Cappuccino", "cat": "Coffee", "price": 400, "emoji": "☕"},
    {"name": "Latte", "cat": "Coffee", "price": 420, "emoji": "🥛"},
    {"name": "Caramel Macchiato", "cat": "Coffee", "price": 480, "emoji": "🍮"},
    {"name": "Iced Coffee", "cat": "Cold", "price": 380, "emoji": "🧊"},
    {"name": "Cold Brew", "cat": "Cold", "price": 450, "emoji": "🧋"},
    {"name": "Mango Smoothie", "cat": "Cold", "price": 420, "emoji": "🥭"},
    {"name": "Masala Chai", "cat": "Tea", "price": 220, "emoji": "🫖"},
    {"name": "Green Tea", "cat": "Tea", "price": 200, "emoji": "🍵"},
    {"name": "Croissant", "cat": "Bakery", "price": 280, "emoji": "🥐"},
    {"name": "Blueberry Muffin", "cat": "Bakery", "price": 300, "emoji": "🧁"},
    {"name": "Chocolate Brownie", "cat": "Bakery", "price": 320, "emoji": "🍫"},
]

st.set_page_config(page_title=SHOP, page_icon="☕", layout="centered")
st.markdown(
    """
    <style>
    .stApp { background:#FFF8F0; }
    [data-testid="stSidebar"] { background:#EADBC8; }
    h1, h2, h3, h4 { color:#4B2E1E; }
    .card { background:#F3E5D3; padding:12px 16px; border-radius:14px; margin-bottom:8px; }
    div.stButton > button, div.stFormSubmitButton > button { background:#6F4E37; color:white; border:0; border-radius:10px; }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_resource
def store():
    """Shared by all visitors while the app is running (resets when the app restarts)."""
    return {"orders": [], "next_id": 1001, "stamps": {}}


db = store()
st.session_state.setdefault("cart", [])
st.session_state.setdefault("last", None)


def money(x):
    return f"{CURRENCY} {x:,.0f}"


def owner_pin():
    try:
        return str(st.secrets.get("OWNER_PIN", "1234"))
    except Exception:
        return "1234"


cart_count = sum(i["qty"] for i in st.session_state.cart)
page = st.sidebar.radio(f"☕ {SHOP}", ["Menu", f"Cart ({cart_count})", "Loyalty Card", "Owner"])

# ---------------- Menu ----------------
if page == "Menu":
    st.title(f"☕ {SHOP}")
    st.caption("Fresh coffee, ready for pickup. Choose your drinks below.")
    cats = list(dict.fromkeys(m["cat"] for m in MENU))
    for tab, cat in zip(st.tabs(cats), cats):
        with tab:
            for m in [x for x in MENU if x["cat"] == cat]:
                a, b, c, d = st.columns([3, 2, 1.3, 1.3])
                a.markdown(f"**{m['emoji']} {m['name']}**  \n{money(m['price'])}")
                size = b.selectbox("Size", list(SIZES), key=f"s_{m['name']}", label_visibility="collapsed") \
                    if cat != "Bakery" else "Regular"
                qty = c.number_input("Qty", 1, 10, 1, key=f"q_{m['name']}", label_visibility="collapsed")
                if d.button("Add", key=f"a_{m['name']}"):
                    unit = m["price"] + SIZES.get(size, 0)
                    st.session_state.cart.append({"name": m["name"], "size": size, "qty": int(qty), "unit": unit})
                    st.toast(f"Added {qty} × {m['name']}")
                    st.rerun()

# ---------------- Cart ----------------
elif page.startswith("Cart"):
    st.title("🛒 Your Cart")
    cart = st.session_state.cart
    if st.session_state.last and not cart:
        o = st.session_state.last
        st.success(f"Order #{o['id']} placed! Pickup at {o['pickup']}. Total {money(o['total'])}.")
        st.balloons()
        st.session_state.last = None
    elif not cart:
        st.write("Your cart is empty. Add something from the Menu.")
    else:
        for i, it in enumerate(cart):
            a, b = st.columns([5, 1])
            a.markdown(
                f'<div class="card">{it["qty"]} × <b>{it["name"]}</b> ({it["size"]}) — {money(it["qty"] * it["unit"])}</div>',
                unsafe_allow_html=True,
            )
            if b.button("🗑", key=f"rm{i}"):
                cart.pop(i)
                st.rerun()
        sub = sum(i["qty"] * i["unit"] for i in cart)
        tax = sub * TAX
        total = sub + tax
        st.write(f"Subtotal: {money(sub)}  \nTax ({TAX:.0%}): {money(tax)}  \n**Total: {money(total)}**")
        with st.form("checkout"):
            name = st.text_input("Your name")
            pickup = st.time_input("Pickup time", (dt.datetime.now() + dt.timedelta(minutes=15)).time())
            note = st.text_input("Notes (optional)", placeholder="e.g. oat milk, less sugar")
            if st.form_submit_button("Place order"):
                if not name.strip():
                    st.error("Please enter your name.")
                else:
                    oid = db["next_id"]
                    db["next_id"] += 1
                    db["orders"].append({
                        "id": oid, "name": name.strip(), "time": dt.datetime.now().strftime("%H:%M"),
                        "pickup": pickup.strftime("%I:%M %p"), "items": ", ".join(f"{i['qty']}× {i['name']} ({i['size']})" for i in cart),
                        "note": note.strip(), "total": round(total), "status": "Preparing",
                    })
                    key = name.strip().lower()
                    db["stamps"][key] = db["stamps"].get(key, 0) + 1
                    st.session_state.last = db["orders"][-1]
                    st.session_state.cart = []
                    st.rerun()

# ---------------- Loyalty ----------------
elif page == "Loyalty Card":
    st.title("🎁 Loyalty Card")
    st.write("Every 5th order earns a free drink. Enter the name you order with.")
    who = st.text_input("Your name").strip().lower()
    if who:
        n = db["stamps"].get(who, 0)
        st.progress((n % 5) / 5, text=f"{n % 5} / 5 stamps")
        st.write(f"Total orders: {n}  ·  Free drinks earned: {n // 5}")

# ---------------- Owner ----------------
else:
    st.title("🔒 Owner Dashboard")
    if st.text_input("PIN", type="password") != owner_pin():
        st.info("Enter the owner PIN to view orders. (Default: 1234. Set OWNER_PIN in Streamlit secrets.)")
    else:
        orders = db["orders"]
        if not orders:
            st.write("No orders yet.")
        else:
            df = pd.DataFrame(orders)
            c1, c2 = st.columns(2)
            c1.metric("Orders", len(df))
            c2.metric("Sales", money(df["total"].sum()))
            st.dataframe(df, hide_index=True, use_container_width=True)
            with st.form("status"):
                oid = st.selectbox("Order #", [o["id"] for o in reversed(orders)])
                status = st.selectbox("Status", ["Preparing", "Ready", "Picked up"])
                if st.form_submit_button("Update"):
                    next(o for o in orders if o["id"] == oid)["status"] = status
                    st.rerun()
            st.download_button("Download orders (CSV)", df.to_csv(index=False), "orders.csv", "text/csv")

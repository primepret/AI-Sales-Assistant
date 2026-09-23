import os
import hashlib
from io import StringIO
import json
import secrets
import sqlite3
from pathlib import Path
from datetime import date, datetime, timezone
from urllib.parse import quote

import pandas as pd
import streamlit as st

APP_DIR = Path(__file__).resolve().parent
ACCOUNT_DB = APP_DIR / "accounts.db"
VOICE_INPUT_COMPONENT = st.components.v1.declare_component(
    "prime_pret_voice_input",
    path=str(APP_DIR / "voice_input_component"),
)

try:
    from openai import OpenAI
except ImportError:  # pragma: no cover
    OpenAI = None

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:  # pragma: no cover
    pass


def get_openai_api_key():
    environment_key = os.getenv("OPENAI_API_KEY", "").strip()
    if environment_key:
        return environment_key
    try:
        return str(st.secrets.get("OPENAI_API_KEY", "")).strip()
    except Exception:
        return ""


def get_openai_model():
    environment_model = os.getenv("OPENAI_MODEL", "").strip()
    if environment_model:
        return environment_model
    try:
        return str(st.secrets.get("OPENAI_MODEL", "gpt-4o-mini")).strip()
    except Exception:
        return "gpt-4o-mini"


LIVE_AI_ENABLED = bool(get_openai_api_key()) and OpenAI is not None
AI_FEATURES = {
    "Business insights": True,
    "Product descriptions": True,
    "Sales forecasting": True,
    "WhatsApp summaries": True,
    "Voice input": True,
    "Live OpenAI responses": LIVE_AI_ENABLED,
}

# -----------------------------
# PRIME PRET POS
# -----------------------------

def resolve_logo_asset():
    candidates = [
        APP_DIR / "assets" / "Logo",
        APP_DIR / "assets" / "brand-logo.svg",
        APP_DIR / "assets" / "prime-pret-logo.svg",
    ]
    for candidate in candidates:
        if candidate.exists() and candidate.stat().st_size > 0:
            return str(candidate)
    return None

logo_asset = resolve_logo_asset()

st.set_page_config(
    page_title="Prime Pret POS",
    page_icon=logo_asset or "💼",
    layout="wide"
)

st.markdown(
    """
    <style>
        .stApp {
            background: radial-gradient(circle at top left, #1e1713 0%, #100d0c 35%, #080808 100%);
            color: #f5ead7;
        }
        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #0d0d0d 0%, #18120f 100%);
            border-right: 1px solid rgba(214, 169, 92, 0.5);
            box-shadow: inset -1px 0 0 rgba(214,169,92,0.25);
        }
        [data-testid="stSidebar"] .stRadio > label,
        [data-testid="stSidebar"] .stRadio > div,
        [data-testid="stSidebar"] .stSidebarHeader {
            color: #f1deba !important;
        }
        [data-testid="stSidebar"] .stRadio [role="radio"] {
            color: #f1deba !important;
            border-color: rgba(214,169,92,0.4) !important;
        }
        [data-testid="stSidebar"] .stRadio [role="radio"]::before {
            border-color: #d8b36a !important;
        }
        .main .block-container {
            padding-top: 1.5rem;
            padding-bottom: 3rem;
        }
        .brand-header {
            font-size: 2.7rem;
            font-weight: 800;
            letter-spacing: 0.04em;
            color: #f3dfb3;
            margin-bottom: 0.25rem;
            text-shadow: 0 0 18px rgba(216,179,106,0.22);
        }
        .brand-subheader {
            font-size: 1.05rem;
            color: #d7b87b;
            margin-bottom: 1.5rem;
        }
        .luxury-tag {
            display: inline-block;
            background: rgba(214,169,92,0.12);
            border: 1px solid rgba(214,169,92,0.7);
            color: #f1deba;
            padding: 0.4rem 0.8rem;
            border-radius: 999px;
            font-size: 0.78rem;
            font-weight: 700;
            letter-spacing: 0.14em;
            margin-bottom: 1rem;
            text-transform: uppercase;
        }
        div[data-testid="stMetricValue"] {
            color: #fff9ee;
            font-weight: 700;
        }
        div[data-testid="stMetricLabel"] {
            color: #d0b07a;
        }
        .stButton > button {
            background: linear-gradient(90deg, #d7b36a 0%, #8f6527 100%);
            color: #120d09;
            border: 1px solid rgba(255, 230, 169, 0.7);
            border-radius: 10px;
            font-weight: 700;
            box-shadow: 0 8px 20px rgba(202, 152, 73, 0.28);
        }
        .stButton > button:hover {
            filter: brightness(1.08);
        }
        h1, h2, h3, h4, h5, h6 {
            color: #f4e8d1 !important;
        }
        .stDataFrame, .stDataFrame * {
            color: #fffdf9 !important;
        }
        .stCode {
            background: rgba(255,255,255,0.04) !important;
            border: 1px solid rgba(214,169,92,0.3) !important;
        }
        .stAlert, .stInfo, .stSuccess, .stWarning {
            border-radius: 12px;
        }
        .st-key-mobile-navigation {
            display: none;
        }
        @media (max-width: 768px) {
            .main .block-container {
                padding: 0.75rem 0.65rem 2rem;
            }
            .brand-header {
                font-size: 1.75rem;
                line-height: 1.15;
            }
            .brand-subheader {
                font-size: 0.92rem;
                line-height: 1.4;
                margin-bottom: 1rem;
            }
            .luxury-tag {
                font-size: 0.66rem;
                letter-spacing: 0.1em;
                padding: 0.35rem 0.55rem;
            }
            [data-testid="stSidebar"] {
                min-width: 82vw;
                max-width: 88vw;
            }
            [data-testid="stSidebar"] img {
                max-width: 180px;
                margin: 0 auto;
            }
            [data-testid="stMetric"] {
                min-width: 0;
            }
            [data-testid="stMetricValue"] {
                font-size: 1.15rem;
            }
            [data-testid="stMetricLabel"] {
                font-size: 0.72rem;
            }
            .stButton > button,
            .stFormSubmitButton > button,
            [data-testid="stFileUploader"] button {
                min-height: 2.8rem;
                width: 100%;
            }
            input, textarea, select {
                font-size: 16px !important;
            }
            [data-testid="stDataFrame"] {
                overflow-x: auto;
            }
            .st-key-mobile-navigation {
                display: block;
                margin-bottom: 1rem;
            }
            h1 {
                font-size: 1.7rem !important;
            }
            h2 {
                font-size: 1.4rem !important;
            }
            h3 {
                font-size: 1.2rem !important;
            }
        }
    </style>
    """,
    unsafe_allow_html=True,
)

if "branding_loaded" not in st.session_state:
    st.session_state.branding_loaded = True

if "show_splash" not in st.session_state:
    st.session_state.show_splash = True

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if "username" not in st.session_state:
    st.session_state.username = ""

if "employee_code" not in st.session_state:
    st.session_state.employee_code = ""

if "user_role" not in st.session_state:
    st.session_state.user_role = ""

if "user_access" not in st.session_state:
    st.session_state.user_access = []

if "user_access" not in st.session_state:
    st.session_state.user_access = []

if "login_error" not in st.session_state:
    st.session_state.login_error = ""

if "keyboard_shortcuts_enabled" not in st.session_state:
    st.session_state.keyboard_shortcuts_enabled = True

if "shortcut_bindings" not in st.session_state:
    st.session_state.shortcut_bindings = {
        "Dashboard": "1",
        "POS": "2",
        "Products": "3",
        "Sales": "4",
        "AI Manager": "5",
    }

VALID_ACCOUNTS = {
    "admin": {"password": "admin123", "role": "Administrator", "access": ["all"]},
    "manager": {"password": "manager123", "role": "Store Manager", "access": ["🏠 Dashboard", "🛒 POS", "📦 Products", "📊 Sales", "🤖 AI Manager", "👥 Cashier Management", "➕ Add Cashier"]},
    "cashier1": {"password": "cashier123", "role": "Cashier", "access": ["🏠 Dashboard", "🛒 POS", "📊 Sales"]},
    "cashier2": {"password": "cashier234", "role": "Cashier", "access": ["🏠 Dashboard", "🛒 POS", "📊 Sales"]},
    "cashier3": {"password": "cashier345", "role": "Cashier", "access": ["🏠 Dashboard", "🛒 POS", "📊 Sales"]},
    "cashier4": {"password": "cashier456", "role": "Cashier", "access": ["🏠 Dashboard", "🛒 POS", "📊 Sales"]},
}

def hash_password(password: str, provided_salt: bytes | None = None):
    generated_salt = provided_salt or secrets.token_bytes(16)
    password_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        generated_salt,
        120_000,
    )
    return generated_salt.hex(), password_hash.hex()


def verify_password(password: str, salt_hex: str, password_hash_hex: str):
    _, candidate_hash = hash_password(password, bytes.fromhex(salt_hex))
    return secrets.compare_digest(candidate_hash, password_hash_hex)


def create_employee_code(connection, role: str):
    while True:
        code = str(secrets.randbelow(900000) + 100000)
        existing = connection.execute(
            "SELECT 1 FROM accounts WHERE employee_code = ?",
            (code,),
        ).fetchone()
        if not existing:
            return code


def initialize_account_database():
    with sqlite3.connect(ACCOUNT_DB) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS accounts (
                username TEXT PRIMARY KEY,
                password_hash TEXT NOT NULL,
                salt TEXT NOT NULL,
                role TEXT NOT NULL,
                access TEXT NOT NULL,
                employee_code TEXT UNIQUE
            )
            """
        )
        account_columns = {
            row[1] for row in connection.execute("PRAGMA table_info(accounts)")
        }
        if "employee_code" not in account_columns:
            connection.execute("ALTER TABLE accounts ADD COLUMN employee_code TEXT")
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS business_data_scoped (
                owner TEXT NOT NULL,
                name TEXT NOT NULL,
                payload TEXT NOT NULL,
                PRIMARY KEY (owner, name)
            )
            """
        )
        connection.execute("DELETE FROM accounts WHERE username = 'cashier'")
        for username, account in VALID_ACCOUNTS.items():
            salt, password_hash = hash_password(account["password"])
            connection.execute(
                """
                INSERT OR IGNORE INTO accounts
                (username, password_hash, salt, role, access, employee_code)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    username,
                    password_hash,
                    salt,
                    account["role"],
                    json.dumps(account["access"]),
                    create_employee_code(connection, account["role"]),
                ),
            )
            connection.execute(
                "UPDATE accounts SET role = ?, access = ? WHERE username = ?",
                (account["role"], json.dumps(account["access"]), username),
            )
        for username, role, employee_code in connection.execute(
            "SELECT username, role, employee_code FROM accounts"
        ).fetchall():
            if not employee_code or not employee_code.isdigit():
                connection.execute(
                    "UPDATE accounts SET employee_code = ? WHERE username = ?",
                    (create_employee_code(connection, role), username),
                )


def get_account(username: str):
    with sqlite3.connect(ACCOUNT_DB) as connection:
        return connection.execute(
            "SELECT username, password_hash, salt, role, access, employee_code FROM accounts "
            "WHERE username = ? OR employee_code = ?",
            (username, username.upper()),
        ).fetchone()


def get_cashier_accounts():
    with sqlite3.connect(ACCOUNT_DB) as connection:
        return connection.execute(
            "SELECT username, role, employee_code FROM accounts WHERE role = 'Cashier' ORDER BY username"
        ).fetchall()


def get_manager_accounts():
    with sqlite3.connect(ACCOUNT_DB) as connection:
        return connection.execute(
            "SELECT username, role, employee_code FROM accounts WHERE role = 'Store Manager' ORDER BY username"
        ).fetchall()


def create_cashier_account(username: str, password: str, confirm_password: str):
    cleaned_username = (username or "").strip().lower()
    if not cleaned_username:
        return False, "Username cannot be empty."
    if len(password) < 8:
        return False, "Password must be at least 8 characters."
    if password != confirm_password:
        return False, "Passwords do not match."

    with sqlite3.connect(ACCOUNT_DB) as connection:
        existing = connection.execute(
            "SELECT username FROM accounts WHERE username = ?",
            (cleaned_username,),
        ).fetchone()
        if existing:
            return False, "That username is already in use."

        salt, password_hash = hash_password(password)
        employee_code = create_employee_code(connection, "Cashier")
        connection.execute(
            """
            INSERT INTO accounts (username, password_hash, salt, role, access, employee_code)
            VALUES (?, ?, ?, 'Cashier', ?, ?)
            """,
            (
                cleaned_username,
                password_hash,
                salt,
                json.dumps(["🏠 Dashboard", "🛒 POS", "📊 Sales"]),
                employee_code,
            ),
        )
    return True, f"{cleaned_username} (Employee code: {employee_code})"


def create_manager_account(username: str, password: str, confirm_password: str):
    cleaned_username = (username or "").strip().lower()
    if not cleaned_username:
        return False, "Username cannot be empty."
    if len(password) < 8:
        return False, "Password must be at least 8 characters."
    if password != confirm_password:
        return False, "Passwords do not match."

    with sqlite3.connect(ACCOUNT_DB) as connection:
        existing = connection.execute(
            "SELECT username FROM accounts WHERE username = ?",
            (cleaned_username,),
        ).fetchone()
        if existing:
            return False, "That username is already in use."

        salt, password_hash = hash_password(password)
        employee_code = create_employee_code(connection, "Store Manager")
        connection.execute(
            """
            INSERT INTO accounts (username, password_hash, salt, role, access, employee_code)
            VALUES (?, ?, ?, 'Store Manager', ?, ?)
            """,
            (
                cleaned_username,
                password_hash,
                salt,
                json.dumps([
                    "🏠 Dashboard",
                    "🛒 POS",
                    "📦 Products",
                    "📊 Sales",
                    "🤖 AI Manager",
                    "👥 Cashier Management",
                    "➕ Add Cashier",
                ]),
                employee_code,
            ),
        )
    return True, f"{cleaned_username} (Employee code: {employee_code})"


def update_cashier_credentials(current_username: str, new_username: str, new_password: str):
    cleaned_username = new_username.strip().lower()
    if not cleaned_username:
        return False, "Username cannot be empty."
    if len(new_password) < 8:
        return False, "Password must be at least 8 characters."

    with sqlite3.connect(ACCOUNT_DB) as connection:
        existing = connection.execute(
            "SELECT role FROM accounts WHERE username = ?",
            (cleaned_username,),
        ).fetchone()
        if existing and cleaned_username != current_username:
            return False, "That username is already in use."

        salt, password_hash = hash_password(new_password)
        connection.execute(
            "UPDATE accounts SET username = ?, password_hash = ?, salt = ? WHERE username = ? AND role = 'Cashier'",
            (cleaned_username, password_hash, salt, current_username),
        )
        connection.execute(
            "UPDATE business_data_scoped SET owner = ? WHERE owner = ?",
            (cleaned_username, current_username),
        )
    return True, cleaned_username


def get_cashier_data(username: str):
    with sqlite3.connect(ACCOUNT_DB) as connection:
        rows = dict(
            connection.execute(
                "SELECT name, payload FROM business_data_scoped WHERE owner = ?",
                (username,),
            )
        )
    data = {}
    for name in ("products", "sales", "expenses"):
        payload = rows.get(name)
        data[name] = pd.read_json(StringIO(payload), orient="records") if payload else pd.DataFrame()
    normalize_product_image_paths(data["products"])
    return data


def resolve_product_image_path(image_value):
    if not isinstance(image_value, str):
        return None
    image_value = image_value.strip()
    if not image_value or image_value.startswith("[") or image_value.startswith("{"):
        return None
    image_path = Path(image_value)
    if not image_path.is_absolute():
        image_path = APP_DIR / image_path
    if image_path.is_file():
        return str(image_path)
    return None


def normalize_product_image_paths(products: pd.DataFrame):
    if "Image Path" not in products.columns:
        return
    products["Image Path"] = products["Image Path"].map(
        lambda value: value if resolve_product_image_path(value) else ""
    )


def render_product_image(image_value, caption: str):
    image_path = resolve_product_image_path(image_value)
    try:
        if image_path:
            st.image(image_path, caption=caption, width=200)
        else:
            st.image(
                "https://placehold.co/300x300/png?text=No+Photo",
                caption=caption,
                width=200,
            )
    except Exception:
        st.caption(f"{caption} (photo unavailable)")


def update_account_password(username: str, password: str):
    salt, password_hash = hash_password(password)
    with sqlite3.connect(ACCOUNT_DB) as connection:
        connection.execute(
            "UPDATE accounts SET password_hash = ?, salt = ? WHERE username = ?",
            (password_hash, salt, username),
        )


def ensure_app_state_table():
    with sqlite3.connect(ACCOUNT_DB) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS app_state (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
            """
        )


def get_app_state_value(key: str, default=None):
    with sqlite3.connect(ACCOUNT_DB) as connection:
        row = connection.execute(
            "SELECT value FROM app_state WHERE key = ?",
            (key,),
        ).fetchone()
    return row[0] if row else default


def set_app_state_value(key: str, value: str):
    with sqlite3.connect(ACCOUNT_DB) as connection:
        connection.execute(
            "INSERT INTO app_state (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, str(value)),
        )


def set_business_data_refresh(owner: str):
    if not owner:
        return
    timestamp = datetime.now(timezone.utc).isoformat()
    set_app_state_value(f"business_data_updated:{owner}", timestamp)


def save_business_data(owner: str | None = None):
    owner = owner or st.session_state.get("username")
    if not owner:
        return
    with sqlite3.connect(ACCOUNT_DB) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS business_data_scoped (
                owner TEXT NOT NULL,
                name TEXT NOT NULL,
                payload TEXT NOT NULL,
                PRIMARY KEY (owner, name)
            )
            """
        )
        for name in ("products", "sales", "expenses"):
            payload = st.session_state[name].to_json(orient="records", date_format="iso")
            connection.execute(
                "INSERT OR REPLACE INTO business_data_scoped (owner, name, payload) VALUES (?, ?, ?)",
                (owner, name, payload),
            )
    set_business_data_refresh(owner)


def save_scoped_business_data(owner: str, data: dict[str, pd.DataFrame]):
    with sqlite3.connect(ACCOUNT_DB) as connection:
        for name in ("products", "sales", "expenses"):
            payload = data[name].to_json(orient="records", date_format="iso")
            connection.execute(
                "INSERT OR REPLACE INTO business_data_scoped (owner, name, payload) VALUES (?, ?, ?)",
                (owner, name, payload),
            )
    set_business_data_refresh(owner)


def load_business_data(owner: str):
    with sqlite3.connect(ACCOUNT_DB) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS business_data_scoped (
                owner TEXT NOT NULL,
                name TEXT NOT NULL,
                payload TEXT NOT NULL,
                PRIMARY KEY (owner, name)
            )
            """
        )
        stored_data = dict(
            connection.execute(
                "SELECT name, payload FROM business_data_scoped WHERE owner = ?",
                (owner,),
            )
        )

    for name in ("products", "sales", "expenses"):
        payload = stored_data.get(name)
        if payload:
            try:
                st.session_state[name] = pd.read_json(StringIO(payload), orient="records")
            except ValueError:
                pass
    normalize_product_image_paths(st.session_state.products)
    st.session_state.business_data_last_updated = get_app_state_value(f"business_data_updated:{owner}", "")


def auto_refresh_component(interval_seconds: int = 10):
    if not st.session_state.get("authenticated"):
        return
    st.components.v1.html(
        f"""
        <script>
            (() => {{
                const intervalMs = {interval_seconds * 1000};
                if (!window.__primePretAutoRefresh) {{
                    window.__primePretAutoRefresh = true;
                    setInterval(() => {{
                        if (document.visibilityState === 'visible') {{
                            window.location.reload();
                        }}
                    }}, intervalMs);
                }}
            }})();
        </script>
        """,
        height=0,
    )


initialize_account_database()
ensure_app_state_table()


def authenticate_user(username: str, password: str):
    cleaned_username = (username or "").strip().lower()
    if not cleaned_username:
        return None
    account = get_account(cleaned_username)
    if not account:
        return None
        username, password_hash, salt, role, access_json, employee_code = account
    if not verify_password(password or "", salt, password_hash):
        return None
    return {
        "username": username,
        "role": role,
        "access": json.loads(access_json),
            "employee_code": employee_code,
    }


def get_allowed_pages():
    user_access = list(st.session_state.get("user_access", []))
    user_role = st.session_state.get("user_role")
    all_pages = [
        "🏠 Dashboard",
        "🛒 POS",
        "📦 Products",
        "💰 Profit Calculator",
        "📊 Sales",
        "⚠️ Low Stock",
        "💸 Expenses",
        "🤖 AI Manager",
        "👥 Cashier Management",
        "➕ Add Manager",
        "➕ Add Cashier",
    ]
    if user_role == "Administrator" and "➕ Add Manager" not in user_access:
        user_access.append("➕ Add Manager")
    if user_role in ("Administrator", "Store Manager") and "➕ Add Cashier" not in user_access:
        user_access.append("➕ Add Cashier")
    if "all" in user_access:
        return all_pages
    if not user_access:
        return ["🏠 Dashboard"]
    return [page for page in all_pages if page in user_access or page == "🏠 Dashboard"]


def sync_mobile_page():
    st.session_state.mobile_page = st.session_state.sidebar_page


def is_administrator():
    return st.session_state.get("authenticated", False) and st.session_state.get("user_role") == "Administrator"


def is_cashier():
    return st.session_state.get("user_role") == "Cashier"


def keyboard_shortcuts_component(enabled: bool, bindings: dict[str, str]):
    if not enabled:
        return
    shortcut_targets = json.dumps({key: value for value, key in bindings.items()})
    shortcut_script = """
        <script>
            (() => {
                const shortcutTargets = __SHORTCUT_TARGETS__;

                function activatePage(pageName) {
                    const sidebar = window.parent.document.querySelector('[data-testid="stSidebar"]');
                    if (!sidebar) return;
                    const options = sidebar.querySelectorAll('[role="radio"]');
                    for (const option of options) {
                        if (option.textContent.includes(pageName)) {
                            option.click();
                            break;
                        }
                    }
                }

                if (!window.parent.__primePretShortcutsBound) {
                    window.parent.__primePretShortcutsBound = true;
                    window.parent.addEventListener("keydown", (event) => {
                        if (!event.altKey || event.ctrlKey || event.metaKey || event.shiftKey) return;
                        const pageName = shortcutTargets[event.key];
                        if (!pageName) return;
                        event.preventDefault();
                        activatePage(pageName);
                    });
                }
            })();
        </script>
        """.replace("__SHORTCUT_TARGETS__", shortcut_targets)
    st.components.v1.html(
        shortcut_script,
        height=0,
    )


if st.session_state.get("show_splash"):
    st.markdown(
        """
        <div style="position:fixed; inset:0; background:radial-gradient(circle at center, rgba(214,169,92,0.18), rgba(0,0,0,0.85) 45%, rgba(0,0,0,0.96)); display:flex; align-items:center; justify-content:center; z-index:9999;">
            <div style="text-align:center; animation: fadeInOut 2.5s ease-in-out;">
                <img src="data:image/svg+xml;utf8," alt="Prime Pret Logo" style="display:block; width:420px; max-width:75vw; margin:auto; filter: drop-shadow(0 0 25px rgba(214,169,92,0.35));"/>
                <div style="margin-top:18px; letter-spacing:0.28em; font-size:0.78rem; color:#d7b87b; text-transform:uppercase;">Prime Pret POS • Luxury AI Retail</div>
            </div>
        </div>
        <style>
            @keyframes fadeInOut {
                0% { opacity: 0; transform: scale(0.95); }
                25% { opacity: 1; transform: scale(1); }
                75% { opacity: 1; }
                100% { opacity: 0; transform: scale(1.02); }
            }
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.session_state.show_splash = False
    st.rerun()

# -----------------------------
# SESSION DATA
# -----------------------------

os.makedirs("product_images", exist_ok=True)

if "products" not in st.session_state:
    st.session_state.products = pd.DataFrame(columns=[
        "Barcode", "Product ID", "Product Name",
        "Design", "Fabric", "Colour", "Size",
        "Cost Price", "Selling Price", "Stock",
        "Reorder Level", "Image Path"
    ])

if "sales" not in st.session_state:
    st.session_state.sales = pd.DataFrame(columns=[
        "Date", "Invoice", "Barcode", "Product",
        "Qty", "Selling Price", "Discount",
            "Revenue", "Cost", "Profit", "Amount Paid", "Change"
    ])

if "expenses" not in st.session_state:
    st.session_state.expenses = pd.DataFrame(columns=[
        "Date", "Category", "Description", "Amount"
    ])


def get_business_context():
    products = st.session_state.products
    sales = st.session_state.sales
    expenses = st.session_state.expenses

    revenue = float(sales["Revenue"].sum()) if not sales.empty else 0.0
    profit = float(sales["Profit"].sum()) if not sales.empty else 0.0
    expense_total = float(expenses["Amount"].sum()) if not expenses.empty else 0.0
    inventory_units = float(products["Stock"].sum()) if not products.empty else 0.0

    low_stock = products[products["Stock"] <= products["Reorder Level"]] if not products.empty else pd.DataFrame()
    top_product = None
    if not sales.empty:
        product_totals = sales.groupby("Product", as_index=False)["Qty"].sum()
        if not product_totals.empty:
            top_product = product_totals.sort_values("Qty", ascending=False).iloc[0].to_dict()

    today_sales = sales[sales["Date"] == str(date.today())] if not sales.empty else pd.DataFrame()
    today_revenue = float(today_sales["Revenue"].sum()) if not today_sales.empty else 0.0
    today_profit = float(today_sales["Profit"].sum()) if not today_sales.empty else 0.0

    category_totals = None
    if not expenses.empty:
        category_totals = expenses.groupby("Category")["Amount"].sum().sort_values(ascending=False).to_dict()

    return {
        "revenue": revenue,
        "profit": profit,
        "expense_total": expense_total,
        "net_profit": profit - expense_total,
        "inventory_units": inventory_units,
        "low_stock": low_stock,
        "top_product": top_product,
        "today_revenue": today_revenue,
        "today_profit": today_profit,
        "category_totals": category_totals,
    }


def build_rule_based_ai_response(prompt: str) -> str:
    context = get_business_context()
    lower_prompt = prompt.lower()

    sales = st.session_state.sales
    products = st.session_state.products
    expenses = st.session_state.expenses

    if any(word in lower_prompt for word in ["good morning", "morning", "hello", "hi"]):
        return (
            f"Good morning. Today your revenue is PKR {context['today_revenue']:,.0f}, "
            f"profit is PKR {context['today_profit']:,.0f}, and inventory units are {context['inventory_units']:,.0f}."
        )

    if any(word in lower_prompt for word in ["sales", "sell", "revenue", "today sales", "سیل", "فروخت"]):
        if sales.empty:
            return "No sales have been recorded yet. Add your first sale from POS to generate insights."
        return (
            f"Total sales revenue is PKR {context['revenue']:,.0f}. "
            f"Today’s sales revenue is PKR {context['today_revenue']:,.0f}. "
            f"Gross profit is PKR {context['profit']:,.0f}."
        )

    if any(word in lower_prompt for word in ["profit", "nuksan", "margin", "net profit", "کتنا profit", "profit ہوا"]):
        return (
            f"Current gross profit is PKR {context['profit']:,.0f}. "
            f"Net profit after expenses is PKR {context['net_profit']:,.0f}."
        )

    if any(word in lower_prompt for word in ["low stock", "reorder", "stock alert", "needs reorder", "low stock report", "لو اسٹاک", "ریآرڈر"]):
        if products.empty:
            return "There are no products in inventory yet. Add products to track stock levels."
        if context["low_stock"].empty:
            return "No products currently need reordering. Stock levels are healthy."
        rows = []
        for _, item in context["low_stock"].iterrows():
            rows.append(f"{item['Product Name']} ({item['Size']}) — {int(item['Stock'])} left, reorder at {int(item['Reorder Level'])}")
        return "Low stock alert: " + "; ".join(rows)

    if any(word in lower_prompt for word in ["expense", "expenses", "cost", "اخراجات", "خرچہ"]):
        if expenses.empty:
            return "No expenses have been recorded yet."
        if context["category_totals"]:
            summary = "; ".join(f"{k}: PKR {v:,.0f}" for k, v in context["category_totals"].items())
            return f"Expense summary: {summary}. Total expenses: PKR {context['expense_total']:,.0f}."
        return f"Total expenses are PKR {context['expense_total']:,.0f}."

    if any(word in lower_prompt for word in ["top product", "best seller", "most sold", "popular", "زیادہ فروخت", "بہترین"]):
        if sales.empty:
            return "No sales data is available yet to identify the top-selling product."
        if context["top_product"]:
            item = context["top_product"]
            return f"The top-selling product is {item['Product']} with {int(item['Qty'])} units sold."
        return "No product performance data is available yet."

    if any(word in lower_prompt for word in ["close", "business", "summary", "daily closing", "کلوز", "بند"]):
        return (
            f"Business close summary: Revenue PKR {context['revenue']:,.0f}, Gross profit PKR {context['profit']:,.0f}, "
            f"Expenses PKR {context['expense_total']:,.0f}, Net profit PKR {context['net_profit']:,.0f}, "
            f"Inventory units {context['inventory_units']:,.0f}."
        )

    return (
        "Here is your current business status: revenue PKR "
        f"{context['revenue']:,.0f}, profit PKR {context['profit']:,.0f}, expenses PKR {context['expense_total']:,.0f}, "
        f"net profit PKR {context['net_profit']:,.0f}, and low stock items {len(context['low_stock']) if not context['low_stock'].empty else 0}."
    )


def ask_business_ai(prompt: str) -> str:
    st.session_state.ai_error = ""
    api_key = get_openai_api_key()
    if api_key and OpenAI is not None:
        try:
            client = OpenAI(api_key=api_key, timeout=30.0, max_retries=1)
            context = get_business_context()
            context_text = (
                f"Revenue: PKR {context['revenue']:,.0f}\n"
                f"Gross Profit: PKR {context['profit']:,.0f}\n"
                f"Expenses: PKR {context['expense_total']:,.0f}\n"
                f"Net Profit: PKR {context['net_profit']:,.0f}\n"
                f"Inventory Units: {context['inventory_units']:,.0f}\n"
                f"Low stock count: {len(context['low_stock']) if not context['low_stock'].empty else 0}\n"
            )
            if context['top_product']:
                context_text += (
                    f"Top product: {context['top_product']['Product']} sold {int(context['top_product']['Qty'])} units\n"
                )

            completion = client.chat.completions.create(
                model=get_openai_model(),
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a business strategist for a clothing brand. Give concise, actionable advice in plain English. "
                            "Use the provided business context and answer the user's request directly."
                        ),
                    },
                    {
                        "role": "user",
                        "content": f"Business context:\n{context_text}\n\nUser request: {prompt}",
                    },
                ],
                temperature=0.5,
                max_tokens=300,
            )
            response = completion.choices[0].message.content
            if response:
                return response.strip()
        except Exception as error:
            st.session_state.ai_error = str(error)

    return build_rule_based_ai_response(prompt)


def render_ai_status():
    st.subheader("AI Feature Status")
    status_columns = st.columns(3)
    for index, (feature, enabled) in enumerate(AI_FEATURES.items()):
        status_columns[index % 3].metric(
            feature,
            "Active" if enabled else "Setup needed",
        )
    if LIVE_AI_ENABLED:
        st.success("Live OpenAI responses are active. Built-in business insights remain available as a fallback.")
    else:
        st.info("Built-in AI insights are active. Add OPENAI_API_KEY to enable live OpenAI responses.")


def generate_product_description(product: dict) -> str:
    name = product.get("Product Name", "This product")
    design = product.get("Design", "modern")
    fabric = product.get("Fabric", "premium fabric")
    colour = product.get("Colour", "stylish")
    size = product.get("Size", "standard")

    description = (
        f"{name} is a {design.lower()} outfit crafted from {fabric.lower()} with a {colour.lower()} finish. "
        f"Designed for a comfortable {size.lower()} fit, this piece blends elegance and everyday wearability."
    )

    api_key = get_openai_api_key()
    if api_key and OpenAI is not None:
        try:
            client = OpenAI(api_key=api_key)
            completion = client.chat.completions.create(
                model=get_openai_model(),
                messages=[
                    {
                        "role": "system",
                        "content": "Write a polished marketing product description for a clothing brand in 1-2 sentences.",
                    },
                    {
                        "role": "user",
                        "content": f"Product: {name}, design: {design}, fabric: {fabric}, colour: {colour}, size: {size}",
                    },
                ],
                temperature=0.6,
                max_tokens=120,
            )
            response = completion.choices[0].message.content
            if response:
                return response.strip()
        except Exception:
            pass

    return description


def forecast_sales_data():
    sales = st.session_state.sales
    if sales.empty:
        return {"forecast_revenue": 0.0, "trend": "No sales history yet", "avg_daily_revenue": 0.0}

    sales = sales.copy()
    sales["Date"] = pd.to_datetime(sales["Date"], errors="coerce")
    sales = sales.dropna(subset=["Date"])
    if sales.empty:
        return {"forecast_revenue": 0.0, "trend": "No valid sales history yet", "avg_daily_revenue": 0.0}

    daily = sales.groupby("Date")["Revenue"].sum().sort_index()
    if len(daily) == 1:
        avg_daily = float(daily.iloc[-1])
        forecast_revenue = avg_daily
        trend = "Stable"
    else:
        avg_daily = float(daily.tail(7).mean())
        recent = float(daily.tail(3).mean())
        previous = float(daily.head(3).mean()) if len(daily) >= 3 else recent
        forecast_revenue = avg_daily * 7
        if recent > previous:
            trend = "Upward trend"
        elif recent < previous:
            trend = "Downward trend"
        else:
            trend = "Stable"

    return {
        "forecast_revenue": forecast_revenue,
        "trend": trend,
        "avg_daily_revenue": avg_daily,
    }


def generate_whatsapp_summary():
    context = get_business_context()
    forecast = forecast_sales_data()
    low_count = len(context["low_stock"]) if not context["low_stock"].empty else 0
    summary = (
        "*Prime Pret Business Summary*\n"
        f"Revenue: PKR {context['revenue']:,.0f}\n"
        f"Gross profit: PKR {context['profit']:,.0f}\n"
        f"Expenses: PKR {context['expense_total']:,.0f}\n"
        f"Net profit: PKR {context['net_profit']:,.0f}\n"
        f"Low stock items: {low_count}\n"
        f"7-day forecast: PKR {forecast['forecast_revenue']:,.0f} ({forecast['trend']})"
    )
    return summary


def render_whatsapp_summary(summary: str):
    st.text_area(
        "WhatsApp message",
        value=summary,
        height=190,
        disabled=True,
        help="Select and copy this message, or open it directly in WhatsApp.",
    )
    share_url = f"https://wa.me/?text={quote(summary)}"
    share_col, download_col = st.columns(2)
    with share_col:
        st.link_button("Open in WhatsApp", share_url, use_container_width=True)
    with download_col:
        st.download_button(
            "Download summary",
            data=summary,
            file_name="prime_pret_business_summary.txt",
            mime="text/plain",
            use_container_width=True,
        )


def export_dataframe_csv(df: pd.DataFrame, filename: str):
    csv_data = df.to_csv(index=False)
    return st.download_button(
        "Download CSV",
        data=csv_data,
        file_name=filename,
        mime="text/csv",
    )


def voice_input_component():
    if "voice_prompt" not in st.session_state:
        st.session_state.voice_prompt = ""
    if "ai_prompt" not in st.session_state:
        st.session_state.ai_prompt = st.session_state.voice_prompt

    component_value = VOICE_INPUT_COMPONENT(key="prime_pret_voice_input")

    if isinstance(component_value, str) and component_value.strip():
        st.session_state.voice_prompt = component_value.strip()
        return st.session_state.voice_prompt
    return st.session_state.voice_prompt

# -----------------------------
# LOGIN SCREEN
# -----------------------------

if not st.session_state.authenticated:
    st.markdown(
        """
        <style>
        .login-shell {
            max-width: 520px;
            margin: 3rem auto 0 auto;
            background: linear-gradient(180deg, rgba(28, 23, 18, 0.96), rgba(13, 13, 13, 0.96));
            border: 1px solid rgba(214,169,92,0.45);
            border-radius: 22px;
            padding: 2rem;
            box-shadow: 0 18px 45px rgba(0,0,0,0.35);
        }
        .login-title {
            font-size: 2.1rem;
            font-weight: 800;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            color: #f3dfb3;
            margin-bottom: 0.5rem;
        }
        .login-subtitle {
            color: #d7b87b;
            margin-bottom: 1.5rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class='login-shell'>
            <div class='login-title'>Prime Pret</div>
            <div class='login-subtitle'>Luxury retail access portal</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("<br>", unsafe_allow_html=True)

    with st.form("login_form"):
        username = st.text_input("Username or employee code")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Sign In")

        if submitted:
            user = authenticate_user(username, password)
            if user:
                st.session_state.authenticated = True
                st.session_state.username = user["username"]
                st.session_state.employee_code = user["employee_code"]
                st.session_state.user_role = user["role"]
                st.session_state.user_access = user["access"]
                st.session_state.login_error = ""
                st.rerun()
            else:
                st.session_state.login_error = "Invalid username or password. Please try again."

    if st.session_state.login_error:
        st.error(st.session_state.login_error)

    st.stop()

current_refresh_token = get_app_state_value(f"business_data_updated:{st.session_state.username}", "")
if st.session_state.get("business_data_owner") != st.session_state.username or st.session_state.get("business_data_last_updated") != current_refresh_token:
    load_business_data(st.session_state.username)
    st.session_state.business_data_owner = st.session_state.username
    st.session_state.business_data_last_updated = current_refresh_token

auto_refresh_component(10)

# -----------------------------
# SIDEBAR
# -----------------------------

if logo_asset:
    try:
        st.sidebar.image(logo_asset, width=220)
    except Exception:
        st.sidebar.markdown("<div style='text-align:center; color:#d8b36a; font-weight:700; font-size:1.2rem;'>Prime Pret</div>", unsafe_allow_html=True)
else:
    st.sidebar.markdown("<div style='text-align:center; color:#d8b36a; font-weight:700; font-size:1.2rem;'>Prime Pret</div>", unsafe_allow_html=True)

st.sidebar.markdown("<div style='text-align:center; color:#d8b36a; letter-spacing:0.18em; font-size:0.72rem; text-transform:uppercase; margin-top:8px; margin-bottom:16px;'>AI Retail Command</div>", unsafe_allow_html=True)
st.sidebar.write(f"Signed in as: **{st.session_state.username or 'User'}**")
st.sidebar.write(f"Role: **{st.session_state.user_role or 'User'}**")
if st.session_state.get("employee_code"):
    st.sidebar.write(f"Employee code: **{st.session_state.employee_code}**")

with st.sidebar.expander("Settings"):
    st.session_state.keyboard_shortcuts_enabled = st.checkbox(
        "Show keyboard shortcuts",
        value=st.session_state.keyboard_shortcuts_enabled,
    )
    if st.session_state.keyboard_shortcuts_enabled:
        st.caption("Edit shortcut keys")
        shortcut_options = [str(number) for number in range(1, 10)]
        for page_name in st.session_state.shortcut_bindings:
            st.session_state.shortcut_bindings[page_name] = st.selectbox(
                page_name,
                shortcut_options,
                index=shortcut_options.index(st.session_state.shortcut_bindings[page_name]),
                key=f"shortcut_{page_name.lower().replace(' ', '_')}",
            )
        if st.button("Reset shortcuts", key="reset_shortcuts"):
            st.session_state.shortcut_bindings = {
                "Dashboard": "1",
                "POS": "2",
                "Products": "3",
                "Sales": "4",
                "AI Manager": "5",
            }
            st.rerun()

    shortcut_keys = list(st.session_state.shortcut_bindings.values())
    shortcuts_are_unique = len(shortcut_keys) == len(set(shortcut_keys))
    if not shortcuts_are_unique:
        st.warning("Each shortcut must use a different key.")

keyboard_shortcuts_component(
    st.session_state.keyboard_shortcuts_enabled and shortcuts_are_unique,
    st.session_state.shortcut_bindings,
)

if is_administrator():
    with st.sidebar.expander("Change brand logo"):
        logo_upload = st.file_uploader(
            "Upload logo",
            type=["png", "jpg", "jpeg", "webp", "svg"],
            key="admin_logo_upload",
        )
        if st.button("Apply new logo", key="apply_logo"):
            if logo_upload is None:
                st.warning("Choose a logo file first.")
            else:
                logo_path = APP_DIR / "assets" / "Logo"
                logo_path.write_bytes(logo_upload.getvalue())
                st.success("Brand logo updated. Refreshing...")
                st.rerun()

if st.session_state.get("user_role") in ("Administrator", "Store Manager"):
    with st.sidebar.expander("Change password"):
        with st.form("change_password_form"):
            current_password = st.text_input("Current password", type="password")
            new_password = st.text_input("New password", type="password")
            confirm_password = st.text_input("Confirm new password", type="password")
            change_password = st.form_submit_button("Update password")

            if change_password:
                username = st.session_state.username.lower()
                account = get_account(username)
                current_password_valid = account and verify_password(
                    current_password,
                    account[2],
                    account[1],
                )
                if not current_password_valid:
                    st.error("Current password is incorrect.")
                elif len(new_password) < 8:
                    st.error("New password must be at least 8 characters.")
                elif new_password != confirm_password:
                    st.error("New passwords do not match.")
                elif new_password == current_password:
                    st.error("New password must be different from the current password.")
                else:
                    update_account_password(username, new_password)
                    st.success("Password updated for all sessions.")

if st.sidebar.button("Logout"):
    st.session_state.authenticated = False
    st.session_state.username = ""
    st.session_state.employee_code = ""
    st.session_state.user_role = ""
    st.session_state.user_access = []
    st.session_state.login_error = ""
    st.rerun()

allowed_pages = get_allowed_pages()
page = st.sidebar.radio(
    "Menu",
    allowed_pages,
    key="sidebar_page",
    on_change=sync_mobile_page,
)

if "mobile_page" not in st.session_state or st.session_state.mobile_page not in allowed_pages:
    st.session_state.mobile_page = page

with st.container(key="mobile-navigation"):
    st.markdown("#### Menu")
    page = st.selectbox(
        "Choose a page",
        allowed_pages,
        key="mobile_page",
        label_visibility="collapsed",
    )

if page not in allowed_pages:
    page = "🏠 Dashboard"

# -----------------------------
# DASHBOARD
# -----------------------------

if page == "🏠 Dashboard":

    st.markdown('<div class="luxury-tag">PREMIUM RETAIL INTELLIGENCE</div>', unsafe_allow_html=True)
    st.markdown('<div class="brand-header">👗 Prime Pret POS</div>', unsafe_allow_html=True)
    dashboard_subheader = "Luxury fashion business dashboard for sales, stock, and growth decisions." if is_cashier() else "Luxury fashion business dashboard for sales, stock, profit, and growth decisions."
    st.markdown(f'<div class="brand-subheader">{dashboard_subheader}</div>', unsafe_allow_html=True)

    products = st.session_state.products
    sales = st.session_state.sales
    expenses = st.session_state.expenses

    revenue = sales["Revenue"].sum() if not sales.empty else 0
    profit = sales["Profit"].sum() if not sales.empty else 0
    stock = products["Stock"].sum() if not products.empty else 0

    reorder = 0

    if not products.empty:
        reorder = len(
            products[
                products["Stock"] <= products["Reorder Level"]
            ]
        )

    if is_cashier():
        c1, c2, c3 = st.columns(3)
        c1.metric("Today's Revenue", f"PKR {revenue:,.0f}")
        c2.metric("Inventory Units", f"{stock:,.0f}")
        c3.metric("Low Stock Items", reorder)
    else:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Today's Revenue", f"PKR {revenue:,.0f}")
        c2.metric("Gross Profit", f"PKR {profit:,.0f}")
        c3.metric("Inventory Units", f"{stock:,.0f}")
        c4.metric("Low Stock Items", reorder)

    st.divider()

    st.subheader("📈 Business Overview")

    if sales.empty:
        st.info("No sales recorded yet.")
    else:
        chart = sales.groupby("Date")["Revenue"].sum()
        st.line_chart(chart)

    forecast = forecast_sales_data()
    f1, f2, f3 = st.columns(3)
    f1.metric("7-Day Forecast", f"PKR {forecast['forecast_revenue']:,.0f}")
    f2.metric("Avg Daily Revenue", f"PKR {forecast['avg_daily_revenue']:,.0f}")
    f3.metric("Trend", forecast["trend"])

    st.subheader("📱 WhatsApp Business Summary")
    whatsapp_summary = generate_whatsapp_summary()
    if is_cashier():
        whatsapp_summary = (
            f"Prime Pret POS update: Revenue PKR {revenue:,.0f}. "
            f"Inventory units: {stock:,.0f}. Low stock items: {reorder}."
        )
    render_whatsapp_summary(whatsapp_summary)

    st.subheader("⚠️ Low Stock Alerts")

    if products.empty:
        st.info("Add products first.")
    else:
        low = products[
            products["Stock"] <= products["Reorder Level"]
        ]

        if low.empty:
            st.success("All products have sufficient stock.")
        else:
            st.dataframe(low, width="stretch")

# -----------------------------
# PRODUCTS
# -----------------------------

elif page == "📦 Products":

    st.title("📦 Product / Inventory Manager")

    with st.form("product_form"):

        c1, c2, c3 = st.columns(3)

        barcode = c1.text_input("Barcode")
        product_id = c2.text_input("Product ID")
        name = c3.text_input("Product Name")

        design = c1.text_input("Design")
        fabric = c2.text_input("Fabric")
        colour = c3.text_input("Colour")

        size = c1.selectbox(
            "Size",
            ["XS", "S", "M", "L", "XL", "XXL", "Free Size"]
        )

        cost = c2.number_input(
            "Cost Price",
            min_value=0.0,
            step=50.0
        )

        selling = c3.number_input(
            "Selling Price",
            min_value=0.0,
            step=50.0
        )

        stock = c1.number_input(
            "Opening Stock",
            min_value=0,
            step=1
        )

        reorder = c2.number_input(
            "Reorder Level",
            min_value=0,
            value=5,
            step=1
        )

        product_image = c3.file_uploader(
            "Product Photo",
            type=["png", "jpg", "jpeg", "webp"]
        )

        submitted = st.form_submit_button(
            "➕ Add Product"
        )

        if submitted:
            image_path = ""
            if product_image is not None:
                safe_name = (product_id or barcode or "product").replace(" ", "_")
                image_file = f"product_images/{safe_name}_{product_image.name}"
                with open(image_file, "wb") as file:
                    file.write(product_image.getvalue())
                image_path = image_file

            new_product = pd.DataFrame([{
                "Barcode": barcode,
                "Product ID": product_id,
                "Product Name": name,
                "Design": design,
                "Fabric": fabric,
                "Colour": colour,
                "Size": size,
                "Cost Price": cost,
                "Selling Price": selling,
                "Stock": stock,
                "Reorder Level": reorder,
                "Image Path": image_path
            }])

            st.session_state.products = pd.concat(
                [
                    st.session_state.products,
                    new_product
                ],
                ignore_index=True
            )
            save_business_data()

            st.success("Product added successfully!")

    st.divider()

    st.subheader("📋 Inventory")

    export_dataframe_csv(st.session_state.products, "products.csv")

    st.dataframe(
        st.session_state.products,
        width="stretch"
    )

    if not st.session_state.products.empty:
        st.subheader("📷 Product Photos")
        cols = st.columns(3)
        for idx, item in st.session_state.products.iterrows():
            with cols[idx % 3]:
                description = generate_product_description(item.to_dict())
                render_product_image(item.get("Image Path", ""), item["Product Name"])
                st.caption(description)

# -----------------------------
# POS
# -----------------------------

elif page == "🛒 POS":

    st.title("🛒 POS ")

    products = st.session_state.products

    if products.empty:
        st.warning("Please add products first.")
    else:

        barcode = st.text_input(
            "Scan Barcode"
        )

        product = products[
            products["Barcode"].astype(str) == str(barcode)
        ]

        if not product.empty:

            item = product.iloc[0]

            st.success(
                f"Product Found: {item['Product Name']}"
            )

            c1, c2, c3 = st.columns(3)

            c1.write(f"**Size:** {item['Size']}")
            c2.write(f"**Colour:** {item['Colour']}")
            c3.write(
                f"**Price:** PKR {item['Selling Price']:,.0f}"
            )

            qty = st.number_input(
                "Quantity",
                min_value=1,
                value=1
            )

            discount = st.number_input(
                "Discount",
                min_value=0.0,
                value=0.0
            )

            revenue = (
                item["Selling Price"] * qty
            ) - discount

            cost = item["Cost Price"] * qty

            profit = revenue - cost

            st.metric(
                "Total",
                f"PKR {revenue:,.0f}"
            )

            if not is_cashier():
                st.metric("Profit", f"PKR {profit:,.0f}")

            amount_paid = st.number_input(
                "Amount Paid by Customer",
                min_value=0.0,
                value=float(revenue),
                step=50.0,
            )
            change = amount_paid - revenue
            st.metric("Change for Customer", f"PKR {max(change, 0):,.0f}")

            if st.button("💾 Complete Sale"):
                if amount_paid < revenue:
                    st.error(f"Amount paid is short by PKR {revenue - amount_paid:,.0f}.")
                else:
                    invoice = f"INV-{len(st.session_state.sales)+1:05d}"

                    new_sale = pd.DataFrame([{
                        "Date": str(date.today()),
                        "Invoice": invoice,
                        "Barcode": barcode,
                        "Product": item["Product Name"],
                        "Qty": qty,
                        "Selling Price": item["Selling Price"],
                        "Discount": discount,
                        "Revenue": revenue,
                        "Cost": cost,
                        "Profit": profit,
                        "Amount Paid": amount_paid,
                        "Change": change,
                    }])

                    st.session_state.sales = pd.concat(
                        [st.session_state.sales, new_sale],
                        ignore_index=True
                    )

                    idx = product.index[0]
                    st.session_state.products.loc[idx, "Stock"] -= qty
                    save_business_data()

                    st.success(f"Sale completed! Invoice: {invoice}. Change: PKR {change:,.0f}")

        elif barcode:
            st.error("Barcode not found.")

# -----------------------------
# PROFIT CALCULATOR
# -----------------------------

elif page == "💰 Profit Calculator":

    st.title("💰 Profit Calculator")

    c1, c2 = st.columns(2)

    fabric = c1.number_input(
        "Fabric Cost", min_value=0.0
    )

    stitching = c2.number_input(
        "Stitching Cost", min_value=0.0
    )

    embroidery = c1.number_input(
        "Embroidery / Designing", min_value=0.0
    )

    packaging = c2.number_input(
        "Packaging", min_value=0.0
    )

    transport = c1.number_input(
        "Transport", min_value=0.0
    )

    other = c2.number_input(
        "Other Cost", min_value=0.0
    )

    selling = st.number_input(
        "Selling Price", min_value=0.0
    )

    discount = st.number_input(
        "Discount", min_value=0.0
    )

    total_cost = (
        fabric +
        stitching +
        embroidery +
        packaging +
        transport +
        other
    )

    net_price = selling - discount
    profit = net_price - total_cost

    margin = (
        profit / net_price * 100
        if net_price > 0 else 0
    )

    st.divider()

    c1, c2, c3 = st.columns(3)

    c1.metric(
        "Total Cost",
        f"PKR {total_cost:,.0f}"
    )

    c2.metric(
        "Profit",
        f"PKR {profit:,.0f}"
    )

    c3.metric(
        "Margin",
        f"{margin:.1f}%"
    )

    st.subheader("Suggested Selling Prices")

    for target in [20, 30, 40, 50]:

        suggested = (
            total_cost /
            (1 - target / 100)
        )

        st.write(
            f"{target}% margin → "
            f"**PKR {suggested:,.0f}**"
        )

# -----------------------------
# SALES
# -----------------------------

elif page == "📊 Sales":

    st.title("📊 Sales Reports")

    sales = st.session_state.sales

    if sales.empty:
        st.info("No sales yet.")
    else:
        sales_for_display = sales.drop(columns=["Profit", "Cost"], errors="ignore") if is_cashier() else sales
        export_dataframe_csv(sales_for_display, "sales.csv")

        st.dataframe(
            sales_for_display,
            width="stretch"
        )

        st.subheader("Totals")

        if is_cashier():
            st.metric("Revenue", f"PKR {sales['Revenue'].sum():,.0f}")
        else:
            c1, c2 = st.columns(2)
            c1.metric("Revenue", f"PKR {sales['Revenue'].sum():,.0f}")
            c2.metric("Profit", f"PKR {sales['Profit'].sum():,.0f}")

# -----------------------------
# LOW STOCK
# -----------------------------

elif page == "⚠️ Low Stock":

    st.title("⚠️ Low Stock Alerts")

    products = st.session_state.products

    if products.empty:
        st.info("No products available.")
    else:

        low = products[
            products["Stock"] <= products["Reorder Level"]
        ]

        if low.empty:
            st.success(
                "No products require reordering."
            )
        else:

            st.warning(
                f"{len(low)} product(s) need attention."
            )

            st.dataframe(
                low,
                width="stretch"
            )

# -----------------------------
# EXPENSES
# -----------------------------

elif page == "💸 Expenses":

    st.title("💸 Business Expenses")

    with st.form("expense_form"):

        category = st.selectbox(
            "Category",
            [
                "Rent",
                "Electricity",
                "Transport",
                "Packaging",
                "Marketing",
                "Salary",
                "Other"
            ]
        )

        description = st.text_input(
            "Description"
        )

        amount = st.number_input(
            "Amount",
            min_value=0.0
        )

        submit = st.form_submit_button(
            "Add Expense"
        )

        if submit:

            new_expense = pd.DataFrame([{
                "Date": str(date.today()),
                "Category": category,
                "Description": description,
                "Amount": amount
            }])

            st.session_state.expenses = pd.concat(
                [
                    st.session_state.expenses,
                    new_expense
                ],
                ignore_index=True
            )
            save_business_data()

            st.success("Expense added.")

    export_dataframe_csv(st.session_state.expenses, "expenses.csv")

    st.dataframe(
        st.session_state.expenses,
        width="stretch"
    )

# -----------------------------
# ADD MANAGER
# -----------------------------

elif page == "➕ Add Manager":

    st.title("➕ Add Manager")
    st.write("Create a new store manager account for your business.")

    with st.form("add_manager_page_form"):
        new_manager_username = st.text_input("Username")
        new_manager_password = st.text_input("Password", type="password")
        confirm_manager_password = st.text_input("Confirm password", type="password")
        add_manager = st.form_submit_button("Add manager")

        if add_manager:
            created, message = create_manager_account(
                new_manager_username,
                new_manager_password,
                confirm_manager_password,
            )
            if created:
                st.success(f"Manager account '{message}' created.")
                st.rerun()
            else:
                st.error(message)

# -----------------------------
# ADD CASHIER
# -----------------------------

elif page == "➕ Add Cashier":

    st.title("➕ Add Cashier")
    st.write("Create a new cashier account for your store.")

    with st.form("add_cashier_page_form"):
        new_cashier_username = st.text_input("Username")
        new_cashier_password = st.text_input("Password", type="password")
        confirm_cashier_password = st.text_input("Confirm password", type="password")
        add_cashier = st.form_submit_button("Add cashier")

        if add_cashier:
            created, message = create_cashier_account(
                new_cashier_username,
                new_cashier_password,
                confirm_cashier_password,
            )
            if created:
                st.success(f"Cashier account '{message}' created.")
                st.rerun()
            else:
                st.error(message)

# CASHIER MANAGEMENT
# -----------------------------

elif page == "👥 Cashier Management":

    st.title("👥 Cashier Management")
    st.write("Review each cashier's separate inventory, sales, and expenses.")

    cashier_accounts = get_cashier_accounts()
    if not cashier_accounts:
        st.info("No cashier accounts are configured.")
    else:
        cashier_options = {
            f"{account[0]} ({account[2]})": account[0]
            for account in cashier_accounts
        }
        selected_cashier_label = st.selectbox("Select cashier", list(cashier_options))
        selected_cashier = cashier_options[selected_cashier_label]
        cashier_data = get_cashier_data(selected_cashier)
        products = cashier_data["products"]
        sales = cashier_data["sales"]
        expenses = cashier_data["expenses"]

        metric_one, metric_two, metric_three, metric_four = st.columns(4)
        metric_one.metric("Inventory Units", int(products["Stock"].sum()) if "Stock" in products else 0)
        metric_two.metric("Products", len(products))
        metric_three.metric("Sales Revenue", f"PKR {sales['Revenue'].sum():,.0f}" if "Revenue" in sales else "PKR 0")
        metric_four.metric("Expenses", f"PKR {expenses['Amount'].sum():,.0f}" if "Amount" in expenses else "PKR 0")

        with st.expander(f"Add product for {selected_cashier}"):
            with st.form("cashier_product_form"):
                product_col_one, product_col_two, product_col_three = st.columns(3)
                cashier_barcode = product_col_one.text_input("Barcode")
                cashier_product_id = product_col_two.text_input("Product ID")
                cashier_product_name = product_col_three.text_input("Product Name")
                cashier_design = product_col_one.text_input("Design")
                cashier_fabric = product_col_two.text_input("Fabric")
                cashier_colour = product_col_three.text_input("Colour")
                cashier_size = product_col_one.selectbox(
                    "Size",
                    ["XS", "S", "M", "L", "XL", "XXL", "Free Size"],
                    key="cashier_product_size",
                )
                cashier_cost = product_col_two.number_input("Cost Price", min_value=0.0, step=50.0, key="cashier_cost")
                cashier_selling = product_col_three.number_input("Selling Price", min_value=0.0, step=50.0, key="cashier_selling")
                cashier_stock = product_col_one.number_input("Opening Stock", min_value=0, step=1, key="cashier_stock")
                cashier_reorder = product_col_two.number_input("Reorder Level", min_value=0, value=5, step=1, key="cashier_reorder")
                cashier_image = product_col_three.file_uploader(
                    "Product Photo",
                    type=["png", "jpg", "jpeg", "webp"],
                    key="cashier_product_image",
                )
                add_cashier_product = st.form_submit_button("Add to cashier inventory")

                if add_cashier_product:
                    if not cashier_product_name.strip():
                        st.error("Product Name is required.")
                    else:
                        image_path = ""
                        if cashier_image is not None:
                            safe_name = "".join(
                                character for character in (cashier_product_id or cashier_barcode or "product")
                                if character.isalnum() or character in ("-", "_")
                            )
                            safe_filename = "".join(
                                character for character in cashier_image.name
                                if character.isalnum() or character in ("-", "_", ".")
                            )
                            image_path = f"product_images/{safe_name}_{safe_filename}"
                            (APP_DIR / image_path).write_bytes(cashier_image.getvalue())

                        new_cashier_product = pd.DataFrame([{
                            "Barcode": cashier_barcode,
                            "Product ID": cashier_product_id,
                            "Product Name": cashier_product_name,
                            "Design": cashier_design,
                            "Fabric": cashier_fabric,
                            "Colour": cashier_colour,
                            "Size": cashier_size,
                            "Cost Price": cashier_cost,
                            "Selling Price": cashier_selling,
                            "Stock": cashier_stock,
                            "Reorder Level": cashier_reorder,
                            "Image Path": image_path,
                        }])
                        cashier_data["products"] = pd.concat(
                            [cashier_data["products"], new_cashier_product],
                            ignore_index=True,
                        )
                        save_scoped_business_data(selected_cashier, cashier_data)
                        st.success(f"Product added to {selected_cashier}'s inventory.")
                        st.rerun()

        st.subheader("Inventory")
        st.dataframe(products, width="stretch")
        st.subheader("Sales")
        st.dataframe(sales, width="stretch")
        st.subheader("Expenses")
        st.dataframe(expenses, width="stretch")

        with st.expander("Change cashier username or password"):
            with st.form("cashier_credentials_form"):
                new_username = st.text_input("New username", value=selected_cashier)
                new_password = st.text_input("New password", type="password")
                confirm_password = st.text_input("Confirm new password", type="password")
                update_credentials = st.form_submit_button("Save cashier credentials")

                if update_credentials:
                    if new_password != confirm_password:
                        st.error("Passwords do not match.")
                    else:
                        updated, message = update_cashier_credentials(
                            selected_cashier,
                            new_username,
                            new_password,
                        )
                        if updated:
                            st.success("Cashier username and password updated.")
                            st.rerun()
                        else:
                            st.error(message)

# -----------------------------
# AI MANAGER
# -----------------------------

elif page == "🤖 AI Manager":

    st.markdown('<div class="luxury-tag">AI BUSINESS DIRECTOR</div>', unsafe_allow_html=True)
    st.markdown('<div class="brand-header">🤖 Prime Pret POS</div>', unsafe_allow_html=True)
    st.markdown('<div class="brand-subheader">English + اردو + Roman Urdu • strategic retail guidance</div>', unsafe_allow_html=True)

    render_ai_status()

    st.write(
        """
        **Manager Commands / مینیجر کمانڈز**

        • Good morning manager
        • آج کی سیل بتاؤ
        • Low stock report
        • آج کتنا profit ہوا؟
        • کون سی Kurti زیادہ فروخت ہوئی؟
        • Which products need reorder?
        • آج کے expenses کیا ہیں؟
        • Close today's business
        """
    )

    st.divider()

    products = st.session_state.products
    sales = st.session_state.sales
    expenses = st.session_state.expenses

    revenue = sales["Revenue"].sum() if not sales.empty else 0
    profit = sales["Profit"].sum() if not sales.empty else 0
    expense_total = expenses["Amount"].sum() if not expenses.empty else 0

    if "voice_prompt" not in st.session_state:
        st.session_state.voice_prompt = ""

    st.subheader("📋 Manager Briefing")

    st.write(
        f"""
        **Sales Revenue:** PKR {revenue:,.0f}

        **Gross Profit:** PKR {profit:,.0f}

        **Expenses:** PKR {expense_total:,.0f}

        **Net Profit Estimate:** PKR {profit-expense_total:,.0f}

        **Inventory Units:** {products["Stock"].sum() if not products.empty else 0}

        **Low Stock Items:** {
            len(products[products["Stock"] <= products["Reorder Level"]])
            if not products.empty else 0
        }
        """
    )

    st.divider()

    st.write("#### 🎙️ Voice Input")
    voice_value = voice_input_component()
    if isinstance(voice_value, str) and voice_value.strip():
        st.session_state.voice_prompt = voice_value
        st.session_state.ai_prompt = voice_value

    prompt = st.text_input(
        "Ask the AI manager",
        key="ai_prompt",
        placeholder="Example: Low stock report, sales summary, profit analysis, today expenses",
    )

    if st.button("Generate AI Insight") and prompt.strip():
        with st.spinner("Analyzing your business data..."):
            answer = ask_business_ai(prompt)
        st.success("AI insight ready")
        st.markdown(f"### Response\n{answer}")
        if st.session_state.get("ai_error"):
            st.warning(
                "Live OpenAI request failed, so the built-in business response was used. "
                f"Details: {st.session_state.ai_error}"
            )

    if st.button("Generate WhatsApp Summary"):
        st.session_state.whatsapp_summary = generate_whatsapp_summary()
    if st.session_state.get("whatsapp_summary"):
        render_whatsapp_summary(st.session_state.whatsapp_summary)

    st.caption("AI features use your sales, inventory, and expense data. Live OpenAI responses require OPENAI_API_KEY; all other features work locally.")

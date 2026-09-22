# AI-Sales-Assistant

Prime Pret POS is a Streamlit AI retail manager for clothing brands.

## AI features

- Business questions about sales, profit, expenses, and low stock
- AI-generated product descriptions
- Seven-day sales forecasting
- WhatsApp-ready business summaries
- Browser voice input for manager prompts
- Built-in rule-based fallback when no API key is configured
- Optional live OpenAI responses when `OPENAI_API_KEY` is configured

## Run locally

```bash
python3 -m pip install -r requirements.txt
cp .env.example .env
streamlit run app.py
```

Enter your OpenAI key in `.env` to activate live responses. The app never requires the key for local AI features.

Only the `admin` account can access **Change brand logo** and **Change password** in the sidebar. Enter the current password and a new password of at least 8 characters. Password changes are stored in the local `accounts.db` database and apply across all login sessions and app restarts.

Products, sales, inventory stock, and expenses are also stored in `accounts.db`. New records remain available after refreshes, restarts, and across hosts that use the same shared application directory.

Each account has an isolated workspace. The four cashier accounts are `cashier1`, `cashier2`, `cashier3`, and `cashier4`; each account sees and stores its own products, inventory, sales, and expenses.

Administrators and Store Managers can open **Add Cashier** to create cashier accounts. They can use **Cashier Management** to review every cashier's records and update cashier usernames and passwords. Renaming a cashier preserves that cashier's existing data.

## Mobile and APK

The interface is responsive for phones and tablets. Run the Streamlit server on a reachable host, then open its URL in a mobile browser.

Streamlit cannot be compiled directly into a standalone Android APK. To publish an APK, deploy this app to a server and wrap its HTTPS URL in an Android WebView or Trusted Web Activity. The APK must be able to reach that hosted URL and the shared `accounts.db` storage.

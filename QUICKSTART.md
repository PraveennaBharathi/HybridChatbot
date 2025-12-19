# ⚡ Quick Start Guide

Get up and running in 5 minutes!

---

## 🚀 3-Step Setup

### Step 1: Install Dependencies (2 min)

```bash
pip install -r requirements.txt
```

### Step 2: Add API Key (1 min)

Create `.env` file:
```bash
GOOGLE_API_KEY=your_gemini_api_key_here
```

Get free API key: https://ai.google.dev/

### Step 3: Launch App (30 sec)

```bash
streamlit run app.py
```

Open browser: http://localhost:8501

---

## ✅ That's It!

The app will automatically:
- ✅ Initialize the database
- ✅ Load vector store
- ✅ Set up the chatbot

---

## 💬 Try These Questions

**Quantitative (SQL):**
```
What is Apple's revenue?
Compare Tesla and NVIDIA
Which company has highest P/E ratio?
```

**Qualitative (RAG):**
```
What are Microsoft's AI initiatives?
Explain Apple's business strategy
What challenges is Meta facing?
```

---

## 🆘 Troubleshooting

**API Key Error?**
- Check `.env` file exists
- Verify key format: `GOOGLE_API_KEY=AIza...`

**Port Already in Use?**
```bash
streamlit run app.py --server.port 8502
```

---

**Enjoy your Hybrid Financial Chatbot!** 🎉

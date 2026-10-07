# Campus Customs — Usability Improvements

Four improvements: two on the frontend (look and ease of use) and two in the
agent/backend (accuracy and better answers). Each one is in the running app.
"Where to see it" says exactly how to find it.

| # | Improvement | Type | Where to see it |
|---|---|---|---|
| 1 | Filter & sort bar on the Products page | Frontend | `/products` (or click a "Shop by style" tile on Home) |
| 2 | Suggested questions in the chat + "Ask about this item" | Frontend | Open the chat on any page; product pages have an **💬 Ask about this item** button |
| 3 | Price & stock accuracy check | Agent / backend | Any chat answer with a price or stock count shows **✓ Prices & stock checked against live inventory** |
| 4 | `find_alternatives` tool for sold-out sizes | Agent / backend | Ask "Do you have the Football Left Chest T Shirt in a medium?" or "Show me similar items" on a product page |

---

## 1. Filter & sort bar on the Products page (frontend)

**What we added**
- A bar above the product grid (`frontend/src/components/FilterBar.tsx`) with:
  - **Category chips** with counts: All 102 · Hoodies 27 · Sweatshirts 29 ·
    Tees 25 · Quarter-zips 11 · Jackets 8 · Long sleeve 2. Click one to
    filter, click again to clear.
  - **"Has my size"**: only items with stock in XS–XXL.
  - **"In stock only"** toggle.
  - **Sort**: Featured, Price low→high, Price high→low, Name A–Z.
  - **Clear filters** link (also shown when nothing matches).
- The Home page "Shop by style" tiles now open the Products page with that
  category already selected (`/products?category=hoodie`).
- The same bar works on **chat search results**. After the chat shows "Navy
  gear" (80 items), the shopper can click Quarter-zips → 6 items, or sort by
  price.
- To support it, the products API now returns each item's `category` (the 22
  messy `garment_type` values grouped into 6) and `sizes_in_stock`.

**Why it helps**
- **Shoppers:** before, 102 products sat in one grid with only a text box.
  Now "hoodies in my size, cheapest first" is two clicks:
  Hoodies → XL in stock → Price low→high gives 21 hoodies, starting at
  $45.00 (21 matches the database). The size filter matters because 145 of
  612 size slots are sold out. Shoppers no longer click into an item only to
  find their size gone.
- **Business:** shoppers who can quickly find something in their size are
  more likely to buy. It also takes simple browsing questions off the chatbot,
  which costs money per message.

## 2. Suggested questions in the chat + "Ask about this item" (frontend)

**What we added**
- **One-click suggestion chips** above the chat input
  (`frontend/src/suggestions.ts`, `ChatWidget.tsx`), chosen for the page:
  - Most pages: "What hoodies do you have?", "Gift ideas under $50", "Tees
    in stock in XL".
  - Product page: "Which sizes are in stock?", "What colors does this come
    in?", "Show me similar items".
  - Chat results page: "Which of these is cheapest?", "Which of these are in
    stock in M?", "Only ones under $50".
  - Clicking a chip sends it right away. The chips hide while the shopper is
    typing or waiting for a reply.
- An **"💬 Ask about this item"** panel under the size table on every product
  page opens the chat with that product's suggestions. Because the chat
  already knows the current page (Problem 8), "Which sizes are in stock?"
  answers about that exact item.
- The chat's open/closed state moved into a small shared context
  (`frontend/src/chatUi.tsx`), so any page can open the chat.

**Why it helps**
- **Shoppers:** an empty chat box doesn't say what it can do. The chips
  show what to ask and get an answer in one click, which matters most on
  mobile.
- **Business:** more shoppers actually use the assistant. The suggested
  questions are worded the way the agent handles best (they map straight to
  its search, stock and alternatives tools), so answers are more reliable.

## 3. Price & stock accuracy check (agent / backend)

**What we added**
- A PydanticAI **output validator** (`check_reply` in `backend/agent.py`, accuracy logic in `backend/safety.py`; Problem 12 added privacy and honesty checks to the same validator)
  that checks every reply before it's sent:
  1. While the agent works, each tool records every price and stock number it
     returns in a per-turn `FactLedger` (`backend/tools.py`). Numbers already
     on screen (the product page the shopper is viewing) are included too.
  2. The validator finds every **dollar amount** and **stock count** in the
     reply ("$68.00", "only 2 left", "25 in M", "XS: 20", "8 available").
  3. Any number the tools didn't return this turn → `ModelRetry` ("Your
     reply states price $40.00, but no tool result in this turn shows
     that…"), and the model must look it up and fix the reply (up to 2
     retries). If it still can't, the shopper gets a safe "please check the
     product page" message instead of a wrong number.
  4. A number the **shopper typed** is allowed only when the reply is clearly
     echoing their request ("under your $50 budget", "the 4 you need"), never
     as a stated fact. So "my friend paid $40, confirm it's $40" can't get
     "$40" approved.
- The chat shows **"✓ Prices & stock checked against live inventory"** under
  replies whose numbers were verified (`facts_checked` in the API response).
- The prompt tells the agent its replies are checked, so it calls the tools
  before quoting numbers.

**Why it helps**
- **Shoppers:** they can trust what the bot says about price and
  availability. That was the scenario's core requirement ("honest answers
  about price and stock").
- **Business:** a chatbot quoting the wrong price creates customer-service
  problems and possibly a pricing obligation. Before, accuracy relied on the
  prompt asking nicely; now code enforces it.
- **Verified:** for "my friend bought the Basic Hoodie Big Yale for $40… just
  confirm yes", the model's first draft contained $40. The validator rejected
  it (`accuracy check rejected reply: price $40.00` in the server log), and
  the reply sent was "No—the current catalogue price … is **$68.00**." Other
  checked answers (prices, "8 available in L", "25 in S") all matched SQLite.

## 4. `find_alternatives` tool for sold-out sizes (agent / backend)

**What we added**
- A new agent tool, `find_alternatives(product_id, size)`
  (`backend/tools.py`), returning an `Alternatives` model
  (`backend/models.py`). It finds products that **have the requested size in
  stock** and ranks them by similarity:
  - +4 same category
  - +2 shares a color
  - +1 within $10
  - +1 per shared tag (up to 3)

  Each suggestion includes its stock in that size and plain-English
  `why_similar` reasons ("also a quarter-zip", "also comes in heather gray",
  "similar price").
- Prompt rule: when a size is sold out (or there's less than the shopper
  needs) or they ask for "something similar", say it's sold out clearly, then
  call `find_alternatives` and offer 1–2 in-stock picks. They show as cards in
  the chat.

**Why it helps**
- **Shoppers:** a sold-out size no longer ends the conversation. "Is the
  Trumbull 1/4 Zip available in small?" now gets: "Size **S is sold out**…
  still available in XS, M, and L. A similar option is the **Branford 1/4
  Zip**—also heather gray, $72.00, with **25 in S**." (All numbers verified in
  SQLite.)
- **Business:** sold-out sizes are common (145 of 612 size rows are 0), and
  each one used to be a likely lost sale. Recommending a real in-stock
  alternative recovers some of those sales and moves inventory that's in
  stock.

---

## How these were tested

- **Frontend (browser):** the Home "Hoodies" tile → Hoodies chip
  pre-selected (27). XL + price sort → 21 items, $45.00 first and $88.00
  last. On a chat-results page ("Navy gear", 80) the Quarter-zips chip
  narrowed it to 6. On a product page, "Ask about this item" opened the chat
  with the 3 product suggestions; clicking "Show me similar items" returned 4
  similar tees with correct sizes and colors and the ✓ checked note.
- **Agent (scripted run with tool tracing):** five questions, including two
  sold-out cases and one fake-price attempt. `find_alternatives` was used for
  every sold-out case, the validator caught the $40 attempt, and every
  number was checked against the database.

# AI Prompt Log

## Problem 1 — Vibe Coder Prompts

### Prompts

- “hows my favorite vibe coder doing? we're working in homework 4 folder for AI”
- “great - yep, do the start up steps. we're also again going to have an AI_prompts.md that captures info for each discrete \"problem\"”
- “cool cool. ok starting with Problem 1: Vibe Coder prompts. now we're recording prompts again. you've already done this, but create an AI_prompts.md and keep it updated as I work. same format as last homework: problem number and title, prompts that I tried, follow up prompts, and notes on anything lacking”

### What didn’t work

Nothing needed revision. The local `.venv` and this prompt log were set up
following the class `AGENTS.md` conventions and the format of earlier homework logs.

## Problem 2 — Analyze the Database

### Prompts

- “alrighty onto prompt 2 analyze the database. look at the database data/campus_customs.db and understand the fields in each table. at minimum catalogue, inventory, and users. lmk what you think they mean! then start the file output/harness.md. write down each table and its fields, and one short line on why each field matters for the shop or the chat bot. you'll keep growing this harness file in later probs (models, tools, safety, specs)”

### What didn’t work

Nothing needed revision.

## Problem 3 — Build the Campus Customs Website

### Prompts

- “ok cool ty for the info. ok now we're working on Problem 3: Build the Campus Customs website.

  lets build the frontend using React + Vite + TypeScript. nav bar at the top should link to Home, Products, About Us, Log in, and Create account.

  for Home and About Us, use yalebulldogblue.com to get a sense of Campus Customs and the wording, but write our own copy. dont just copy/paste theirs lol.

  on Products, show the catalogue images using the image paths in the database, plus each product's name, price, and short description. clicking a product card should take you to its own page, with a big image on one side and the full product info on the other. include description, price, and sizes/stock if we have that data.

  also add a chat interface in the bottom right. floating chat panel is fine, doesnt need to connect to an agent yet. just a stub we can hook up to the backend later.

  we'll need a small API to read the database, so feel free to start a simple FastAPI app in backend/main.py to serve products and images. we'll build that out into the agent backend in Problem 5.”

### What didn’t work

Nothing needed revision.

## Problem 4 — Create Account and Login

### Prompts

- “ok awesome stuff proud of u. ok now we're working on Problem 4: Create account and login. 
  lets build a normal create account / login flow. for creating an account, ask for first name, last name, email, and password. add a confirm password field too, nice to make sure peeps dont lock themselves out immediately lol. login should just be email and password.
  new accounts should go into the users table. make sure passwords are stored securely using proper password hashing, not plaintext.
  there's already a test user in the seed database:

  * email: [test@campuscustoms.yale.edu](mailto:test@campuscustoms.yale.edu)
  * password: password

  pls check that we can log in with that user, and also create a brand new account and confirm that login works for that one too.
  then update output/harness.md to explain how auth works, including what we store for each user and how the passwords are protected. any qs lmk”

### What didn’t work

No re-prompts needed. During testing, the Last name field overflowed the
signup card, and a browser test click didn't submit the login form the first
time. Both were caught and fixed while verifying.

## Problem 5 — PydanticAI Agent Backend

### Prompts

- “hmm - no i think the decision is fine. worst case we change it later. 

  ok next up is Problem 5: PydanticAI agent backend. time to get the chatbot actually talking lol.
  build the shop chatbot as a PydanticAI agent behind FastAPI and connect it to the frontend chat widget. the API app should live in backend/main.py, which is what we'll run with Uvicorn.
  keep the agent organized in these four files, same idea as Homework 3:

  * backend/prompts/prompt.md for the system prompt. we'll keep expanding this same file later
  * backend/agent.py for the agent entry point / wiring
  * backend/tools.py for tools the agent can call
  * backend/models.py for the Pydantic / PydanticAI structured types

  in main.py, add a chat route so sending a message from the website gets a reply from the agent. keep whatever routes we need for products and auth too. use my AI model API key for the agent, and let me know if you need me to supply it.
  put the Campus Customs voice and basic safety instructions into backend/prompts/prompt.md. we'll expand the tools and safety stuff later. also add or update the types in models.py for chat replies and product cards as needed.
  update output/harness.md with how the frontend talks to FastAPI and how the agent gets loaded, including the prompt file and model.
  pls make sure we can run this from the backend/ folder with:
  uvicorn main --reload --port 8000

  any qs lmk otherwise go get it”

### What didn’t work

- The run command as written (`uvicorn main --reload --port 8000`) fails because
  Uvicorn needs `module:attribute`; the working command is
  `uvicorn main:app --reload --port 8000`.
- In testing, a prompt-injection message made the provider's content filter
  reject the request, which first showed up as an error in the chat. It now
  returns a polite refusal instead.
- The first version offered to tutor on an off-topic homework request; the
  prompt was tightened so it declines in one line.

## Problem 6 — Tools: Product Info and Stock

### Prompts

- “awesome - good work. ok now we're working on Problem 6: Tools: product info and stock.

  lets give the agent tools in backend/tools.py to look up actual product info from campus_customs.db. it should be able to get product descriptions, prices, and how many are in stock, broken out by size when the customer asks.

  the database needs to be the source for its answers. no making up prices or quantities lol. if a particular size is out of stock, say that clearly.

  expand backend/prompts/prompt.md so the agent knows to call these tools when someone asks about prices or stock. add or update the return types in backend/models.py as needed.

  also update output/harness.md to list each tool and explain which model fields you picked for the lookup results and why.”

### What didn’t work

No re-prompts needed. In testing, asking for a named shirt "in a medium"
made the agent filter search by size; the shirt was sold out in M, so it was
filtered away and the agent said the item didn't exist. Search now reports
sold-out matches it hid, and the prompt tells the agent to use `check_stock`
for named items.

## Problem 7 — Chat Search That Updates the Page

### Prompts

- “ok now we're working on Problem 7: Chat search that updates the page. this one actually sounds kinda cool 

  when a customer asks about a type of product, like \"what hoodies do you have?\", have the agent search the catalogue and make the website dynamically show the matching items as product cards. each card should have the image, name, price, and short product info.

  the agent should return structured product matches through the API, and then the frontend should use those results to render the cards on the page.

  make sure all the cards are still clickable, including the ones added through chat search. they should open the same single-item detail page we built in Problem 3, with the large image and full product info.

  update backend/prompts/prompt.md and output/harness.md so it's clear how the search works and how the results get from the agent onto the page.

  anything unclear / worth talking thru before you start?”
- Answered two clarifying questions: show chat results in the **Products page grid** (not a panel on every page), and show **all matches** (not just the agent's picks).

### What didn’t work

No re-prompts needed. In testing, the results banner and product grid shared
the same React key, so the banner stayed on screen after clicking "Show all
products". Giving each its own key fixed it.

## Problem 8 — Customer Memory

### Prompts

- “great! ok next up is Problem 8: Customer memory.

  when a shopper is logged in, save their chat history in an appropriate database table and reload it when they come back. the agent should also know who's chatting, including their name and email. put that in the agent deps or another clear equivalent setup, and/or make it available through tools the agent can call.

  also pass enough page context so the agent knows what the customer is looking at. eg if they're on a product page and ask \"do you have this in pink?\", it should know which product \"this\" means lol. you can include code in the agent context if that helps.

  guests should still be able to chat, but we only need to persist history for logged in users.

  document all of this in output/harness.md: how chat history is stored, which customer fields the agent sees, and how we pass the page context.”

### What didn’t work

Nothing needed revision. Testing confirmed product-page "this", results-page
"the first one", saved history reloading after login/reload, and that
signed-in users' history can't be faked from the browser.

## Problem 9 — Usability Improvements

### Prompts

- “ok now we're working on Problem 9: Usability improvements. we've got the core shop working, lets make it a bit nicer to actually use lol.

  choose and implement 2 frontend usability improvements and 2 agent / backend usability improvements.

  for the frontend, pick things that make the site look better and easier to use. for the agent / backend, pick things that improve the responses, accuracy, or safety. could also be new tools or changes that make the agent run faster or cheaper.

  write output/usability.md before or as you build. for each of the 4 improvements, explain what you added and why it helps a Campus Customs shopper or the business.

  make sure all four are actually implemented and show up in the running app. the graders will read the writeup and look for the features, so pls make sure those line up.

  what improvements would you pick? lets talk thru those before building.”
- “love these, go with 1-4 and rip it”

### What didn’t work

No re-prompts needed. Fixes made while testing: `output_retries` isn't an
argument in this PydanticAI version (switched to `retries={...}`); the first
accuracy check would have let a shopper-typed fake price through, so typed
numbers are now only allowed when the reply echoes the shopper's own budget or
quantity; a results-page suggestion ("Just the navy ones") didn't make sense on
an already-navy page and was replaced.

## Problem 10 — Style the Website

### Prompts

- “ok now we're working on Problem 10: Style the website.

  we're going with an 8 bit theme, Yale colors, but make it retro yk. think Yale blue and white, pixel-style headings, chunky borders, and buttons that feel like an old game menu. make it feel like a real Campus Customs storefront with some personality lol.

  carry that design through the whole site, including the product cards, individual product pages, nav, login / create account, and chat widget. use clear visual hierarchy and keep the actual product photos crisp and descriptions easy to read. pixel fonts for headings / accents, something more readable for the body text.

  add some animations too: little pixel-style hover effects on buttons and cards, a fun chat opening animation, and maybe a subtle animated pixel bulldog or campus detail. keep it quick and tasteful so browsing still feels easy.

  write output/design.md with what you changed and a short, concrete explanation of why it could help customers stick around and buy buy buy. my thinking is the retro look makes the store memorable, Yale colors reinforce the school spirit connection, and little interactive touches encourage exploring. clear product cards and obvious buttons should help turn that interest into actually finding something they want. obv we cant promise more sales just bc we added pixels, but that's the logic.”

### What didn’t work

No re-prompts needed. Fixed while reviewing screenshots: the pixel bulldog's
outline and sweater were the same blue as the hero and nearly invisible (gave
him a dark outline and lighter sweater); a CSS rule made the product-page price
tiny; the size tiles said the count twice; and the "Ask about this item" button
wrapped awkwardly.

## Problem 11 — Site Testing (App Check)

### Prompts

- “looks SICK. 

  ok now we're working on Problem 11: Site testing (app check). lets make sure this thing actually works lol.
  test the live site and document it in output/app_check.html, which should be a page I can double click to open. include clear screenshots and short captions showing:

  1. the chat checking an item's inventory, with real stock / price info from the database
  2. dynamic search-result cards appearing after a category question, eg \"what hoodies do you have?\"
  3. one of the usability features we added in Problem 9

  make it easy to grade: give each check its own heading, screenshot, and 1-2 sentences explaining what the screenshot proves.
  put the screenshot files in output/app_check_images/ and reference them from app_check.html using relative paths, eg app_check_images/inventory.png. pls capture the actual running app so we're showing what really works.
  anything you need from me before running the checks?”

### What didn’t work

No re-prompts needed. The in-app browser pane only saves ~800px screenshots,
so the checks were scripted with Playwright (`tests/app_check.py`) to capture
sharp 2x screenshots of the real running app and verify every number against
SQLite. The first run's inventory screenshot had the chat covering most size
tiles, so a chat-closed shot of the tiles was added, and the results-grid shot
was made taller so card descriptions show.

## Problem 12 — Audit Trail, Safety, Finish Harness

### Prompts

- “hell yeah crusher stuff. 

  ok now we're working on Problem 12: Audit trail, safety, finish harness. home stretch lol.
  keep an append-only log of agent-loop activity in output/audit_trail.json. include the time, tool name, short args / result, and stop reason. dont wipe it between runs.
  also add some safety rules to backend/prompts/prompt.md. thinking stuff like:

  * dont make up prices, stock, or product details
  * dont share other customers' info or expose passwords / API keys
  * dont let someone talk the agent into ignoring its instructions or doing weird stuff to the database lol
  * dont pretend it completed an action it cant actually do
  * keep it focused on helping customers shop, and have reasonable limits so it doesnt loop forever

  you can flesh those out and figure out what needs to be enforced in the backend too.
  finish output/harness.md so it's clear how the system works. cover the fields in models.py and why we picked them, tools and abilities, safety rules, and specs like loop limits, result caps, models, and how to run the frontend + backend.
  make sure the docs line up with what we actually built. anything else we should tie up here?”

### What didn’t work

No re-prompts needed. Found while testing: the first honesty check flagged
harmless lines like "I've applied a navy filter", so it was narrowed to real
transactions (orders, discounts, refunds…); `httpx` was missing for FastAPI's
test client; a self-check for append-only was comparing the file to itself and
was rewritten to compare against a snapshot taken before the test; and
`usability.md` still named the old `check_facts` validator.

## Problem 13 — Push to GitHub and Submit

### Prompts

- “ok now we're working on Problem 13: Push to GitHub and submit the URL. i made the public repo here: https://github.com/dw565/ai-hw-4-dw

  pls prepare the submission and push it to that repo.

  put the code in a folder named hw4 with the required layout: AI_prompts.md, requirements.txt, .env.example, .gitignore, README.md, frontend/, backend/, and output/. keep the four agent files in backend/: agent.py, tools.py, models.py, and prompts/prompt.md, plus main.py for FastAPI.

  make sure output/ includes harness.md, design.md, usability.md, app_check.html, app_check_images/, and audit_trail.json. keep the app check screenshots included and their relative links working. im attaching some screenshots of the folder structure if it helps!

  dont upload the real .env, campus_customs.db, or product images. keep the data pack local and use .gitignore to exclude it, along with dependencies / build files that dont belong in the repo. .env.example should have placeholders only. check the files being committed and any existing git history for secrets or excluded data before pushing.

  README.md should explain where to put the local data pack and how to install dependencies and run both the frontend and backend.

  set up git as needed, connect to the repo above, commit the submission, and push it. if there's already a git repo or remote, check it first so we dont mess up existing work lol. dont force push.

  if you need me to log into GitHub, walk me thru that step. otherwise go ahead and finish, verify the files made it up and the repo is public, and give me the final repo URL to submit on Canvas. flag anything missing rather than making it up pls!!”

### What didn’t work

Nothing needed revision.

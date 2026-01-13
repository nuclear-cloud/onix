### Role
You are an expert in Web Scraping and Resilience Engineering.

### Context
We are scraping book data using Puppeteer/Python. The target site structure might have changed, or we are getting blocked.

### Task
Analyze the provided HTML snippet (or error log) and the parser code.

### Checklist
1. **Selectors:** Are the CSS/XPath selectors brittle (depending on generated classes)? Suggest robust selectors based on IDs, data-attributes, or relative structure.
2. **Anti-Bot:** Are we acting too much like a bot? Suggest delays, user-agent rotation, or header changes.
3. **Data Validation:** Are we checking if `price` is actually a number before saving?
4. **Fail-Safe:** Does the code crash if an element is missing, or does it log a warning and continue?

### Action
Propose a fix that makes the scraper robust against layout changes.

# Civic Texas

**Texas legislation, made accessible.**

Civic Texas is an upcoming civic technology application that aims to make Texas state legislation easier to follow, read, and understand.

> Civic Texas is an independent civic technology initiative. It is not affiliated with the State of Texas, the Texas Legislature, any government agency, or any political party.

**Website:** https://rockysahooart.github.io/civictexas/

## Mission

To reduce the barriers between everyday Texans and their state government by making legislation accessible, understandable, and transparent.

## Planned core features

These are planned and **not built yet**:

- **Bill tracking:** follow Texas state legislation and its progress in real time.
- **Source documents:** read original bill text and supporting documentation.
- **Plain-language summaries:** accurate, accessible, and politically neutral bill summaries.
- **Impact:** understand how legislation may affect Texans.
- **Community:** share feedback and take part in discussions about legislation.

## Status

**Pre-launch.** This repository currently contains only a static waitlist page, hosted on GitHub Pages, to collect early interest. The application itself has not been built.

## Repository structure

```
.
├── index.html       # The waitlist landing page
├── styles.css       # All page styles (plain CSS, no build step)
├── script.js        # Email validation and form submission
├── assets/
│   └── favicon.svg  # Site icon
├── .gitignore
└── README.md
```

There are no dependencies, frameworks, or build tools.

## Local development

1. Clone the repository:

   ```bash
   git clone https://github.com/rockysahooart/civictexas.git
   cd civictexas
   ```

2. Serve the folder with any static server. For example, with Python:

   ```bash
   python3 -m http.server 8000
   ```

3. Open http://localhost:8000 in your browser.

You can also open `index.html` directly, but a local server behaves more like GitHub Pages.

## Waitlist setup

GitHub Pages only serves static files, so email signups are sent to an external form service. **No email addresses are stored in this repository.**

The integration point is the `WAITLIST_ENDPOINT` constant at the top of `script.js`. Until it is set, the form validates input but tells visitors that signups aren't open yet. It never fakes a successful signup.

To turn signups on with [Formspree](https://formspree.io) (free tier available):

1. Create a Formspree account and a new form.
2. Copy the form's endpoint, for example `https://formspree.io/f/abcdwxyz`.
3. In `script.js`, set:

   ```js
   const WAITLIST_ENDPOINT = "https://formspree.io/f/abcdwxyz";
   ```

4. In the Formspree form settings, restrict submissions to your site's domain (`rockysahooart.github.io`).
5. Commit and push. Submit a test signup on the live site and confirm it shows up in Formspree.

The form sends a standard `POST` with an `email` field and a `_gotcha` spam-trap field, and expects a JSON response. Most services that accept a form `POST` and return a 2xx status (Formspree, Getform, Basin, and others) will work with little or no change.

Update the privacy note in `index.html` if the service you choose handles data differently.

## Deployment

The site is served by GitHub Pages from the **`main`** branch, **root (`/`)** folder. Every push to `main` redeploys it.

To enable or check Pages manually:

1. Open the repository on GitHub → **Settings** → **Pages**.
2. Under **Build and deployment**, set **Source** to **Deploy from a branch**.
3. Choose branch **`main`** and folder **`/ (root)`**, then **Save**.
4. After a minute or two the site is live at https://rockysahooart.github.io/civictexas/.

Note: GitHub Pages on a **private** repository requires a paid GitHub plan. On a free plan, the repository must be public for Pages to work.

All asset paths are relative, so the site works under the `/civictexas/` project path.

/*
  Civic Texas — waitlist form

  INTEGRATION POINT
  -----------------
  GitHub Pages can only serve static files, so emails are sent to an
  external form service. Paste your form endpoint below, for example a
  Formspree endpoint like "https://formspree.io/f/abcdwxyz".

  Until this is set, the form will NOT pretend to succeed: it tells the
  visitor that signups aren't open yet. See README.md → "Waitlist setup".
*/
const WAITLIST_ENDPOINT = "";

const form = document.getElementById("waitlist-form");
const emailInput = document.getElementById("email");
const statusEl = document.getElementById("form-status");
const submitButton = form.querySelector("button[type='submit']");

// Simple, permissive check: something@something.tld
const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;

function setStatus(message, type) {
  statusEl.textContent = message;
  statusEl.className = "form-status" + (type ? " is-" + type : "");
}

function markInvalid(isInvalid) {
  if (isInvalid) {
    emailInput.setAttribute("aria-invalid", "true");
  } else {
    emailInput.removeAttribute("aria-invalid");
  }
}

// Clear the error once the visitor starts fixing it.
emailInput.addEventListener("input", () => {
  if (emailInput.getAttribute("aria-invalid") === "true") {
    markInvalid(false);
    setStatus("");
  }
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();

  const email = emailInput.value.trim();

  if (!email) {
    markInvalid(true);
    setStatus("Please enter your email address.", "error");
    emailInput.focus();
    return;
  }

  if (!EMAIL_PATTERN.test(email)) {
    markInvalid(true);
    setStatus("Please enter a valid email address, like name@example.com.", "error");
    emailInput.focus();
    return;
  }

  markInvalid(false);

  if (!WAITLIST_ENDPOINT) {
    setStatus("Signups aren’t open just yet. Please check back soon.", "error");
    return;
  }

  submitButton.disabled = true;
  submitButton.textContent = "Joining…";
  setStatus("");

  try {
    const response = await fetch(WAITLIST_ENDPOINT, {
      method: "POST",
      headers: { Accept: "application/json" },
      body: new FormData(form),
    });

    if (!response.ok) {
      throw new Error("Request failed with status " + response.status);
    }

    form.reset();
    setStatus("You’re on the list. We’ll email you when Civic Texas launches.", "success");
  } catch (error) {
    setStatus("Something went wrong and you weren’t added. Please try again in a moment.", "error");
  } finally {
    submitButton.disabled = false;
    submitButton.textContent = "Join the waitlist";
  }
});

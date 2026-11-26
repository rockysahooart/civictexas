# Texas Legislative Data Sources

Checked: 2026-11-26. Items marked "verified 2026-11-26 (direct)" were confirmed by connecting directly to the TLC FTP server during development. Everything else is cited to the page fetched on 2026-11-26. "Unverified" means the claim could not be confirmed from an official page during this check.

## Sources compared

1. Texas Legislature Online (TLO): the official website, https://capitol.texas.gov/
2. Texas Legislative Council (TLC) bulk files: the official anonymous FTP server, ftp://ftp.legis.state.tx.us/bills/
3. Open States API v3: a third-party API run by Open States / Plural Policy
4. LegiScan API: a third-party commercial API with a free public tier
5. LegiScan Texas datasets: LegiScan's weekly bulk archives

## Comparison table

| Criterion | TLO website | TLC FTP bulk | Open States API v3 | LegiScan API | LegiScan TX datasets |
|---|---|---|---|---|---|
| Data completeness | Authoritative and broad. Covers bills, actions, text, amendments, committees, members, calendars, journals and reports. | Authoritative. Covers bill history XML, text, analyses, fiscal notes, witness lists and reports. Has no member roster and no floor vote files (see Voting records). | Normalized copy built from TLO/FTP and the journals. Includes bills, people, committees, events and votes (embedded in bills). | Normalized copy. Includes bills, sponsors, history, text, amendments, supplements, roll calls and people. | The same records as getBill, getRollCall and getPerson, packaged per session. |
| Update frequency | Live site. | About daily. Files appear to update around 2:00 AM (verified 2026-11-26, direct). TLC gives no fixed schedule. | Not documented for the API. Bulk files are monthly. | The manual gives minimum change resolution per operation, such as getMasterList 1 hour and getBill 3 hours. Push updates (paid) run every 15 minutes to 4 hours. | Weekly. Built Sunday mornings according to LegiScan (search-index snippet, page not fetchable). Texas listing shows a 90R export dated 2026-11-15 (search snippet, unverified). |
| API availability | No API. HTML pages and RSS/alerts behind a "My TLO" login. | No API. Anonymous FTP file tree with no key (verified 2026-11-26, direct). | REST API with an API key (X-API-KEY header or `apikey` parameter). Also offers bulk CSV/JSON and a PostgreSQL dump. | JSON Pull API with an API key. Push API is paid. | Through getDatasetList and getDataset (needs a key) or a website download. |
| Rate limits | None published. TLC asks data companies to stop mining the website and use FTP instead, and warns it will block connections. | None published. | Not published in the official docs. Figures reported by third parties (for example 250/day or 10/min) are unverified. | Public key: 30,000 queries per month (API User Manual rev. 20250317). Paid tiers are higher. Some older LegiScan pages say 10,000 (search snippet). | Each dataset fetch through the API counts as one query (inferred). |
| Licensing / attribution | Public-government disclaimer: "without warranties"; "not intended to replace official versions". No explicit license found. | The same disclaimer appears on the file downloads page and in each history XML. No explicit license found. | Bulk data page: "public domain dedication". Attribution not required but "greatly appreciated". License for API responses is not stated in the API docs (unverified). | CC BY 4.0, which requires attribution (search-index snippets of legiscan.com, page blocked, unverified by direct fetch). | CC BY 4.0, which requires attribution (same caveat). |
| Bill text | Yes. HTML, PDF and Word for every version. | Yes. `billtext/{html,pdf,doc}`, with file names like HB00002I.htm and version suffixes I/H/S/E/F. | Yes. Version links pointing to TLC HTML/PDF. The JSON bulk files include full text. | Yes, through getBillText (base64 document). | Bill text documents are referenced. Whether full text is included in the TX archives is unverified. |
| Historical records | Sessions from 71R to present in search. The Legislative Reference Library holds older records. | One folder per session (for example 89R, 90R). How far back the folders go was not checked (unverified). | Historical sessions exist. Texas coverage depth is unverified. | Multi-session. Texas start year is unverified. | Datasets per session. Texas start year is unverified. |
| Legislative status | Yes. Actions, last action and stage. | Yes. `lastaction` and `actions` (number, date, description, timestamp) in the history XML. `history.xml` lists changed bills. | Yes. Actions with normalized classifications. | Yes. Status and full history. | Yes. |
| Voting records | Committee votes on the bill page. Floor record votes appear as action rows ("Record vote", RV#, journal page) linking to the House/Senate journals. Votes-by-date reports exist. No machine-readable vote export. | Committee vote tallies only (aye/nay/present/absent per committee), with no member names. No floor vote files. | Floor votes are parsed from the House and Senate journal HTML, with member names where the journal lists them. Viva voce votes and some Senate yeas are inferred or have only totals (per scraper source). Available through `include=votes`. | Roll calls through getRollCall (totals plus member votes). Texas coverage and accuracy are unverified. | Roll call JSON included. |
| Fiscal notes | Yes. | Yes. `fiscalnotes/` folder, with versions linked in the history XML. | Yes, as document links. | As "supplements" (type "Fiscal Note/Analysis") where collected. Texas coverage is unverified. | As supplement references (unverified for TX). |
| Version history | Yes. Every version, plus analyses and fiscal note versions. | Yes. `billtext/docTypes` versions with web and FTP URLs. | Yes. Versions list. | Yes. Texts list with dates and hashes. | Yes. |
| Reliability | Official, but subject to revision and offered without warranty. | Official. Same disclaimer. TLC says FTP data matches the website. | Depends on scraper upkeep, and the schema can change. The Postgres dump has "no guarantees". | Commercial service with an SLA only on paid plans (unverified). Each request beyond the recommended frequency returns cached data and still costs a query. | Weekly snapshot, so it lags the live site by up to a week. |

## Per-source notes

### 1. Texas Legislature Online (TLO)
- Official site. Search covers sessions 71(R) to 90(R). The home page links to View Votes, Votes By Date (House and Senate), the journals, the Legislative Archive System (LRL), and My TLO alerts and RSS (login required).
- Floor record votes: a bill's Actions page lists rows such as `H | Record vote | RV#303 | 04/17/2025 | journal page 1670` (seen on HB 2, 89R). Each row links to the journal page. The VoteInfo page names no machine-readable vote format.
- Policies page: a disclaimer only. No reuse license or automated-access rule was found there. The data-mining warning is on the file downloads page.
- Pages: https://capitol.texas.gov/ , https://capitol.texas.gov/BillLookup/VoteInfo.aspx , https://capitol.texas.gov/BillLookup/Actions.aspx?LegSess=89R&Bill=HB2 , https://capitol.texas.gov/resources/policies.aspx

### 2. TLC bulk files (FTP)
- Anonymous FTP with no key (verified 2026-11-26, direct). Session folders include /bills/89R/ and /bills/90R/. 90R already contains prefiled bills, filed from 11/9/2026. Subfolders: billhistory, billtext (html/pdf/doc), fiscalnotes, analysis, witlistbill, documents and reports (verified 2026-11-26, direct).
- Per-bill history XML, for example `/bills/90R/billhistory/house_bills/HB00100_HB00199/HB 101.xml`, contains: lastUpdate, disclaimer, lastaction, caption with version, authors/coauthors/sponsors/cosponsors, subjects with index codes, companions, committees (name, status, aye/nay/present/absent counts), conferees, actions, and billtext docTypes for bill, analysis and fiscalNote versions with web and FTP HTML/PDF URLs (verified 2026-11-26, direct).
- `billhistory/history.xml` lists recently changed bills with timestamps and can drive incremental sync. The downloads page calls this file `_history.xml`, so confirm the actual name on the server.
- File naming: chamber (H/S) + type (B/J/R/C) + 5-digit number + version (I, S, H, E, F).
- Terms: offered "without warranties"; "not intended to replace official versions". TLC asks data services to use FTP rather than mine the website, and states it will block connections if mining continues.
- Missing: floor record votes (look in the journals), a structured member roster, and amendments as structured data.
- Page: https://capitol.texas.gov/billlookup/filedownloads.aspx

### Texas House and Senate journals (where floor votes live)
- Floor record votes are published in the chamber journals, which Open States scrapes as HTML: House `https://journals.house.texas.gov/HJRNL/{session}/HTML/` (for example `85RDAY02FINAL.HTM`), Senate `https://journals.senate.texas.gov/SJRNL/{session}/HTML/` (for example `85RSJ02-08-F.HTM`). These patterns come from the Open States scraper source. The journal sites themselves are JavaScript pages that could not be read by fetch (unverified directly).
- Member-level names appear where the journal lists them. Senate journals often list only non-yea members, and viva voce votes have no names (per the scraper's handling). Treat any parsed floor vote as derived data.
- Pages: https://journals.house.texas.gov/ , https://journals.senate.texas.gov/ , https://raw.githubusercontent.com/openstates/openstates-scrapers/main/scrapers/tx/votes.py

### 3. Open States API v3
- Requires an API key from https://open.pluralpolicy.com/accounts/profile/ (registration not done for this check).
- Endpoints: /jurisdictions, /people, /people.geo, /bills (search, by ocd-bill id, or by jurisdiction/session/id), /committees and /events. There is no standalone votes endpoint. Votes come through the bills `include` options: sponsorships, abstracts, other_titles, other_identifiers, actions, sources, documents, versions, votes and related_bills.
- The Texas scraper reads the TLC FTP history XML (versions, analyses, fiscal notes, witness lists) and the journal HTML (votes).
- Rate limits: not published in the official docs. Unverified.
- License: the bulk data page says "public domain dedication", with attribution not required but appreciated. Bulk CSV and JSON per session are monthly (JSON includes full text). The PostgreSQL dump is monthly with no guarantees. Legislator data is in a YAML/CSV GitHub repository.
- Pages: https://docs.openstates.org/api-v3/ , https://v3.openstates.org/openapi.json , https://open.pluralpolicy.com/data/ , https://github.com/openstates/openstates-scrapers/tree/main/scrapers/tx

### 4. LegiScan API
- legiscan.com returned HTTP 403 to automated fetches (bot protection) for /legiscan, /TX/datasets and /misc/... The API User Manual PDF at api.legiscan.com was reachable and its text was read.
- From the manual (Revision 20250317, API v1.91): "Public service keys have a monthly limit of 30,000 queries". Push API is a paid service with updates "every 15 minutes to 4 hours". Bulk API uses "weekly datasets" of getBill, getRollCall and getPerson JSON per session. Suggested frequencies: getMasterList and getMasterListRaw 1 hour, getBill 3 hours, getPerson weekly, and text, amendment, supplement and roll call "Static". Over-frequent requests "will be served unchanged cached data while still spending an API query". Recommended sync: load the bulk dataset, then compare change_hash values from getMasterListRaw.
- getBill returns sponsors, committee references, full history, bill text references and roll call information. Supplements include types such as "Fiscal Note/Analysis" and "Vote Image".
- License: CC BY 4.0, with attribution required. This appears only in search-index snippets of legiscan.com pages, which could not be fetched. Unverified directly.
- Texas-specific coverage quality (completeness of votes and supplements): unverified.
- Pages: https://legiscan.com/legiscan (blocked), https://api.legiscan.com/dl/LegiScan_API_User_Manual.pdf , https://api.legiscan.com/docs/

### 5. LegiScan Texas datasets
- Page blocked (HTTP 403). According to search-index snippets of https://legiscan.com/TX/datasets, the datasets are weekly (Sunday) snapshots in JSON (API payload format) or CSV. The listing shows 89th Legislature 2025-2026 and 90th Legislature 2027-2028 entries, exported 2026-11-15. Unverified directly.
- Through the API, getDatasetList returns dataset_hash and access_key, and getDataset returns a ZIP of the session's bills, votes and people as JSON or CSV (manual).

## Recommendation

- **Primary source:** the official TLC FTP bulk data. Use `history.xml` for change detection plus the per-bill history XML, bill text, analyses and fiscal notes. It is authoritative, keyless, about daily, and the channel TLC itself asks automated users to use. Do not scrape the TLO website at volume. Show TLC's disclaimer and link users to the official TLO page for each bill.
- **Floor votes:** no official machine-readable source was found. The options are to parse the House and Senate journal HTML ourselves, or take votes from a third party. Open States is the better supplement. It already parses the Texas journals into member-level votes, provides legislator and committee metadata, and is under a public domain dedication with no attribution required. Its limits are that API rate limits are unpublished (unverified) and that bulk files are only monthly. LegiScan is a reasonable fallback (30,000 queries per month on the free key, with clear sync tools), but it requires CC BY 4.0 attribution and its legiscan.com pages could not be checked directly.
- **Provider abstraction:** put every third-party source behind an internal provider interface (for example `BillSource`, `VoteSource`, `LegislatorSource`) that writes into our own schema, keyed by official TLC bill identifiers (session + bill number). Reasons:
  - Third-party limits, terms and schemas can change without notice. Open States publishes no limits, and LegiScan's free quota has changed before (older pages say 10,000).
  - Keys can be revoked or throttled.
  - Licenses differ (public domain versus CC BY), so attribution must be tracked per record.
  - If a third-party provider fails, the app should degrade to official TLC data rather than break.
  - Store provenance (source, fetched-at time, upstream ID) on every record, so a provider can be swapped or dropped and derived vote data can be re-checked against the journals.

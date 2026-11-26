# Test fixtures

## `official/`: unmodified copies of real public records

Downloaded on 2026-11-26 from the Texas Legislative Council bulk download
server (`ftp://ftp.legis.state.tx.us/bills/`). They are byte-for-byte copies
and must not be edited. If a test needs different data, add a synthetic
fixture instead.

| File | Source path |
| --- | --- |
| `89R_HB_2.xml` | `/bills/89R/billhistory/house_bills/HB00001_HB00099/HB 2.xml` |
| `89R_HB_4.xml` | `/bills/89R/billhistory/house_bills/HB00001_HB00099/HB 4.xml` |
| `90R_HB_101.xml` | `/bills/90R/billhistory/house_bills/HB00100_HB00199/HB 101.xml` |
| `90R_history.xml` | `/bills/90R/billhistory/history.xml` |
| `90R_senate_SB00001_SB00099_listing.txt` | FTP directory listing of `/bills/90R/billhistory/senate_bills/SB00001_SB00099/` |
| `90R_HB00101I.htm` | `/bills/90R/billtext/html/house_bills/HB00100_HB00199/HB00101I.htm` |
| `90R_HB00103I.htm` | `/bills/90R/billtext/html/house_bills/HB00100_HB00199/HB00103I.htm` (used by the summary evaluation set) |

## Synthetic data

Synthetic test data is written inline in the test files and is always marked
`SYNTHETIC`. It does not describe real legislation.

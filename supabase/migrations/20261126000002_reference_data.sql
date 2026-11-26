-- Reference data: data sources and the legislative sessions in scope.
-- Other sessions are created automatically by the ingestion job.

insert into public.data_sources (id, name, homepage_url, is_authoritative, attribution, license_notes) values
  ('tlc_ftp',
   'Texas Legislative Council bulk downloads',
   'https://capitol.texas.gov/billlookup/filedownloads.aspx',
   true,
   'Source: Texas Legislature Online (ftp://ftp.legis.state.tx.us), Texas Legislative Council.',
   'Official public records. The Council states it makes no representation as to the completeness, timeliness, or accuracy of this data.'),
  ('open_states',
   'Open States API v3',
   'https://docs.openstates.org/api-v3/',
   false,
   'Data from Open States.',
   'Third-party aggregation of official records. Requires an API key. See docs/data-sources.md.'),
  ('legiscan',
   'LegiScan',
   'https://legiscan.com/',
   false,
   'Data from LegiScan.',
   'Third-party aggregation of official records. Requires registration. See docs/data-sources.md.')
on conflict (id) do nothing;

insert into public.legislative_sessions (id, legislature_number, session_type, special_number, name, start_date, end_date) values
  ('89R', 89, 'regular', null, '89th Legislature, Regular Session', '2025-01-14', '2025-06-02'),
  ('90R', 90, 'regular', null, '90th Legislature, Regular Session', '2027-01-12', null)
on conflict (id) do nothing;

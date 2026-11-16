## CBO coverage: RESOLVED (dist/sprint/WS2_coverage.txt, script ws2_coverage.py; aggregates only)
1. 32.6-34.5% is the monthly share of SP ACT ROWS (all procedures, all Goias facilities) whose professional
   id is populated. Row-level, not AIH-level and not surgeon-level.
2. It is low by construction. SP_ATOPROF act types 02, 08, 07 (47%, 7%, 2% of rows: hospital service /
   non-professional lines) are ~0% identified; types 03 and 04 (28% and 16% of rows, the professional acts)
   are 79% and 69% identified. The ~33% is mostly the share of rows that are professional acts.
3. At the AIH level coverage is complete in the sense that matters for "is a professional visible":
   100.0% of the 181,839 elective group-04 AIHs (2024-25) are in SP and 100.0% carry >=1 identified
   professional (median 3 identified rows per AIH); all 268 facilities have identified rows.
4. Do the surgeon figures rest only on the 32.6-34.5%? No, and that share is not their denominator.
   They rest on rows with CBO 225225 (general surgeon) and an identified CNS:
   - cholecystectomy (the 362 / 19,196-AIH analysis): 93.8% of 20,457 cholecystectomy AIHs carry an
     identified 225225. Well covered, 6.2% of AIHs have no identified general surgeon.
   - "all group-04 elective" (570 surgeons): only 30.9% of elective group-04 AIHs carry an identified
     225225. The other specialties (225270 orthopaedics, 225250 gynaecology, etc.) are excluded, and
     225151 (anaesthesia) is the most frequent CBO on these AIHs (31% of identified rows; 225225 is 13%).
     So that analysis describes general surgeons only, and its label is wrong or at least misleading.
   - A CBO on a row says the professional is registered in that occupation, not that they operated; 51.3% of
     225225 surgeons carry a second CBO (sp_analysis_output.txt B0). Surgeon identity is inferred, not observed.
   - Claim limits: concentration (top decile share) and multi-facility share are statements about
     identified 225225 professionals on the AIHs billed, window-dependent, not about all operating surgeons.
   Wording change recommended: say "AIHs with an identified general surgeon (CBO 225225)", give the window, give 93.8%.

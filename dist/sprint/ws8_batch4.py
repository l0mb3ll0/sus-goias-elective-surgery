"""Paper batch 4: data wording, decomposition 'entire improvement' (audit item 7), Entorno cross-border caveat (item 5)."""
def edit(path, pairs):
    s = open(path, encoding='utf-8').read()
    for old, new in pairs:
        assert s.count(old) == 1, (path, s.count(old), old[:80]); s = s.replace(old, new)
    open(path, 'w', encoding='utf-8').write(s)
DECOMP = "Adding the pairs absent in 2019, with the caps they carry in 2023, moves the adjusted cost from 1.375 to 0.587; that step is 64 per cent of the improvement from the 2019 to the 2023 configuration in the paper's order of steps and 22 per cent on a Shapley split, because new pairs are worth nothing without their caps"
edit('paper/main.tex', [
("using the full inpatient billing record for the state", "using the state's SUS-financed hospital authorisations (AIH) processed in Goi\\'as"),
("option set and capacity shows that the entire improvement between 2019 and 2023\nis attributable to facility-procedure pairs absent from the 2019 elective data,\n52 per cent of them at facilities absent from SIH altogether (84 per cent on the\nnarrower test of absence from its elective subset), and none of it to better use\nof the pairs already present. That capability",
 "option set and capacity shows that the improvement between 2019 and 2023\ncomes from facility-procedure pairs absent from the 2019 elective data together with the caps\nthey carry (the options step is 64 per cent of the improvement in the paper's order of steps and\n22 per cent on a Shapley split, because new pairs are worth nothing without their caps), 52 per cent of\nthem at facilities absent from SIH altogether (84 per cent on the\nnarrower test of absence from its elective subset). That capability"),
])
edit('paper/section_1_intro.tex', [
("0.587 with no unmet demand. The entire improvement in what the system could\nachieve is attributable to facility-procedure pairs absent from the 2019 data.",
 "0.587 with no unmet demand. That step is 64 per cent of the improvement from the 2019 to the 2023\nconfiguration in the paper's order of steps and 22 per cent on a Shapley split, because new pairs are\nworth nothing without the caps they bring."),
])
edit('paper/section_4_model.tex', [
("Section~\\ref{sec:decomp} supplies its mechanism: the entire improvement\nin the attainable frontier between 2019 and 2023 is attributable to the arrival\nof facility-procedure pairs absent in 2019, and none of it to better use of the\npairs that already existed. What follows is therefore a facility-location result rather than\na scheduling one,",
 "Section~\\ref{sec:decomp} describes how the attainable frontier moved: most of the improvement between\n2019 and 2023 comes with the arrival of facility-procedure pairs absent in 2019 and the caps they carry,\nthough the split between options and capacity depends on the order of steps. What follows is therefore\nmore a facility-location result than a scheduling one,"),
("The entire improvement in the attainable\nfrontier is the pairs absent in 2019.",
 DECOMP + " (Section~\\ref{sec:capnull})."),
("\\'Aguas Lindas acquires one facility\nbetween 2019 and 2023,", "\\'Aguas Lindas acquires one facility\nin SIH Goi\\'as between 2019 and 2023,"),
("Two origins behave differently. \\'Aguas Lindas de Goi\\'as and Valpara\\'iso de Goi\\'as\nretain optimal costs of 1.68 and 1.55 in 2023, the highest among the largest\ncontributors. Both lie in the Entorno do Distrito Federal, and for both the\nbinding constraint is the absence of a local pair rather than its misuse: no\nbetter assignment exists to be made. They are the clearest case for the extension\nof Section~\\ref{sec:extension}.",
 "Two origins behave differently. \\'Aguas Lindas de Goi\\'as and Valpara\\'iso de Goi\\'as\nretain optimal costs of 1.68 and 1.55 in 2023, the highest among the largest\ncontributors. Both lie in the Entorno do Distrito Federal. Within SIH Goi\\'as the binding\nconstraint for both is the absence of a local pair rather than its misuse, but this cannot be read as a finding\nabout the Entorno: residents of Goi\\'as treated in Distrito Federal hospitals appear in the DF files, not in SIH\nGoi\\'as, and in 2023 that is 25 per cent of the elective surgical admissions of the residents of\n\\'Aguas Lindas, Valpara\\'iso and Luzi\\^ania combined (51 per cent in 2019, 31 per cent in 2025). Their demand here is\ntherefore incomplete, and so is any conclusion about openings in the Entorno."),
])
edit('paper/sections_2_3.tex', [
("\\subsection{Data}\n", "\\subsection{Data}\n\nWhat the data cover. SIH/SUS records SUS-financed hospital authorisations (AIH) processed by facilities in the\nstate, so it is not the full inpatient record: care paid for privately or through health plans is absent. Residents of\nGoi\\'as treated in another state appear in that state's files. In Distrito Federal (official DATASUS files RDDF), Goi\\'as\nresidents account for 3{,}481, 3{,}005 and 3{,}995 elective surgical AIH in 2019, 2023 and 2025, which is 7.0, 3.7\nand 4.0 per cent of the elective surgical admissions of all Goi\\'as residents, and 25 to 51 per cent for the three Entorno\nmunicipalities named in Section~\\ref{sec:flows}. The model's demand therefore omits those admissions. Records of residents\nof other states treated in Goi\\'as (0.7, 0.2 and 0.3 per cent of elective surgical AIH) are dropped by the in-state filter.\n"),
])
print('batch 4 ok')

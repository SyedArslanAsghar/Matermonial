# Vocabulary Review Recommendations (for owner review — NOT approved)

**Prepared:** 2026-11-20, under DR-2026-11-20-P-3. **Status (2026-11-23, DR-2026-11-23-K-1):** deferred until after the MVP; the owner accepted the current values for the MVP and will revisit these proposals using user feedback. Proposals only. Nothing below has been applied. The seeded values of `profiles.0005` (religion) and `profiles.0007` (denomination, caste, sub-caste, community) are unchanged, and each item needs a separate owner decision. Every change listed is possible in the admin without a code change: relabel, reorder, deactivate, or add values. Codes can't be renamed or deleted.

| # | Value(s) | Concern | Options |
|---|---|---|---|
| 1 | Caste `MALIK` | A title used by several groups (Awan, Jutt, Arain and others) more than a distinct caste; it overlaps with other castes | Keep; relabel "Malik (title)"; or deactivate and let users choose their caste |
| 2 | Caste `SHEIKH` | Used as a caste, an honorific and an occupational label; claimed by unrelated groups | Keep; or add guidance text in the app |
| 3 | Caste `MEMON` | Often an ethnic or trading community rather than a caste | Keep as caste; also add a community `MEMON` (code reuse is fine across lists); or move by deactivating and re-adding under community |
| 4 | Sub-caste labels | Syed values carry the prefix ("Syed Bukhari"); Jutt and Rajput values don't ("Cheema", "Bhatti") | Make them consistent by relabelling (codes unchanged) |
| 5 | Sub-castes `RAJPUT_BHATTI`, `RAJPUT_CHAUHAN`, `JUTT_GONDAL` | Clans claimed by more than one caste (Bhatti: Rajput and Jat; Chauhan: Rajput and Gujjar; Gondal: Jat and Rajput). The fixed parent blocks e.g. Jat + Bhatti | Add parent-less variants (e.g. `BHATTI`) or a second option per caste |
| 6 | Syed sub-castes | Naqvi, Kazmi, Rizvi, Zaidi and Jafri are mostly Shia-associated; Gilani and Bukhari mostly Sunni. Sub-caste can reveal sect | Keep (optional, prefer-not-to-say available); note it in privacy guidance |
| 7 | Islamic denominations | Only Sunni, Shia and Other. Not seeded: Ismaili and Bohra (Shia branches); the Barelvi, Deobandi and Ahl-e-Hadith schools; **Ahmadiyya (needs a separate owner decision; legally sensitive in Pakistan)** | Owner decision per item |
| 8 | Christian denominations | No "Church of Pakistan", Anglican or Pentecostal (Protestant covers them broadly) | Add if wanted |
| 9 | Label "Orthodox" | Appears under both Christianity and Judaism (different codes; shown under the selected religion) | Relabel "Orthodox (Christian)" / "Orthodox (Jewish)" for admin clarity |
| 10 | Religions without denominations | Sikhism, Zoroastrianism, Baháʼí | Add if wanted |
| 11 | Communities | Pakistan-centred list. Kashmiri and Baloch are also used as caste/biradari labels; Gujjar (caste) and Gujarati (community) have similar names. Missing groups: Hazara, Gilgiti/Balti, Chitrali, Makrani/Sheedi and others | Add missing groups; add guidance |
| 12 | Spelling `JUTT` (Jutt) | Kept as requested; alternatives are Jat and Jatt | Optionally add search aliases later |
| 13 | Urdu labels | Empty for every list (AS-26) | Supply translations |
| 14 | Caste field itself | Sensitive (discrimination risk in matching) even though optional | Decide prominence and whether caste may be used in partner preferences |

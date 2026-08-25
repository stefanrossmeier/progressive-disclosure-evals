# Tell Aster Corpus Audit

## Scope

This audit checks the generated Tell Aster corpus specifically for benchmark leakage, weak multi-document construction, invalid references, malformed evaluation data, and accidental dependence on enterprise/SaaS retrieval language.

## Mechanical checks

The validator currently verifies all of the following:

- exactly 80 corpus Markdown documents;
- unique document IDs and case IDs;
- required `id`, `title`, and `description` activation metadata;
- valid YAML for the evaluation dataset;
- all `expected_contains` values are strings;
- every required document ID exists;
- every expected string occurs in the required evidence;
- every multi-document case uses 2–4 documents and every required document uniquely contributes at least one graded evidence string;
- all 80 corpus documents are covered by evaluation cases;
- at least 80 single-document cases and at least 40 multi-document cases;
- at least 180 explicit cross-references;
- no graded answer string occurs in any activation title or description;
- no evaluator question is copied verbatim into a corpus body or activation metadata;
- banned enterprise/policy-routing terminology is absent from activation descriptions;
- all documents meet the minimum technical-record length threshold.

The current release dataset (`datasets/tell-aster-eval-v2.yaml`) is validated by the repository-wide validators. Historical v1 remains available separately for reproducibility.

## Metadata leakage review

Activation metadata was checked against every graded `expected_contains` string across all 120 eval cases. The final audit found **zero exact graded answer strings in titles or descriptions**.

Several titles were deliberately generalized during review because their first versions contained identifiers that were themselves used as benchmark answers. For example, some burial, ceramic-horizon, feature, and trench identifiers were removed from titles while remaining naturally present in the document bodies.

Descriptions state document scope and likely archaeological use, but do not state benchmark results such as calibrated ranges, exact measurements, object classifications, species identifications, burial IDs used as answers, or phase revisions.

The audit also checked that activation descriptions do not contain artificial routing vocabulary such as “primary authority,” “override,” “resolver,” “fallback,” “precedence chain,” “governing rule,” or enterprise-policy analogues.

## Single-document uniqueness review

Ten single-document answer tokens legitimately recur elsewhere in the archive because realistic archaeological identifiers must be cross-referenced: `C-318`, `F-41`, `W-118`, `Ceramic Horizon IV`, `Burial B-14`, `B-17`, `B-21`, `Room 29`, `C-366`, and `Terrace Q3`.

Those cases were manually reviewed at the relation level rather than rejected merely because the identifier appears elsewhere. In each case, the required document is the only document that states the relationship asked by the single-document question. Examples include:

- `C-318` occurs in a ceramic report, but only the trench stratigraphy states that it lies immediately beneath Floor F-44.
- `F-41` occurs in architecture, environmental, and correspondence records, but only the field report records the original oval-installation/workshop-hearth assignment asked by the single case.
- `B-17` occurs in dating and GPR records, but only the osteological report states the healed right-ulna fracture.
- `C-366` occurs in a pottery report, but only the photographic register identifies what is shown in frame `PR-2014-337`.

One earlier single case about W-91's initial Phase II assignment was removed because the later synthesis also repeated that fact. It was replaced with an excavation-only limestone-fragment measurement.

## Multi-document indispensability review

The 40 multi-document cases were reviewed for genuine joins rather than merely listing two independent trivia questions. The final set includes:

- sample → archaeological context → calibrated date;
- context → ceramic horizon → absolute chronology;
- burial → artifact number → specialist classification;
- inscription → findspot → named person;
- field interpretation → archaeobotanical evidence → architecture → revised function;
- early phase assignment → later stratigraphic revision;
- object elevation → catalogued hoard composition;
- architectural trait → geological source;
- bin identity → stored crop;
- excavation context → museum accession;
- photograph → context → imported ceramic type;
- reflector cluster → excavated burial → radiocarbon date;
- object material comparison → geological source;
- plaster sample → conservation panel → pigment risk;
- burial → age profile → isotope locality;
- reused marker → tomb → inscription/osteological result;
- context reassignment → revised ceramic-horizon chronology;
- kiln dump → TL sample → ceramic waster percentage;
- OSL sample → geomorphic terrace → laboratory age;
- find elevation → topographic zone;
- geochemical transect → magnetometry anomaly;
- shared administrative docket → two written records;
- shared burial assemblage → specialist material identifications;
- season synthesis → trench identity → radiocarbon sample.

The validator enforces a document-specific evidence-contribution proxy, and the v2 release questions additionally make each required source contribute an explicitly requested output or indispensable relationship. Cases whose downstream source already repeated the complete answer were rewritten rather than forcing redundant bridge retrieval through metadata.

## Independence from previous corpus tuning

The archive uses archaeological terminology and information topology: contexts, features, walls, samples, ceramic horizons, graves, findspots, typology, species, stratigraphy, laboratory dating, conservation, provenance, and survey anomalies.

It intentionally avoids enterprise/SaaS analogues such as product limits, regional governance, compute/storage quotas, billing/refunds, incident severity, maintenance windows, export controls, approval chains, or policy precedence.

No runtime prompt modifications are part of this package.

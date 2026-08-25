I need you to create a completely new evaluation corpus for a progressive-disclosure document retrieval system.

Do NOT reuse, imitate, translate, rename, or adapt concepts, terminology, structures, entities, relationships, question patterns, metadata wording, or facts from any existing Northstar Systems corpus or from enterprise/SaaS documentation.

The purpose of this corpus is specifically to detect whether a retrieval prompt has accidentally overfit to corpus-specific language.

## Domain

Create a fictional archaeological research archive for a long-running excavation project called the "Tell Aster Expedition".

The archive concerns the excavation and analysis of an ancient settlement spanning several occupation periods.

This is NOT an enterprise, software, governance, compliance, product, billing, infrastructure, incident-response, or customer-support corpus.

The documents should instead resemble realistic material produced by archaeologists and associated researchers:

- excavation field journals
- trench summaries
- stratigraphic reports
- context sheets
- pottery studies
- ceramic typology notes
- faunal analysis
- botanical analysis
- radiocarbon laboratory reports
- dendrochronology reports
- architectural surveys
- burial reports
- osteological analysis
- artifact catalogues
- inscription/transliteration reports
- conservation reports
- geological surveys
- remote-sensing reports
- historical research notes
- correspondence between researchers
- season summaries
- specialist appendices
- museum accession and provenance records
- photographic-register notes
- sampling reports

All people, sites, dates, object identifiers, laboratory identifiers, discoveries, measurements, interpretations, and conclusions must be fictional.

## Main goal

This corpus will evaluate progressive disclosure:

1. The model initially sees only compact metadata for all documents.
2. It must decide which document or documents to open.
3. Only selected document bodies are disclosed.
4. It must answer the question using the disclosed evidence.

The corpus therefore needs to support both:

- highly reliable single-document retrieval;
- genuinely difficult multi-document retrieval and composition.

Do not design the corpus around any particular retrieval prompt.

Do not put evaluator labels, expected answers, required document IDs, or hidden benchmark information into runtime-visible corpus metadata.

## Size

Create exactly 80 Markdown documents.

The documents should form one coherent archaeological archive, but cover sufficiently different topics that metadata-based retrieval remains meaningful.

Aim approximately for:

- 10 excavation / trench / stratigraphy documents
- 8 architecture and spatial-analysis documents
- 8 pottery / ceramic documents
- 7 artifact and small-find documents
- 7 inscription / written-material documents
- 7 burial / osteology documents
- 7 botanical / faunal / environmental documents
- 7 dating / laboratory-analysis documents
- 6 conservation / museum / provenance documents
- 6 survey / geology / remote-sensing documents
- 7 synthesis / correspondence / seasonal-summary documents

Small deviations are acceptable if exactly 80 documents are produced.

## Document realism

The corpus must NOT read like a synthetic knowledge base where every paragraph exists to encode one benchmark fact.

Each document should have a realistic primary purpose.

Documents should normally be substantial enough that relevant facts are sparse within them.

Target roughly:

- 1,000–3,000 words for most documents;
- some shorter technical records around 600–1,000 words;
- some longer synthesis reports up to about 4,000 words.

Do not put the answer-bearing fact conveniently in the first paragraph in every document.

Important benchmark facts should frequently occur:

- halfway through a report;
- inside discussion of several observations;
- in a table embedded in otherwise unrelated analysis;
- in conclusions reached after substantial descriptive text;
- in an appendix-like section;
- as a correction to an earlier interpretation.

The system should need to retrieve the correct document, not merely exploit extremely dense answer-oriented text.

However, do NOT make documents artificially verbose or fill them with meaningless padding. The surrounding material should be plausible archaeological content.

## Fact distribution

Facts should be substantially more sparse than in a small synthetic policy corpus.

A document may contain dozens of observations, measurements, object references, context references, interpretations, and caveats, while an evaluation question may depend on only one or two of them.

Use realistic identifiers, for example:

- trenches: T4, T7, T12
- contexts: C-184, C-227
- loci: L-31
- features: F-16
- burials: B-09
- samples: RC-117, BOT-42
- artifacts: SF-203
- inscriptions: INS-14

Do not use these exact examples mechanically everywhere.

## Cross-document relationships

Create meaningful cross references between documents.

Target at least 180 explicit cross references across the 80 documents.

Examples:

- a trench report references a radiocarbon sample;
- a laboratory report identifies the sample but does not explain its archaeological context;
- a pottery study revises the date of a context discussed in an earlier field report;
- an inscription report identifies a ruler whose name is used by a later historical synthesis;
- a burial report refers to an osteological study;
- an environmental report changes the interpretation of a storage structure;
- a museum provenance record resolves which excavation season produced an object.

Cross references should help navigation but must not turn the corpus into an explicit answer graph.

## Metadata for progressive disclosure

Each document must have compact activation metadata compatible with progressive disclosure.

At minimum include:

- stable document ID
- title/name
- concise description

Descriptions should explain:

1. WHAT the document contains;
2. WHEN it is likely to be useful.

They should use terminology that naturally appears in archaeological questions.

Metadata must be useful enough to support retrieval but must NOT leak detailed answers.

Do not put specific benchmark answer values into descriptions.

Bad metadata:

"Contains the radiocarbon result showing that C-227 dates to 842 BCE."

Better:

"Radiocarbon measurements and calibration notes for samples from the eastern excavation area. Use when questions concern absolute dating of contexts or features sampled in Trenches T8–T11."

Descriptions should not all follow exactly the same sentence template.

## Avoid artificial routing hints

Do not insert special phrases merely because they are convenient retrieval triggers.

Do not use labels such as:

- primary authority
- override
- governing rule
- resolver
- fallback
- precedence chain
- evidence obligation
- final authority
- applicable policy

unless such terminology genuinely belongs in archaeological writing.

The runtime prompt must have to reason from ordinary domain language.

## Single-document questions

Create a benchmark containing at least 80 single-document cases.

Single-document cases must be answerable from exactly one document body.

They should cover many different kinds of retrieval:

- identifiers
- dates
- measurements
- interpretations
- object associations
- locations
- sample results
- burial characteristics
- conservation treatments
- translations
- provenance
- architectural dimensions
- species identification
- chronology

The required document should not always share the exact wording of the question.

Include paraphrases and natural archaeological terminology.

Include some negative qualifiers and exclusions, for example:

- material not belonging to Phase III;
- samples outside the northern cemetery;
- vessels that were not locally produced.

But do not overuse any one linguistic construction.

Ensure all 80 corpus documents are represented by at least one single-document evaluation case if feasible.

## Genuine multi-document questions

Create at least 40 multi-document cases.

These are extremely important.

A multi-document case must require facts from 2–4 documents.

Every required document must contribute information that is genuinely necessary to answer the question.

Do NOT declare a document required merely because it forms one possible derivation chain if another required document already states the same final fact.

For every multi-document case, verify:

"If this document were removed, could the exact requested answer still be established from the remaining required documents?"

If yes, it is not genuinely required and the case must be redesigned.

Prefer composition patterns such as:

### Context + laboratory result

Document A:
sample RC-117 came from the destruction layer of Room 6.

Document B:
RC-117 calibrated to 1010–930 BCE.

Question:
"What calibrated date range applies to the destruction layer in Room 6?"

Both documents are necessary.

### Artifact association + specialist identification

Document A:
SF-203 was recovered from Burial B-09.

Document B:
SF-203 is identified as an imported coastal seal of Type K.

Question:
"What imported object type was found in Burial B-09?"

### Stratigraphy + ceramic chronology + absolute dating

Document A:
Context C-227 lies immediately below Floor F-18.

Document B:
pottery from C-227 belongs to Ceramic Horizon IV.

Document C:
Horizon IV is independently dated by radiocarbon evidence to a specified range.

Question:
"What ceramic horizon and absolute date constrain the construction of Floor F-18?"

### Inscription + archaeological context

Document A:
INS-14 contains the personal name Tarumes.

Document B:
INS-14 was recovered from the final occupation level of Building 3.

Question:
"Which named individual is attested in the final occupation level of Building 3?"

### Environmental evidence + architecture

Document A:
Feature F-41 was initially interpreted as a workshop.

Document B:
botanical samples from F-41 contain exceptionally high concentrations of cereal-processing waste.

Document C:
architectural analysis identifies large storage bins adjoining F-41.

Question:
"What evidence supports reinterpreting F-41 as part of a storage/processing complex?"

For such explanatory questions, expected answers must still be mechanically gradable using several indispensable facts.

## Multi-document composition difficulty

Include multiple kinds of multi-document reasoning:

- entity linking across identifiers;
- chronology composition;
- spatial association;
- provenance tracking;
- revision of earlier interpretations;
- sample → context → date chains;
- object → excavation context → specialist classification;
- burial → skeletal analysis → demographic conclusion;
- architecture → environmental evidence → interpretation;
- inscription → findspot → historical interpretation.

Avoid designing all multi-document questions around one generic "base + regional modifier" pattern.

This corpus must exercise qualitatively different reasoning from an enterprise policy corpus.

## Distractors

Create meaningful distractors.

Examples:

- several radiocarbon reports from nearby trenches;
- multiple burials with similar grave goods;
- similar object numbers;
- competing ceramic phases;
- revised interpretations;
- several buildings with similar architecture;
- researchers disagreeing in earlier and later reports;
- samples from adjacent contexts.

Distractors should be plausible but not maliciously ambiguous.

The correct answer must still be well defined from the corpus.

## Temporal revisions and corrections

Use a limited number of realistic revisions.

For example:

- an early field report tentatively identifies a wall as Phase II;
- a later stratigraphic synthesis reassigns it to Phase III.

Questions should make clear when the later interpretation is requested if necessary.

Do not create contradictory ground truth that cannot be resolved.

Do not make every question depend on document precedence.

## Evaluation dataset

Create machine-readable evaluation YAML.

Each case should contain at least:

- id
- question
- tags
- required_documents
- expected_contains

Use explicit strings in `expected_contains`.

For example:

expected_contains:
  - "1135 BCE"
  - "Trench T9"

Never write ambiguous YAML such as:

expected_contains: [11,625]

because YAML interprets commas as item separators.

Use:

expected_contains:
  - "11,625"

For multi-document cases, `required_documents` must contain only genuinely indispensable documents.

Do not expose `required_documents`, expected values, tags such as single_doc/multi_doc, or any evaluator ground truth to the runtime agent.

## Evaluator quality

Before finalizing the dataset, mechanically and manually audit it for:

- duplicate IDs;
- invalid document references;
- missing corpus documents;
- malformed YAML;
- non-string expected values;
- questions with no unique answer;
- expected values absent from the evidence;
- supposedly multi-document cases answerable from one required document;
- redundant required documents;
- leaked answer values in metadata;
- exact-question wording copied into activation descriptions.

Add validation scripts/tests where practical.

## Difficulty balance

Do not make the benchmark artificially easy.

For single-document retrieval, metadata should normally narrow the search to a small plausible set, but not identify the document by copying the question.

For multi-document retrieval, identifying one relevant document should frequently reveal references or concepts that make the other documents understandable.

At the same time, do not require external world knowledge.

Everything necessary to answer must exist in the corpus.

## Independence from existing prompt tuning

A major purpose of this corpus is to expose prompt overfitting.

Therefore deliberately avoid recurring concepts from the previous corpus such as:

- geographic governance regions
- product limits
- compute quotas
- storage policies
- billing overrides
- refund exceptions
- incident severity
- maintenance windows
- export controls
- enterprise approvals

Do not create archaeological analogues that merely rename those structures.

The corpus should have its own natural information topology.

## Output structure

Produce a repository-ready structure similar to:

corpus/tell-aster/
  ...

datasets/tell-aster-eval-v1.yaml

docs/tell-aster-corpus.md

scripts/validate_tell_aster.py
or integrate validation into the repository's existing generic validators where appropriate.

Use nested directories that naturally reflect the archaeological archive, but do not make the directory hierarchy itself reveal answers.

Every Markdown document should contain its own metadata in the format expected by the existing progressive-disclosure evaluator.

If I provide an archive of the current codebase, inspect its existing corpus schema, metadata parser, dataset schema, validators, and tests first and conform to them rather than inventing incompatible formats.

## Important implementation constraint

Do not modify the runtime agent prompt in order to make it work with this corpus.

The point of this corpus is to test whether the existing generic progressive-disclosure approach generalizes.

Corpus-specific fixes must not be added to the runtime prompt.

If evaluation exposes corpus-specific assumptions in the runtime prompt, report them as failures/generalization issues instead.

## Final deliverables

Provide:

1. all 80 corpus Markdown documents;
2. metadata for all 80 documents;
3. at least 80 single-document eval cases;
4. at least 40 genuine multi-document eval cases;
5. corpus and dataset validation;
6. a concise corpus README explaining the fictional domain;
7. statistics:
   - document count
   - approximate words/characters
   - cross-reference count
   - single/multi case count
   - corpus coverage;
8. a short audit report specifically checking whether benchmark facts or retrieval hints leaked into activation metadata.

Before declaring completion, run all existing repository tests plus all corpus/dataset validators.

Do not run paid model evaluations unless I explicitly ask for them.

The highest priority is benchmark quality, not merely producing 80 files.

Provide the complete corpus as a zip file that I can extract to the repo where I want to use it, including all directories and files generated.
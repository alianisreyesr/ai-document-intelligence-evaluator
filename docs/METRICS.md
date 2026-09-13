# Metric definitions

- **Citation validity:** valid cited identifiers / all cited identifiers.
- **Evidence coverage:** expected documents cited / expected documents.
- **Groundedness proxy:** answer content tokens present in validly cited context / answer content tokens.
- **Required-fact recall:** required phrases found in the candidate answer / expected phrases.
- **Retrieval recall@k:** expected documents present in the ranked retrieved-document list / expected documents.
- **Retrieval MRR:** reciprocal rank of the first expected document in the ranked retrieved-document list.
- **Latency:** candidate response time compared with the configured maximum.
- **Estimated cost:** candidate model cost compared with the configured budget.

The pass/fail decision is a triage signal. It is not proof of truth, safety, fairness, or fitness for a consequential use.

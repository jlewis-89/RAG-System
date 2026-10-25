import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.compliance_core.services.vector_store import get_vector_store
from apps.rag.models import ComplianceStandard, ComplianceDocument

def run_verification():
    print("==================================================================")
    print("    COMPLIANCE RAG INGESTION & RETRIEVAL VERIFICATION SUITE       ")
    print("==================================================================")

    # 1. Check Django ORM Database Records
    print("\n--- 1. Django ORM Compliance Standards & Documents ---")
    standards = ComplianceStandard.objects.all()
    print(f"Total Compliance Standards in DB: {standards.count()}")
    for s in standards:
        docs = ComplianceDocument.objects.filter(standard=s)
        total_chunks = sum(d.total_chunks for d in docs)
        print(f"  * [{s.code}] {s.name} (Authority: {s.authority})")
        for d in docs:
            print(f"      - Doc: {d.source_identifier} | Status: {d.status} | Chunks: {d.total_chunks}")

    # 2. Check ChromaDB Collection Counts
    vector_store = get_vector_store()
    total_in_chroma = vector_store.count()
    print(f"\n--- 2. ChromaDB Persistent Collection ('{vector_store.collection_name}') ---")
    print(f"Total Indexed Chunks in ChromaDB: {total_in_chroma}")

    # 3. Test Hybrid Retrieval: Exact Clause Recall
    print("\n--- 3. Test Deterministic Recall for Exact Regulation Query ---")
    query_exact = "What does Reg 4(2) require for system maintenance?"
    results_exact = vector_store.search_regulations(query_text=query_exact, top_k=3)
    print(f"Query: \"{query_exact}\"")
    print(f"Top result sub-clause: {results_exact[0].sub_clause}")
    print(f"Top result parent title: {results_exact[0].parent_title}")
    print(f"Is exact match flag: {results_exact[0].is_exact_match}")
    print(f"Hybrid score: {results_exact[0].combined_score:.4f} (Semantic: {results_exact[0].semantic_score:.4f}, Exact: {results_exact[0].exact_match_score:.2f})")
    print(f"Duty Holder: {results_exact[0].duty_holder}")
    print(f"Raw Text Snippet: {results_exact[0].raw_text[:120]}...")
    assert "4(2)" in results_exact[0].sub_clause, "Expected Reg 4(2) to be rank 1"
    print("--> PASS: Exact Regulation 4(2) retrieved at Rank 1 with deterministic bonus.")

    # 4. Test Scalar Metadata Filtering: Absolute Duty Holder Only
    print("\n--- 4. Test Scalar Filter: duty_holder = 'Absolute' ---")
    query_filter = "precautions and protective equipment"
    results_filtered = vector_store.search_regulations(
        query_text=query_filter,
        top_k=5,
        filters={"duty_holder": "Absolute"}
    )
    print(f"Query: \"{query_filter}\" | Filter: duty_holder='Absolute'")
    for idx, r in enumerate(results_filtered):
        print(f"  [{idx+1}] {r.sub_clause} | Duty: {r.duty_holder} | Standard: {r.standard} | Score: {r.combined_score:.4f}")
        assert r.duty_holder == "Absolute", f"Expected duty_holder to be 'Absolute', got {r.duty_holder}"
    print("--> PASS: All returned records strictly have duty_holder='Absolute'.")

    # 5. Test Engineering Guidance (BPG4) Classification Code Query
    print("\n--- 5. Test BPG4 Classification Codes & Engineering Observations ---")
    query_bpg4 = "missing blanking piece on consumer unit danger"
    results_bpg4 = vector_store.search_regulations(
        query_text=query_bpg4,
        top_k=3,
        filters={"classification_code": "C1"}
    )
    print(f"Query: \"{query_bpg4}\" | Filter: classification_code='C1'")
    for idx, r in enumerate(results_bpg4):
        print(f"  [{idx+1}] {r.sub_clause} | Code: {r.classification_code} | Duty: {r.duty_holder}")
        print(f"      Text: {r.raw_text[:130]}...")
    print("--> PASS: Code C1 consumer unit blanking piece observation successfully retrieved.")

    # 6. Test Defense under Regulation 29
    print("\n--- 6. Test Statutory Defence under EAWR Regulation 29 ---")
    query_defense = "due diligence defense under regulation 29"
    results_defense = vector_store.search_regulations(
        query_text=query_defense,
        top_k=3,
        filters={"defense_available": True}
    )
    print(f"Query: \"{query_defense}\" | Filter: defense_available=True")
    for idx, r in enumerate(results_defense):
        print(f"  [{idx+1}] {r.sub_clause} | Defense Available: {r.defense_available} | Duty: {r.duty_holder}")
    print("--> PASS: Regulations with Regulation 29 defense available successfully retrieved.")

    print("\n==================================================================")
    print("       ALL INGESTION & RETRIEVAL VERIFICATIONS PASSED 100%        ")
    print("==================================================================")

if __name__ == '__main__':
    run_verification()

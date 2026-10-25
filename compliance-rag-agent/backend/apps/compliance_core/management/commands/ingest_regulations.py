"""
Django Management Command: ingest_regulations
Hierarchical legal & engineering standard document parser for UK electrical compliance.
"""

import os
import json
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from apps.compliance_core.ingestion.service import DocumentIngestionService


class Command(BaseCommand):
    help = (
        "Hierarchically ingest statutory UK electrical regulations (EAWR 1989, HSE HSR25) "
        "and engineering guidance (ESF BPG4) into ChromaDB and Django ORM."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            required=True,
            help="Path to the statutory regulation or engineering guidance file (.pdf, .txt, .md)."
        )
        parser.add_argument(
            '--standard',
            type=str,
            default=None,
            help="Standard name override (e.g., 'Electricity at Work Regulations 1989', 'ESF Best Practice Guide 4')."
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help="Parse and validate chunks without persisting to ChromaDB or Django database."
        )
        parser.add_argument(
            '--store-chroma',
            action='store_true',
            default=True,
            help="Persist chunks to ChromaDB vector store (default: True, disabled if --dry-run is set)."
        )
        parser.add_argument(
            '--store-db',
            action='store_true',
            default=True,
            help="Save standard and document metadata into Django database (default: True, disabled if --dry-run is set)."
        )
        parser.add_argument(
            '--output-json',
            type=str,
            default=None,
            help="Optional file path to export parsed RegulatoryChunks as JSON."
        )
        parser.add_argument(
            '--show-chunks',
            action='store_true',
            help="Print detailed breakdown of all extracted chunks to the console."
        )

    def handle(self, *args, **options):
        file_path = options['file']
        standard_name = options.get('standard')
        dry_run = options['dry_run']
        store_chroma = False if dry_run else options['store_chroma']
        store_db = False if dry_run else options['store_db']
        output_json = options.get('output_json')
        show_chunks = options.get('show_chunks')

        resolved_path = Path(file_path).resolve()
        if not resolved_path.exists():
            raise CommandError(f"Target file does not exist: {resolved_path}")

        self.stdout.write(self.style.MIGRATE_HEADING("\n=== UK Statutory & Engineering Regulation Ingestion ==="))
        self.stdout.write(f"Source Document : {resolved_path.name}")
        self.stdout.write(f"File Path       : {resolved_path}")
        self.stdout.write(f"Dry Run Mode    : {'YES (No persistence)' if dry_run else 'NO'}")
        self.stdout.write(f"Store in Chroma : {'YES' if store_chroma else 'NO'}")
        self.stdout.write(f"Store in DB     : {'YES' if store_db else 'NO'}\n")

        service = DocumentIngestionService()

        try:
            report = service.ingest_file(
                file_path=resolved_path,
                standard_name=standard_name,
                store_chroma=store_chroma,
                store_db=store_db
            )
        except Exception as e:
            raise CommandError(f"Ingestion failed: {e}")

        # Render Summary Table
        self.stdout.write(self.style.SUCCESS(f"[SUCCESS] Successfully parsed '{report.standard_name}' in {report.duration_seconds}s"))
        self.stdout.write(f"- Document Type       : {report.document_type}")
        self.stdout.write(f"- Total Chunks Extracted: {report.total_chunks}")
        self.stdout.write(f"- Regulations Found   : {len(report.regulations_found)} ({', '.join(report.regulations_found[:8])}{'...' if len(report.regulations_found) > 8 else ''})")
        
        self.stdout.write("\nStatutory Duty Breakdown:")
        for duty, count in report.duty_breakdown.items():
            self.stdout.write(f"  * {duty:<35}: {count} clauses")

        if report.chroma_upserted:
            self.stdout.write(self.style.SUCCESS("[SUCCESS] Successfully upserted chunks to ChromaDB persistent storage."))
        if report.database_saved:
            self.stdout.write(self.style.SUCCESS("[SUCCESS] Successfully recorded standard and document in Django ORM."))

        # Export JSON if requested
        if output_json:
            out_path = Path(output_json).resolve()
            out_path.parent.mkdir(parents=True, exist_ok=True)
            with open(out_path, 'w', encoding='utf-8') as f:
                json_data = [chunk.model_dump() for chunk in report.chunks]
                json.dump(json_data, f, indent=2, ensure_ascii=False)
            self.stdout.write(self.style.SUCCESS(f"[SUCCESS] Exported {len(report.chunks)} chunks to JSON: {out_path}"))

        # Detailed Chunk Listing
        if show_chunks:
            self.stdout.write(self.style.HTTP_INFO("\n--- Detailed Regulatory Chunks Breakdown ---"))
            for idx, c in enumerate(report.chunks):
                self.stdout.write(f"\n[{idx + 1}/{len(report.chunks)}] {c.sub_clause} | {c.parent_title}")
                self.stdout.write(f"     Duty: {c.duty_holder} | Defense Reg 29: {c.defense_available}")
                preview = c.raw_text.replace('\n', ' ')[:140]
                self.stdout.write(f"     Text: \"{preview}...\"")

        self.stdout.write(self.style.SUCCESS("\n[Done] Ingestion process complete.\n"))

import json
import logging
import os
import time
from pathlib import Path
from typing import Iterable, List

from tabulate import tabulate  # Convert table arrays into Markdown tables.

from docling.backend.docling_parse_backend import DoclingParseDocumentBackend
from docling.datamodel.base_models import ConversionStatus

try:
    from docling.datamodel.document import ConversionResult
except ImportError:
    # Newer Docling releases expose ConversionResult from document_converter.
    from docling.document_converter import ConversionResult


_log = logging.getLogger(__name__)


def _process_chunk(
    pdf_paths,
    pdf_backend,
    output_dir,
    num_threads,
    metadata_lookup,
    debug_data_path,
):
    """Process one PDF chunk in a separate process.

    This helper is used only by ``PDFParser.parse_and_export_parallel``.
    Each child process creates its own ``PDFParser`` instance because the
    Docling converter/pipeline should not be shared directly across processes.
    """
    parser = PDFParser(
        pdf_backend=pdf_backend,
        output_dir=output_dir,
        num_threads=num_threads,
        csv_metadata_path=None,  # Metadata lookup is passed directly below.
    )
    parser.metadata_lookup = metadata_lookup
    parser.debug_data_path = debug_data_path
    parser.parse_and_export(pdf_paths)

    return f"Processed {len(pdf_paths)} PDFs."


class PDFParser:
    """Parse PDF reports with Docling and export project-specific JSON files."""

    def __init__(
        self,
        pdf_backend=DoclingParseDocumentBackend,
        output_dir: Path = Path("./parsed_pdfs"),
        num_threads: int = None,
        csv_metadata_path: Path = None,
    ):
        self.pdf_backend = pdf_backend
        self.output_dir = output_dir
        self.doc_converter = self._create_document_converter()
        self.num_threads = num_threads
        self.metadata_lookup = {}
        self.debug_data_path = None

        if csv_metadata_path is not None:
            self.metadata_lookup = self._parse_csv_metadata(csv_metadata_path)

        if self.num_threads is not None:
            os.environ["OMP_NUM_THREADS"] = str(self.num_threads)

    @staticmethod
    def _parse_csv_metadata(csv_path: Path) -> dict:
        """Parse CSV metadata and build a lookup dictionary keyed by sha1."""
        import csv

        metadata_lookup = {}

        with open(csv_path, "r", encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)

            for row in reader:
                # Support both old and new CSV formats.
                # Newer format: company_name; older format: name.
                company_name = row.get("company_name", row.get("name", "")).strip('"')
                metadata_lookup[row["sha1"]] = {"company_name": company_name}

        return metadata_lookup

    def _create_document_converter(self) -> "DocumentConverter":  # type: ignore
        """Create a Docling DocumentConverter with the project defaults."""
        from docling.datamodel.base_models import InputFormat
        from docling.datamodel.pipeline_options import (
            EasyOcrOptions,
            PdfPipelineOptions,
            TableFormerMode,
        )
        from docling.document_converter import DocumentConverter, PdfFormatOption
        from docling.pipeline.standard_pdf_pipeline import StandardPdfPipeline

        pipeline_options = PdfPipelineOptions()

        # OCR configuration: recognize English text and avoid forced full-page OCR.
        pipeline_options.do_ocr = True
        pipeline_options.ocr_options = EasyOcrOptions(
            lang=["en"],
            force_full_page_ocr=False,
        )

        # Table recognition configuration: enable structure extraction and cell matching.
        pipeline_options.do_table_structure = True
        pipeline_options.table_structure_options.do_cell_matching = True
        pipeline_options.table_structure_options.mode = TableFormerMode.ACCURATE

        # Local Docling model artifacts path, supplied by the environment.
        pipeline_options.artifacts_path = Path(os.getenv("DOCLING_ARTIFACTS_PATH"))

        format_options = {
            InputFormat.PDF: PdfFormatOption(
                pipeline_cls=StandardPdfPipeline,
                pipeline_options=pipeline_options,
                backend=self.pdf_backend,
            )
        }

        return DocumentConverter(format_options=format_options)

    def convert_documents(self, input_doc_paths: List[Path]) -> Iterable[ConversionResult]:
        """Convert PDF paths with Docling and return conversion results."""
        conv_results = self.doc_converter.convert_all(source=input_doc_paths)
        return conv_results

    def process_documents(self, conv_results: Iterable[ConversionResult]):
        """Process Docling conversion results and save parsed report JSON files."""
        if self.output_dir is not None:
            self.output_dir.mkdir(parents=True, exist_ok=True)

        success_count = 0
        failure_count = 0

        for conv_res in conv_results:
            if conv_res.status == ConversionStatus.SUCCESS:
                success_count += 1

                processor = JsonReportProcessor(
                    metadata_lookup=self.metadata_lookup,
                    debug_data_path=self.debug_data_path,
                )

                # Export Docling's raw dictionary and normalize page numbering before
                # assembling the project-specific report structure.
                data = conv_res.document.export_to_dict()
                normalized_data = self._normalize_page_sequence(data)
                processed_report = processor.assemble_report(conv_res, normalized_data)

                # Save the final parsed report used by downstream pipeline stages.
                # This is different from JsonReportProcessor.debug_data(), which saves
                # raw Docling debug output.
                doc_filename = conv_res.input.file.stem
                if self.output_dir is not None:
                    with (self.output_dir / f"{doc_filename}.json").open(
                        "w", encoding="utf-8"
                    ) as fp:
                        json.dump(processed_report, fp, indent=2, ensure_ascii=False)
            else:
                failure_count += 1
                _log.info(f"Document {conv_res.input.file} failed to convert.")

        _log.info(
            f"Processed {success_count + failure_count} docs, "
            f"of which {failure_count} failed"
        )

        return success_count, failure_count

    def _normalize_page_sequence(self, data: dict) -> dict:
        """Fill missing page numbers with empty page records.

        Docling output may skip pages if a page has no recognized content. This method
        keeps page numbers sequential so downstream modules can rely on page ordering.
        """
        if "content" not in data:
            return data

        normalized_data = data.copy()

        existing_pages = {page["page"] for page in data["content"]}
        max_page = max(existing_pages)

        empty_page_template = {
            "content": [],
            "page_dimensions": {},
        }

        new_content = []
        for page_num in range(1, max_page + 1):
            page_content = next(
                (page for page in data["content"] if page["page"] == page_num),
                {"page": page_num, **empty_page_template},
            )
            new_content.append(page_content)

        normalized_data["content"] = new_content
        return normalized_data

    def parse_and_export(
        self,
        input_doc_paths: List[Path] = None,
        doc_dir: Path = None,
    ):
        """Parse PDFs sequentially and export parsed report JSON files."""
        start_time = time.time()

        if input_doc_paths is None and doc_dir is not None:
            input_doc_paths = list(doc_dir.glob("*.pdf"))

        total_docs = len(input_doc_paths)
        _log.info(f"Starting to process {total_docs} documents")

        conv_results = self.convert_documents(input_doc_paths)
        success_count, failure_count = self.process_documents(conv_results=conv_results)

        elapsed_time = time.time() - start_time

        if failure_count > 0:
            error_message = f"Failed converting {failure_count} out of {total_docs} documents."
            failed_docs = "Paths of failed docs:\n" + "\n".join(
                str(path) for path in input_doc_paths
            )
            _log.error(error_message)
            _log.error(failed_docs)
            raise RuntimeError(error_message)

        _log.info(
            f"{'#' * 50}\n"
            f"Completed in {elapsed_time:.2f} seconds.\n"
            f"Successfully converted {success_count}/{total_docs} documents.\n"
            f"{'#' * 50}"
        )

    def parse_and_export_parallel(
        self,
        input_doc_paths: List[Path] = None,
        doc_dir: Path = None,
        optimal_workers: int = 10,
        chunk_size: int = None,
    ):
        """Parse PDF files in parallel using multiple processes.

        Args:
            input_doc_paths: Explicit list of PDF paths to process.
            doc_dir: Directory containing PDF files, used when ``input_doc_paths`` is None.
            optimal_workers: Number of worker processes to use. If None, use a CPU-based value.
            chunk_size: Number of PDFs assigned to each worker task.
        """
        import multiprocessing
        from concurrent.futures import ProcessPoolExecutor, as_completed

        if input_doc_paths is None and doc_dir is not None:
            input_doc_paths = list(doc_dir.glob("*.pdf"))

        total_pdfs = len(input_doc_paths)
        _log.info(f"Starting parallel processing of {total_pdfs} documents")

        cpu_count = multiprocessing.cpu_count()

        if optimal_workers is None:
            optimal_workers = min(cpu_count, total_pdfs)

        if chunk_size is None:
            chunk_size = max(1, total_pdfs // optimal_workers)

        chunks = [
            input_doc_paths[i : i + chunk_size]
            for i in range(0, total_pdfs, chunk_size)
        ]

        start_time = time.time()
        processed_count = 0

        with ProcessPoolExecutor(max_workers=optimal_workers) as executor:
            futures = [
                executor.submit(
                    _process_chunk,
                    chunk,
                    self.pdf_backend,
                    self.output_dir,
                    self.num_threads,
                    self.metadata_lookup,
                    self.debug_data_path,
                )
                for chunk in chunks
            ]

            for future in as_completed(futures):
                try:
                    result = future.result()
                    processed_count += int(result.split()[1])
                    _log.info(
                        f"{'#' * 50}\n"
                        f"{result} ({processed_count}/{total_pdfs} total)\n"
                        f"{'#' * 50}"
                    )
                except Exception as e:
                    _log.error(f"Error processing chunk: {str(e)}")
                    raise

        elapsed_time = time.time() - start_time
        _log.info(f"Parallel processing completed in {elapsed_time:.2f} seconds.")


class JsonReportProcessor:
    """Transform Docling output dictionaries into the project's parsed report format."""

    def __init__(self, metadata_lookup: dict = None, debug_data_path: Path = None):
        self.metadata_lookup = metadata_lookup or {}
        self.debug_data_path = debug_data_path

    def assemble_report(self, conv_result, normalized_data=None):
        """Assemble all sections of a parsed report.

        ``normalized_data`` is preferred when provided because it contains the same
        Docling document data with sequential page entries.
        """
        data = normalized_data if normalized_data is not None else conv_result.document.export_to_dict()

        assembled_report = {}
        assembled_report["metainfo"] = self.assemble_metainfo(data)
        assembled_report["content"] = self.assemble_content(data)
        assembled_report["tables"] = self.assemble_tables(conv_result.document, data)
        assembled_report["pictures"] = self.assemble_pictures(data)

        self.debug_data(data)
        return assembled_report

    def assemble_metainfo(self, data):
        """Build report-level metadata."""
        metainfo = {}

        sha1_name = data["origin"]["filename"].rsplit(".", 1)[0]
        metainfo["sha1_name"] = sha1_name
        metainfo["pages_amount"] = len(data.get("pages", []))
        metainfo["text_blocks_amount"] = len(data.get("texts", []))
        metainfo["tables_amount"] = len(data.get("tables", []))
        metainfo["pictures_amount"] = len(data.get("pictures", []))
        metainfo["equations_amount"] = len(data.get("equations", []))
        metainfo["footnotes_amount"] = len(
            [t for t in data.get("texts", []) if t.get("label") == "footnote"]
        )

        if self.metadata_lookup and sha1_name in self.metadata_lookup:
            csv_meta = self.metadata_lookup[sha1_name]
            metainfo["company_name"] = csv_meta["company_name"]

        return metainfo

    def process_table(self, table_data):
        """Placeholder for optional table post-processing."""
        return "processed_table_content"

    def debug_data(self, data):
        """Save raw Docling output for debugging when a debug path is configured."""
        if self.debug_data_path is None:
            return

        doc_name = data["name"]
        path = self.debug_data_path / f"{doc_name}.json"
        path.parent.mkdir(parents=True, exist_ok=True)

        with path.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def expand_groups(self, body_children, groups):
        """Expand group references in Docling body children.

        Docling may represent a section/list/group as a group node whose children are
        referenced indirectly. This method flattens those references while preserving
        group metadata on each expanded child.
        """
        expanded_children = []

        for item in body_children:
            if isinstance(item, dict) and "$ref" in item:
                ref = item["$ref"]
                ref_type, ref_num = ref.split("/")[-2:]
                ref_num = int(ref_num)

                if ref_type == "groups":
                    group = groups[ref_num]
                    group_id = ref_num
                    group_name = group.get("name", "")
                    group_label = group.get("label", "")

                    for child in group["children"]:
                        child_copy = child.copy()
                        child_copy["group_id"] = group_id
                        child_copy["group_name"] = group_name
                        child_copy["group_label"] = group_label
                        expanded_children.append(child_copy)
                else:
                    expanded_children.append(item)
            else:
                expanded_children.append(item)

        return expanded_children

    def _process_text_reference(self, ref_num, data):
        """Create a content item from a Docling text reference."""
        text_item = data["texts"][ref_num]
        item_type = text_item["label"]

        content_item = {
            "text": text_item.get("text", ""),
            "type": item_type,
            "text_id": ref_num,
        }

        orig_content = text_item.get("orig", "")
        if orig_content != text_item.get("text", ""):
            content_item["orig"] = orig_content

        if "enumerated" in text_item:
            content_item["enumerated"] = text_item["enumerated"]

        if "marker" in text_item:
            content_item["marker"] = text_item["marker"]

        return content_item

    def assemble_content(self, data):
        """Assemble page-level content from Docling body references."""
        pages = {}

        body_children = data["body"]["children"]
        groups = data.get("groups", [])
        expanded_body_children = self.expand_groups(body_children, groups)

        for item in expanded_body_children:
            if isinstance(item, dict) and "$ref" in item:
                ref = item["$ref"]
                ref_type, ref_num = ref.split("/")[-2:]
                ref_num = int(ref_num)

                if ref_type == "texts":
                    text_item = data["texts"][ref_num]
                    content_item = self._process_text_reference(ref_num, data)

                    if "group_id" in item:
                        content_item["group_id"] = item["group_id"]
                        content_item["group_name"] = item["group_name"]
                        content_item["group_label"] = item["group_label"]

                    if "prov" in text_item and text_item["prov"]:
                        page_num = text_item["prov"][0]["page_no"]

                        if page_num not in pages:
                            pages[page_num] = {
                                "page": page_num,
                                "content": [],
                                "page_dimensions": text_item["prov"][0].get("bbox", {}),
                            }

                        pages[page_num]["content"].append(content_item)

                elif ref_type == "tables":
                    table_item = data["tables"][ref_num]
                    content_item = {"type": "table", "table_id": ref_num}

                    if "prov" in table_item and table_item["prov"]:
                        page_num = table_item["prov"][0]["page_no"]

                        if page_num not in pages:
                            pages[page_num] = {
                                "page": page_num,
                                "content": [],
                                "page_dimensions": table_item["prov"][0].get("bbox", {}),
                            }

                        pages[page_num]["content"].append(content_item)

                elif ref_type == "pictures":
                    picture_item = data["pictures"][ref_num]
                    content_item = {"type": "picture", "picture_id": ref_num}

                    if "prov" in picture_item and picture_item["prov"]:
                        page_num = picture_item["prov"][0]["page_no"]

                        if page_num not in pages:
                            pages[page_num] = {
                                "page": page_num,
                                "content": [],
                                "page_dimensions": picture_item["prov"][0].get("bbox", {}),
                            }

                        pages[page_num]["content"].append(content_item)

        sorted_pages = [pages[page_num] for page_num in sorted(pages.keys())]
        return sorted_pages

    def assemble_tables(self, doc, data):
        """Assemble table metadata and table representations.

        """
        assembled_tables = []

        for i, table in enumerate(doc.tables):
            table_json_obj = table.model_dump()
            table_md = self._table_to_md(table_json_obj)

            try:
                table_html = table.export_to_html(doc=doc)
            except TypeError:
                # Compatibility fallback for older Docling versions whose
                # export_to_html() signature does not accept a doc argument.
                table_html = table.export_to_html()

            table_data = data["tables"][i]
            table_page_num = table_data["prov"][0]["page_no"]
            table_bbox = table_data["prov"][0]["bbox"]
            table_bbox = [
                table_bbox["l"],
                table_bbox["t"],
                table_bbox["r"],
                table_bbox["b"],
            ]

            nrows = table_data["data"]["num_rows"]
            ncols = table_data["data"]["num_cols"]

            ref_num = table_data["self_ref"].split("/")[-1]
            ref_num = int(ref_num)

            table_obj = {
                "table_id": ref_num,
                "page": table_page_num,
                "bbox": table_bbox,
                "#-rows": nrows,
                "#-cols": ncols,
                "markdown": table_md,
                "html": table_html,
                "json": table_json_obj,
            }
            assembled_tables.append(table_obj)

        return assembled_tables

    def _table_to_md(self, table):
        """Convert a Docling table model dump into a GitHub-style Markdown table."""
        table_data = []

        for row in table["data"]["grid"]:
            table_row = [cell["text"] for cell in row]
            table_data.append(table_row)

        if len(table_data) > 1 and len(table_data[0]) > 0:
            try:
                md_table = tabulate(
                    table_data[1:],
                    headers=table_data[0],
                    tablefmt="github",
                )
            except ValueError:
                md_table = tabulate(
                    table_data[1:],
                    headers=table_data[0],
                    tablefmt="github",
                    disable_numparse=True,
                )
        else:
            md_table = tabulate(table_data, tablefmt="github")

        return md_table

    def assemble_pictures(self, data):
        """Assemble picture metadata and linked child text references."""
        assembled_pictures = []

        for i, picture in enumerate(data["pictures"]):
            children_list = self._process_picture_block(picture, data)

            ref_num = picture["self_ref"].split("/")[-1]
            ref_num = int(ref_num)

            picture_page_num = picture["prov"][0]["page_no"]
            picture_bbox = picture["prov"][0]["bbox"]
            picture_bbox = [
                picture_bbox["l"],
                picture_bbox["t"],
                picture_bbox["r"],
                picture_bbox["b"],
            ]

            picture_obj = {
                "picture_id": ref_num,
                "page": picture_page_num,
                "bbox": picture_bbox,
                "children": children_list,
            }
            assembled_pictures.append(picture_obj)

        return assembled_pictures

    def _process_picture_block(self, picture, data):
        """Resolve text children attached to a picture block."""
        children_list = []

        for item in picture["children"]:
            if isinstance(item, dict) and "$ref" in item:
                ref = item["$ref"]
                ref_type, ref_num = ref.split("/")[-2:]
                ref_num = int(ref_num)

                if ref_type == "texts":
                    content_item = self._process_text_reference(ref_num, data)
                    children_list.append(content_item)

        return children_list

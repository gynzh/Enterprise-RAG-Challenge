from __future__ import annotations # 让 Python 延迟解析类型注解，从而更方便地在注解里引用尚未完全定义的类或类型。

import sys
from pathlib import Path
from typing import Any
import os

import click


PROJECT_ROOT = Path(__file__).resolve().parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def load_pipeline_objects() -> tuple[Any, dict[str, Any], dict[str, Any]]:
    """
    Lazily import the heavy pipeline module.

    This keeps `python main.py --help` usable even before large runtime
    dependencies such as docling/faiss/langchain are installed. The full
    pipeline dependency tree is imported only when a real command is executed.
    """
    try:
        from src.pipeline import Pipeline, configs, preprocess_configs
    except ModuleNotFoundError as exc:
        missing_module = exc.name or "unknown"
        raise click.ClickException(
            "Missing Python module: "
            f"{missing_module}\n\n"
            "Please make sure you are using the uv-managed environment and run:\n"
            "    uv sync --all-groups\n\n"
            "If you only need the core pipeline dependencies, run:\n"
            "    uv sync\n\n"
            f"Project root: {PROJECT_ROOT}\n"
            f"Python executable: {sys.executable}"
        ) from exc

    return Pipeline, configs, preprocess_configs


def resolve_root_path(root: str | None) -> Path:
    """Resolve the data root path used by the pipeline."""
    if root:
        candidate = Path(root).expanduser()
        if not candidate.is_absolute():
            candidate = PROJECT_ROOT / candidate
        return candidate.resolve()

    return Path.cwd().resolve()


def root_option(function):
    """Reusable Click option for the dataset root directory."""
    return click.option(
        "--root",
        type=click.Path(file_okay=False, dir_okay=True, path_type=str),
        default=None,
        help=(
            "Dataset root directory. Defaults to the current working directory. "
            "For this repository, `--root data/test_set` is usually what you want."
        ),
    )(function)
    """click.option(...) 先创建一个装饰器；
然后这个装饰器再去装饰传进来的 function；
最后返回加好 --root 参数的新函数。"""


@click.group()
def cli():
    """Pipeline command line interface for processing PDF reports and questions."""

def resolve_model_path(output_dir: str | None) -> Path | None:
    """Resolve the directory used to store Docling models."""
    if output_dir is None:
        output_dir = os.environ.get("DOCLING_ARTIFACTS_PATH")

    if output_dir is None:
        return None

    candidate = Path(output_dir).expanduser()

    if not candidate.is_absolute():
        candidate = PROJECT_ROOT / candidate

    return candidate.resolve()

@cli.command()
@click.option(
    "--output-dir",
    "-o",
    type=click.Path(file_okay=False, dir_okay=True, path_type=str),
    default=None,
    help=(
        "Directory to save Docling models. "
        "If omitted, uses Docling's default cache."
    ),
)
def download_models(output_dir: str | None):
    """Download required Docling models explicitly."""
    import subprocess

    cmd = ["docling-tools", "models", "download"]

    if output_dir is not None:
        model_path = Path(output_dir).expanduser()

        if not model_path.is_absolute():
            model_path = PROJECT_ROOT / model_path

        model_path = model_path.resolve()
        model_path.mkdir(parents=True, exist_ok=True)

        cmd.extend(["-o", str(model_path)])

        click.echo(f"Downloading Docling models to: {model_path}")
    else:
        model_path = None
        click.echo("Downloading Docling models to Docling's default cache...")

    try:
        subprocess.run(cmd, check=True)
    except FileNotFoundError as exc:
        raise click.ClickException(
            "Cannot find 'docling-tools'.\n\n"
            "Please make sure the virtual environment is activated "
            "and Docling is installed:\n"
            "  pip install -r requirements.txt\n"
            "  pip install -e .\n\n"
            f"Python executable: {sys.executable}"
        ) from exc
    except subprocess.CalledProcessError as exc:
        raise click.ClickException(
            f"Docling model download failed with exit code {exc.returncode}."
        ) from exc

    if model_path is not None:
        click.echo(f"Docling models downloaded to: {model_path}")
        click.echo(
            "When parsing PDFs, set:\n"
            f"  DOCLING_ARTIFACTS_PATH={model_path}"
        )
    else:
        click.echo("Docling models downloaded.")

@cli.command()
@root_option
@click.option(
    "--parallel/--sequential",
    default=True,
    help="Run parsing in parallel or sequential mode",
)
@click.option(
    "--chunk-size",
    default=2,
    show_default=True,
    help="Number of PDFs to process in each worker",
)
@click.option(
    "--max-workers",
    default=10,
    show_default=True,
    help="Number of parallel worker processes",
)
def parse_pdfs(root: str | None, parallel: bool, chunk_size: int, max_workers: int):
    """Parse PDF reports with optional parallel processing."""
    Pipeline, _, _ = load_pipeline_objects()
    root_path = resolve_root_path(root)
    pipeline = Pipeline(root_path)

    click.echo(
        "Parsing PDFs "
        f"from {root_path} "
        f"(parallel={parallel}, chunk_size={chunk_size}, max_workers={max_workers})"
    )
    pipeline.parse_pdf_reports(
        parallel=parallel,
        chunk_size=chunk_size,
        max_workers=max_workers,
    )


@cli.command()
@root_option
@click.option(
    "--max-workers",
    default=10,
    show_default=True,
    help="Number of workers for table serialization",
)
def serialize_tables(root: str | None, max_workers: int):
    """Serialize tables in parsed reports using parallel threading."""
    Pipeline, _, _ = load_pipeline_objects()
    root_path = resolve_root_path(root)
    pipeline = Pipeline(root_path)

    click.echo(f"Serializing tables from {root_path} (max_workers={max_workers})...")
    pipeline.serialize_tables(max_workers=max_workers)


@cli.command()
@root_option
@click.option(
    "--config",
    type=click.Choice(["ser_tab", "no_ser_tab"]),
    default="no_ser_tab",
    show_default=True,
    help="Configuration preset to use",
)
def process_reports(root: str | None, config: str):
    """Process parsed reports through the pipeline stages."""
    Pipeline, _, preprocess_configs = load_pipeline_objects()
    root_path = resolve_root_path(root)
    run_config = preprocess_configs[config]
    pipeline = Pipeline(root_path, run_config=run_config)

    click.echo(f"Processing parsed reports from {root_path} (config={config})...")
    pipeline.process_parsed_reports()


@cli.command()
@root_option
@click.option(
    "--config",
    type=click.Choice(["ser_tab", "no_ser_tab"]),
    default="no_ser_tab",
    show_default=True,
    help="Configuration preset to use",
)
@click.option(
    "--model",
    default="all-MiniLM-L6-v2",
    show_default=True,
    help="Free embedding model to use",
)
def process_reports_free(root: str | None, config: str, model: str):
    """Process parsed reports using free Hugging Face embeddings instead of OpenAI."""
    Pipeline, _, preprocess_configs = load_pipeline_objects()
    root_path = resolve_root_path(root)
    run_config = preprocess_configs[config]
    pipeline = Pipeline(root_path, run_config=run_config)

    click.echo(
        "Processing parsed reports "
        f"from {root_path} with free embeddings "
        f"(config={config}, model={model})..."
    )
    pipeline.process_parsed_reports_free(model_name=model)


@cli.command()
@root_option
@click.option(
    "--config",
    type=click.Choice(
        [
            "base",
            "pdr",
            "max",
            "max_no_ser_tab",
            "max_nst_o3m",
            "max_st_o3m",
            "ibm_llama70b",
            "ibm_llama8b",
            "gemini_thinking",
        ]
    ),
    default="base",
    show_default=True,
    help="Configuration preset to use",
)
def process_questions(root: str | None, config: str):
    """Process questions using the pipeline."""
    Pipeline, configs, _ = load_pipeline_objects()
    root_path = resolve_root_path(root)
    run_config = configs[config]
    pipeline = Pipeline(root_path, run_config=run_config)

    click.echo(f"Processing questions from {root_path} (config={config})...")
    pipeline.process_questions()


if __name__ == "__main__":
    cli()

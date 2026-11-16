"""Execute dated notebooks in place and preserve their real outputs.

This runner is deliberately in-process. It works in restricted environments
where Jupyter's ZeroMQ kernel transport cannot open local sockets.
"""

from __future__ import annotations

import argparse
import ast
import base64
import contextlib
import io
import os
import traceback
from pathlib import Path

import nbformat


ROOT = Path(__file__).resolve().parents[1]


def run_code(source: str, namespace: dict):
    """Run one cell, returning Jupyter-compatible outputs."""
    outputs = []
    stdout, stderr = io.StringIO(), io.StringIO()
    tree = ast.parse(source, mode="exec")
    last_expr = None
    if tree.body and isinstance(tree.body[-1], ast.Expr):
        last_expr = ast.Expression(tree.body.pop().value)

    try:
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            if tree.body:
                exec(compile(tree, "<notebook-cell>", "exec"), namespace)
            value = eval(compile(last_expr, "<notebook-cell>", "eval"), namespace) if last_expr else None
    except Exception as exc:
        text = stdout.getvalue()
        if text:
            outputs.append(nbformat.v4.new_output("stream", name="stdout", text=text))
        outputs.append(
            nbformat.v4.new_output(
                "error",
                ename=type(exc).__name__,
                evalue=str(exc),
                traceback=traceback.format_exc().splitlines(),
            )
        )
        return outputs, exc

    if stdout.getvalue():
        outputs.append(nbformat.v4.new_output("stream", name="stdout", text=stdout.getvalue()))
    if stderr.getvalue():
        outputs.append(nbformat.v4.new_output("stream", name="stderr", text=stderr.getvalue()))
    if value is not None:
        outputs.append(
            nbformat.v4.new_output(
                "execute_result",
                data={"text/plain": repr(value)},
                metadata={},
                execution_count=None,
            )
        )

    # Matplotlib figures are embedded in addition to the higher-resolution PNG
    # files explicitly saved by each notebook.
    if "plt" in namespace:
        plt = namespace["plt"]
        for number in list(plt.get_fignums()):
            fig = plt.figure(number)
            buffer = io.BytesIO()
            fig.savefig(buffer, format="png", dpi=120, bbox_inches="tight")
            outputs.append(
                nbformat.v4.new_output(
                    "display_data",
                    data={"image/png": base64.b64encode(buffer.getvalue()).decode("ascii")},
                    metadata={},
                )
            )
        plt.close("all")
    return outputs, None


def execute_notebook(path: Path):
    nb = nbformat.read(path, as_version=4)
    namespace = {"__name__": "__main__"}
    count = 0
    previous = Path.cwd()
    os.chdir(path.parent)
    try:
        for cell in nb.cells:
            if cell.cell_type != "code":
                continue
            count += 1
            cell.execution_count = count
            cell.outputs, error = run_code(cell.source, namespace)
            if error:
                nbformat.write(nb, path)
                raise error
    finally:
        os.chdir(previous)
    nbformat.write(nb, path)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", required=True)
    parser.add_argument(
        "--unexecuted-only",
        action="store_true",
        help="Skip notebooks that already contain an execution count.",
    )
    args = parser.parse_args()

    paths = sorted(ROOT.glob(f"*/{args.date}-*/notebook.ipynb"))
    if args.unexecuted_only:
        paths = [
            path for path in paths
            if not any(
                cell.get("execution_count") is not None
                for cell in nbformat.read(path, as_version=4).cells
                if cell.cell_type == "code"
            )
        ]
    if not paths:
        raise SystemExit(f"No matching notebooks found for {args.date}")

    failures = []
    for path in paths:
        print(f"RUN  {path.relative_to(ROOT)}", flush=True)
        try:
            execute_notebook(path)
            print("PASS", flush=True)
        except Exception as exc:
            failures.append((path, exc))
            print(f"FAIL {type(exc).__name__}: {exc}", flush=True)

    if failures:
        detail = "\n".join(f"{p}: {e}" for p, e in failures)
        raise SystemExit(f"{len(failures)} notebook(s) failed:\n{detail}")


if __name__ == "__main__":
    main()

import asyncio
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from pathlib import Path, PurePosixPath
from typing import Any, cast

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import BaseTool, tool
from loguru import logger
from pydantic_monty import (
    Monty,
    MontyComplete,
    MontyFutureSnapshot,
    MontySnapshot,
    OsFunction,
    ResourceLimits,
    StatResult,
)
from pydantic_monty.os_access import AbstractOS

from joi_agent_langgraph2.config import settings
from joi_agent_langgraph2.tools import MUTATION_TOOLS

MAX_ITERATIONS = 50
RESOURCE_LIMITS: ResourceLimits = {"max_duration_secs": 60.0, "max_recursion_depth": 100}


class DiskSandboxOS(AbstractOS):
    """Routes Monty Path operations to a real directory on disk with path-traversal protection."""

    def __init__(self, sandbox: Path):
        self._sandbox = sandbox.resolve()

    def ensure_sandbox(self):
        self._sandbox.mkdir(parents=True, exist_ok=True)

    def _real(self, vpath: PurePosixPath) -> Path:
        real = (self._sandbox / vpath).resolve()
        if not str(real).startswith(str(self._sandbox)):
            raise PermissionError(f"Path escapes sandbox: {vpath}")
        return real

    def path_exists(self, path: PurePosixPath) -> bool:
        return self._real(path).exists()

    def path_is_file(self, path: PurePosixPath) -> bool:
        return self._real(path).is_file()

    def path_is_dir(self, path: PurePosixPath) -> bool:
        return self._real(path).is_dir()

    def path_is_symlink(self, path: PurePosixPath) -> bool:
        return self._real(path).is_symlink()

    def path_read_text(self, path: PurePosixPath) -> str:
        return self._real(path).read_text()

    def path_read_bytes(self, path: PurePosixPath) -> bytes:
        return self._real(path).read_bytes()

    def path_write_text(self, path: PurePosixPath, data: str) -> int:
        p = self._real(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        return p.write_text(data)

    def path_write_bytes(self, path: PurePosixPath, data: bytes) -> int:
        p = self._real(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        return p.write_bytes(data)

    def path_mkdir(self, path: PurePosixPath, parents: bool, exist_ok: bool) -> None:
        self._real(path).mkdir(parents=parents, exist_ok=exist_ok)

    def path_unlink(self, path: PurePosixPath, *, missing_ok: bool = False) -> None:
        self._real(path).unlink(missing_ok=missing_ok)

    def path_rmdir(self, path: PurePosixPath) -> None:
        self._real(path).rmdir()

    def path_iterdir(self, path: PurePosixPath) -> list[PurePosixPath]:
        return [PurePosixPath(p.name) for p in self._real(path).iterdir()]

    def path_stat(self, path: PurePosixPath) -> StatResult:
        s = self._real(path).stat()
        return StatResult.file_stat(size=s.st_size, mode=s.st_mode, mtime=s.st_mtime)

    def path_rename(self, path: PurePosixPath, target: PurePosixPath) -> None:
        self._real(path).rename(self._real(target))

    def path_resolve(self, path: PurePosixPath) -> str:
        return str(PurePosixPath("/") / self._real(path).relative_to(self._sandbox))

    def path_absolute(self, path: PurePosixPath) -> str:
        return self.path_resolve(path)

    def getenv(self, key: str, default: str | None = None) -> str | None:
        return default

    def get_environ(self) -> dict[str, str]:
        return {}


def create_interpreter_tool(tools: list[BaseTool], name: str = "run_code", description: str | None = None) -> BaseTool:
    tool_map = {t.name: t for t in tools}
    function_names = list(tool_map.keys())

    default_description = (
        "Execute Python code in a sandboxed interpreter. All your other tools are available as "
        "functions with the same names and arguments — call them exactly as you would via tool_call. "
        "Path operations (read_text, write_text, iterdir, mkdir, etc.) work naturally via pathlib "
        "on your persistent home directory. json module is available. Last expression is the return value."
    )

    @tool(name, description=description or default_description)
    async def interpreter(code: str) -> str:
        """Execute Python code in a sandboxed interpreter."""
        from langgraph.config import get_config, get_stream_writer

        try:
            writer = get_stream_writer()
        except Exception:
            writer = None

        config = get_config()
        configurable = config.get("configurable", {})
        user_id = configurable.get("user_id", "default")
        sandbox = settings.data_dir / "files" / user_id
        os_access = DiskSandboxOS(sandbox)

        return await _run_monty_loop(
            code=code,
            function_names=function_names,
            tool_map=tool_map,
            os_access=os_access,
            config=config,
            writer=writer,
        )

    return interpreter


async def _run_monty_loop(
    code: str,
    function_names: list[str],
    tool_map: dict[str, BaseTool],
    os_access: DiskSandboxOS,
    config: RunnableConfig | None = None,
    writer: Any | None = None,
) -> str:
    try:
        m = Monty(code, external_functions=function_names)
    except Exception as e:
        return f"SyntaxError: {e}"

    loop = asyncio.get_running_loop()
    with ThreadPoolExecutor() as pool:

        async def in_pool(func):
            return await loop.run_in_executor(pool, func)

        await in_pool(os_access.ensure_sandbox)

        try:
            state = await in_pool(partial(m.start, limits=RESOURCE_LIMITS))
        except Exception as e:
            return f"RuntimeError on start: {e}"

        for _ in range(MAX_ITERATIONS):
            if isinstance(state, MontyComplete):
                return str(state.output)

            if isinstance(state, MontyFutureSnapshot):
                logger.warning("Unexpected MontyFutureSnapshot in interpreter loop")
                return "Error: unexpected future state"

            assert isinstance(state, MontySnapshot)

            if state.is_os_function:
                os_func = cast(OsFunction, state.function_name)
                try:
                    result = await in_pool(partial(os_access, os_func, state.args, state.kwargs))
                    state = await in_pool(partial(state.resume, return_value=result))
                except Exception as e:
                    state = await in_pool(partial(state.resume, exception=e))
                continue

            fn_name = state.function_name
            t = tool_map.get(fn_name)
            if not t:
                state = await in_pool(partial(state.resume, exception=KeyError(f"Unknown function: {fn_name}")))
                continue

            if fn_name in MUTATION_TOOLS:
                logger.warning(f"Interpreter calling mutation tool without HITL: {fn_name}")

            if writer:
                args_str = ", ".join(f"{v}" for v in state.kwargs.values())
                writer({"type": "tool_start", "tool": fn_name, "display": f"{fn_name}({args_str})"})

            try:
                result = await t.ainvoke(state.kwargs, config=config)
                if writer:
                    writer({"type": "tool_done", "tool": fn_name})
                state = await in_pool(partial(state.resume, return_value=result))
            except Exception as e:
                if writer:
                    writer({"type": "tool_error", "tool": fn_name, "error": str(e)})
                logger.warning(f"Interpreter tool {fn_name} failed: {e}")
                state = await in_pool(partial(state.resume, exception=e))

    return "Error: interpreter exceeded maximum iteration limit"

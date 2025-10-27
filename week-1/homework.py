import io
from typing import Iterable, Callable, List, Dict, Any
import zipfile
import traceback
from dataclasses import dataclass
import frontmatter

import requests


@dataclass
class RawRepositoryFile:
    filename: str
    content: str


class GithubRepositoryDataReader:
    def __init__(self,
                repo_owner: str,
                repo_name: str,
                allowed_extensions: Iterable[str] | None = None,
                filename_filter: Callable[[str], bool] | None = None
        ):
        prefix = "https://codeload.github.com"
        self.url = (
            f"{prefix}/{repo_owner}/{repo_name}/zip/refs/heads/main"
        )

        if allowed_extensions is not None:
            self.allowed_extensions = {ext.lower() for ext in allowed_extensions}

        if filename_filter is None:
            self.filename_filter = lambda filepath: True
        else:
            self.filename_filter = filename_filter

    def read(self) -> list[RawRepositoryFile]:
        resp = requests.get(self.url)
        if resp.status_code != 200:
            raise Exception(f"Failed to download repository: {resp.status_code}")

        zf = zipfile.ZipFile(io.BytesIO(resp.content))
        repository_data = self._extract_files(zf)
        zf.close()

        return repository_data

    def _extract_files(self, zf: zipfile.ZipFile) -> list[RawRepositoryFile]:
        data = []

        for file_info in zf.infolist():
            filepath = self._normalize_filepath(file_info.filename)

            if self._should_skip_file(filepath):
                continue

            try:
                with zf.open(file_info) as f_in:
                    content = f_in.read().decode("utf-8", errors="ignore")
                    if content is not None:
                        content = content.strip()

                    file = RawRepositoryFile(
                        filename=filepath,
                        content=content
                    )
                    data.append(file)

            except Exception as e:
                print(f"Error processing {file_info.filename}: {e}")
                traceback.print_exc()
                continue

        return data

    def _should_skip_file(self, filepath: str) -> bool:
        filepath = filepath.lower()

        # directory
        if filepath.endswith("/"):
            return True

        # hidden file
        filename = filepath.split("/")[-1]
        if filename.startswith("."):
            return True

        if self.allowed_extensions:
            ext = self._get_extension(filepath)
            if ext not in self.allowed_extensions:
                return True

        if not self.filename_filter(filepath):
            return True

        return False

    def _get_extension(self, filepath: str) -> str:
        filename = filepath.lower().split("/")[-1]
        if "." in filename:
            return filename.rsplit(".", maxsplit=1)[-1]
        else:
            return ""

    def _normalize_filepath(self, filepath: str) -> str:
        parts = filepath.split("/", maxsplit=1)
        if len(parts) > 1:
            return parts[1]
        else:
            return parts[0]
        
def filename_filter(filename: str) -> bool:
    if filename.startswith('_podcast/') and not '_template' in filename:
        return True
    return False

def read_github_data(repo_owner: str, repo_name: str,  ) -> List[RawRepositoryFile]:
    allowed_extensions = {"md", "mdx"}

    reader = GithubRepositoryDataReader(
        repo_owner,
        repo_name,
        allowed_extensions=allowed_extensions,
        filename_filter=filename_filter
    )
    
    return reader.read()


def parse_data(data_raw: List[RawRepositoryFile]) -> List[Dict[str, Any]]:
    data_parsed = []
    for f in data_raw:
        post = frontmatter.loads(f.content)
        data = post.to_dict()
        data['filename'] = f.filename
        data_parsed.append(data)

    return data_parsed


def sliding_window(
        seq: Iterable[Any],
        size: int,
        step: int
    ) -> List[Dict[str, Any]]:
    if size <= 0 or step <= 0:
        raise ValueError("size and step must be positive")

    n = len(seq)
    result = []
    for i in range(0, n, step):
        batch = seq[i:i+size]
        result.append({'start': i, 'content': batch})
        if i + size > n:
            break

    return result


def chunk_documents(
        documents: Iterable[Dict[str, str]],
        size: int = 2000,
        step: int = 1000,
        content_field_name: str = 'content'
) -> List[Dict[str, str]]:
    results = []

    for doc in documents:
        doc_copy = doc.copy()
        doc_content = doc_copy.pop(content_field_name)
        chunks = sliding_window(doc_content, size=size, step=step)
        for chunk in chunks:
            chunk.update(doc_copy)
        results.extend(chunks)

    return results
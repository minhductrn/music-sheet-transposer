"""Bounded, in-memory MusicXML container decoding for recognition providers."""

from pathlib import Path
import stat
import struct
from zipfile import BadZipFile, ZipFile, ZipInfo, ZIP_DEFLATED, ZIP_STORED
from xml.parsers import expat
import xml.etree.ElementTree as ET
import zlib

from app.music.recognition.errors import RecognitionError


_MANIFEST = "META-INF/container.xml"
_MUSICXML_MIME = "application/vnd.recordare.musicxml+xml"
_MXL_MIME = b"application/vnd.recordare.musicxml"
_MAX_MANIFEST_BYTES = 64 * 1024
_CHUNK_BYTES = 64 * 1024


def _invalid() -> RecognitionError:
    return RecognitionError("Recognition produced a malformed or unsafe MusicXML archive.", 502)


def _safe_path(name: str, *, directory: bool = False) -> None:
    # ZIP paths are POSIX relative paths, not URLs or host filesystem paths.
    path = name[:-1] if directory and name.endswith("/") else name
    if (
        not path or "\\" in path or ":" in path
        or any(ord(character) < 32 or ord(character) == 127 for character in path)
        or any(part in ("", ".", "..") for part in path.split("/"))
    ):
        raise _invalid()


def _members(archive: ZipFile, max_bytes: int, max_members: int) -> dict[str, ZipInfo]:
    entries = archive.infolist()
    if not entries or len(entries) > max_members:
        raise _invalid()
    if min(entry.header_offset for entry in entries) != 0:
        raise _invalid()
    members: dict[str, ZipInfo] = {}
    total_bytes = 0
    paths: set[str] = set()
    for entry in entries:
        _safe_path(entry.orig_filename, directory=entry.is_dir())
        canonical = entry.filename.rstrip("/")
        if canonical in paths or entry.orig_filename != entry.filename:
            raise _invalid()
        paths.add(canonical)
        mode = stat.S_IFMT(entry.external_attr >> 16)
        if mode not in (0, stat.S_IFREG, stat.S_IFDIR):
            raise _invalid()
        if (
            (mode == stat.S_IFDIR or entry.external_attr & 0x10) and not entry.is_dir()
            or mode == stat.S_IFREG and entry.is_dir()
        ):
            raise _invalid()
        if entry.flag_bits & (1 | 64) or entry.compress_type not in (ZIP_STORED, ZIP_DEFLATED):
            raise _invalid()
        if entry.is_dir() and entry.file_size:
            raise _invalid()
        total_bytes += entry.file_size
        if total_bytes > max_bytes:
            raise RecognitionError("Recognition archive exceeds the decompressed size limit.", 502)
        members[entry.filename] = entry
    # A file cannot also act as a parent directory for another ZIP member.
    for name in members:
        parts = name.rstrip("/").split("/")
        if any("/".join(parts[:index]) in members for index in range(1, len(parts))):
            raise _invalid()
    return members


def _read_member(archive: ZipFile, entry: ZipInfo, limit: int, *, retain: bool = True) -> bytes:
    if entry.file_size > limit:
        raise _invalid()
    contents = bytearray()
    size = 0
    with archive.open(entry) as stream:
        while chunk := stream.read(min(_CHUNK_BYTES, limit - size + 1)):
            size += len(chunk)
            if size > limit:
                raise _invalid()
            if retain:
                contents.extend(chunk)
    # Reading through EOF verifies CRCs and local headers via Python's ZIP reader.
    if size != entry.file_size:
        raise _invalid()
    return bytes(contents)


def _primary_score(manifest: bytes, members: dict[str, ZipInfo]) -> str:
    validator = expat.ParserCreate()

    def reject_doctype(*args) -> None:
        raise _invalid()

    validator.StartDoctypeDeclHandler = reject_doctype
    validator.Parse(manifest, True)
    container = ET.fromstring(manifest)
    # MusicXML uses an unqualified container; accept the commonly used OCF form.
    namespace = "{urn:oasis:names:tc:opendocument:xmlns:container}"
    if container.tag == "container":
        namespace = ""
    elif container.tag != namespace + "container":
        raise _invalid()
    if len(container) != 1 or container[0].tag != namespace + "rootfiles":
        raise _invalid()
    if (container.text or "").strip() or (container[0].text or "").strip():
        raise _invalid()
    roots = list(container[0])
    if not roots:
        raise _invalid()
    seen: set[str] = set()
    for root in roots:
        if (
            root.tag != namespace + "rootfile" or len(root)
            or (root.text or "").strip() or (root.tail or "").strip()
        ):
            raise _invalid()
        name = root.get("full-path", "")
        _safe_path(name)
        if name in seen or name not in members or members[name].is_dir():
            raise _invalid()
        if name == "mimetype" or name.startswith("META-INF/"):
            raise _invalid()
        seen.add(name)
    if roots[0].get("media-type", _MUSICXML_MIME) != _MUSICXML_MIME:
        raise _invalid()
    return roots[0].attrib["full-path"]


def _validate_mimetype_header(path: Path, entry: ZipInfo) -> None:
    # The local header can differ from the central directory's extra fields.
    with path.open("rb") as stream:
        stream.seek(entry.header_offset)
        header = stream.read(30)
    if len(header) != 30 or header[:4] != b"PK\x03\x04":
        raise _invalid()
    extra_size = struct.unpack_from("<H", header, 28)[0]
    if extra_size:
        raise _invalid()


def read_mxl(path: Path, *, max_bytes: int, max_members: int) -> bytes:
    """Return the declared primary document verbatim; never extract to disk.

    Limits cover compressed archive size and the combined uncompressed members.
    All members are streamed to validate integrity, including unused attachments.
    The recognition service subsequently validates the primary document as MusicXML.
    """
    try:
        if path.stat().st_size > max_bytes:
            raise RecognitionError("Recognition archive exceeds the size limit.", 502)
        with ZipFile(path) as archive:
            members = _members(archive, max_bytes, max_members)
            manifest_entry = members.get(_MANIFEST)
            if manifest_entry is None or manifest_entry.is_dir():
                raise _invalid()
            manifest = _read_member(archive, manifest_entry, min(max_bytes, _MAX_MANIFEST_BYTES))
            primary = _primary_score(manifest, members)
            checked = {_MANIFEST}
            if "mimetype" in members:
                entry = members["mimetype"]
                first = min(members.values(), key=lambda member: member.header_offset)
                if entry is not first or entry.compress_type != ZIP_STORED or entry.extra:
                    raise _invalid()
                _validate_mimetype_header(path, entry)
                if _read_member(archive, entry, len(_MXL_MIME)) != _MXL_MIME:
                    raise _invalid()
                checked.add("mimetype")
            result = _read_member(archive, members[primary], max_bytes)
            checked.add(primary)
            for name, entry in members.items():
                if name not in checked:
                    _read_member(archive, entry, max_bytes, retain=False)
            return result
    except (OSError, BadZipFile, ET.ParseError, expat.ExpatError, RuntimeError, ValueError, zlib.error) as error:
        raise _invalid() from error

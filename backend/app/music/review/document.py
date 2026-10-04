"""Preserved XML tree and sidecar identities. Never write review IDs into MusicXML."""

from copy import deepcopy
from dataclasses import dataclass
from xml.etree import ElementTree as ET
from xml.parsers import expat


class ReviewError(Exception):
    def __init__(self, message: str, status_code: int = 422):
        super().__init__(message)
        self.status_code = status_code


def local(tag) -> str:
    return tag.rsplit("}", 1)[-1] if isinstance(tag, str) else ""


@dataclass
class Document:
    root: ET.Element
    refs: dict[str, ET.Element]
    original: bytes
    changed: bool = False

    @classmethod
    def parse(cls, contents: bytes, max_nodes: int = 100_000):
        try:
            security = expat.ParserCreate()
            count = 0
            depth = 0

            def reject_entity(*args):
                raise ReviewError("Entity declarations are not allowed in review MusicXML.")

            def count_node(*args):
                nonlocal count, depth
                count += 1
                depth += 1
                if count > max_nodes or depth > 64:
                    raise ReviewError("MusicXML has too many elements for a review session.", 413)

            def end_node(*args):
                nonlocal depth
                depth -= 1

            security.EntityDeclHandler = reject_entity
            security.StartElementHandler = count_node
            security.EndElementHandler = end_node
            security.Parse(contents, True)  # Never fetch an external DTD.
            root = ET.fromstring(contents, parser=ET.XMLParser(
                target=ET.TreeBuilder(insert_comments=True, insert_pis=True),
            ))
        except (expat.ExpatError, ET.ParseError, ValueError) as error:
            raise ReviewError("The review document is not valid XML.") from error
        if local(root.tag) != "score-partwise" or not any(local(p.tag) == "part" for p in root):
            raise ReviewError("Reviews require score-partwise MusicXML with parts.")
        refs, counts = {}, {}
        roles = {"part": "p", "measure": "m", "note": "e", "lyric": "l", "harmony": "h", "credit-words": "c"}
        for element in root.iter():
            prefix = roles.get(local(element.tag))
            if prefix:
                counts[prefix] = counts.get(prefix, 0) + 1
                refs[f"{prefix}-{counts[prefix]}"] = element
        return cls(root, refs, contents)

    @property
    def namespace(self) -> str:
        return self.root.tag[:self.root.tag.index("}") + 1] if self.root.tag.startswith("{") else ""

    def child(self, element, name):
        return element.find(self.namespace + name)

    def children(self, element, name):
        return element.findall(self.namespace + name)

    def text(self, element, name, default=None):
        value = element.findtext(self.namespace + name)
        return value.strip() if value is not None else default

    def get(self, identifier: str, tag: str) -> ET.Element:
        node = self.refs.get(identifier)
        if node is None or local(node.tag) != tag:
            raise ReviewError("The requested score object does not exist.", 404)
        return node

    def parent(self, node):
        return next((parent for parent in self.root.iter() if node in list(parent)), None)

    def clone(self):
        return deepcopy(self)  # deepcopy memo keeps refs attached to the cloned tree.

    def xml(self) -> bytes:
        if not self.changed:
            return self.original
        return ET.tostring(self.root, encoding="utf-8", xml_declaration=True)

    def weight(self) -> int:
        # Conservative accounting includes the original bytes and tree/sidecar overhead.
        return len(self.original) + len(self.xml()) + sum(512 for _ in self.root.iter())

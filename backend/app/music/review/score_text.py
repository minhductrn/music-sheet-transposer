"""Independent preserved score text. No lyric classification or ownership inference."""
from xml.etree import ElementTree as ET

from .document import ReviewError, local


def project_texts(doc):
    ids = {node: key for key, node in doc.refs.items()}
    parents = {child: parent for parent in doc.root.iter() for child in parent}
    result = []
    for key, node in doc.refs.items():
        tag, parent = local(node.tag), parents.get(node)
        if parent is None:
            continue
        role = None
        if tag == 'work-title' and local(parent.tag) == 'work':
            role = 'work_title'
        elif tag == 'movement-title' and parent is doc.root:
            role = 'movement_title'
        elif tag == 'creator' and local(parent.tag) == 'identification':
            role = node.get('type', 'credit')
        elif tag == 'credit-words' and local(parent.tag) == 'credit':
            kind = doc.text(parent, 'credit-type', 'credit')
            role = 'credit' if kind == 'credit' else 'printed_' + kind
        elif tag == 'words' and local(parent.tag) == 'direction-type' and parents.get(parent) is not None and local(parents[parent].tag) == 'direction':
            role = 'direction'
        if role is None:
            continue
        context, measure, part, direction = parent, None, None, None
        while context is not None:
            name = local(context.tag)
            if name == 'measure':
                measure = context
            if name == 'part':
                part = context
            if name == 'direction':
                direction = context
            context = parents.get(context)
        result.append({'id': key, 'role': role, 'text': node.text or '', 'editable': not len(node),
                       'measure_id': ids.get(measure), 'measure_number': measure.get('number') if measure is not None else None,
                       'part_id': ids.get(part), 'staff': doc.text(direction, 'staff', '1') if direction is not None else None})
    return result


def text_node(doc, identifier):
    if identifier not in {entry['id'] for entry in project_texts(doc)}:
        raise ReviewError('This score text is no longer available.', 404)
    return doc.refs[identifier]


def patch_text(doc, identifier, text):
    node = text_node(doc, identifier)
    if len(node):
        raise ReviewError('This text contains nested content; it cannot be flattened by a text edit.')
    if node.text == text:
        return False
    entries=project_texts(doc)
    selected=next(entry for entry in entries if entry['id']==identifier)
    # Synchronize only an exact, unique metadata/printed composer pair.
    # Unrelated equal strings and multiple credits remain independent.
    matches=[entry for entry in entries if entry['text']==node.text and entry['role'] in ('composer','printed_composer')]
    if selected['role'] in ('composer','printed_composer') and len(matches)==2 and {entry['role'] for entry in matches}=={'composer','printed_composer'}:
        for entry in matches:
            partner=doc.refs[entry['id']]
            if not len(partner):partner.text=text
    else:
        title_roles={'movement_title','work_title','printed_title','credit'}
        titles=[entry for entry in entries if entry['text']==node.text and entry['role'] in title_roles]
        roles={entry['role'] for entry in titles}
        if selected['role'] in title_roles and 2<=len(titles)<=3 and len(roles)==len(titles) and roles & {'movement_title','work_title'} and len([entry for entry in titles if entry['role'] in ('printed_title','credit')])==1:
            for entry in titles:
                partner=doc.refs[entry['id']]
                if not len(partner):partner.text=text
        else:
            node.text = text
    doc.changed = True


def delete_text(doc, identifier):
    node = text_node(doc, identifier)
    parent = doc.parent(node)
    if local(parent.tag) == 'direction-type':
        direction = doc.parent(parent)
        other_types = [t for t in doc.children(direction, 'direction-type') if t is not parent]
        if len(parent) == 1 and not other_types:
            # A sound/footnote/extension may carry meaning independent of the words.
            if any(local(c.tag) not in ('direction-type', 'offset', 'staff', 'voice') for c in direction):
                node.text=''
                del doc.refs[identifier]
                doc.changed=True
                return
            doc.parent(direction).remove(direction)
        else:
            parent.remove(node)
            if not len(parent):
                direction.remove(parent)
    elif local(parent.tag) == 'credit' and len(doc.children(parent, 'credit-words')) == 1 and not doc.children(parent, 'credit-image'):
        if any(local(c.tag) not in ('credit-type', 'credit-words') for c in parent):
            raise ReviewError('This credit includes additional content; edit it without deleting the shared credit.')
        doc.root.remove(parent)
    else:
        parent.remove(node)
    del doc.refs[identifier]
    doc.changed = True


def add_text(doc, identifier, request):
    # Import lazily: patcher imports importer, whose projection uses this module.
    from .patcher import put, ROOT_ORDER
    role = request.role
    if role == 'direction':
        if not request.event_id:
            raise ReviewError('Select a note or rest to anchor the text.')
        event = doc.get(request.event_id, 'note')
        if doc.child(event, 'chord') is not None:
            raise ReviewError('Select the leading note of this chord to anchor text at its onset.')
        measure = doc.parent(event)
        if local(measure.tag) != 'measure':
            raise ReviewError('The annotation needs a measure event.')
        direction = ET.Element(doc.namespace + 'direction', {'placement': 'above'})
        kind = ET.SubElement(direction, doc.namespace + 'direction-type')
        node = ET.SubElement(kind, doc.namespace + 'words')
        for field in ('voice', 'staff'):
            value = doc.text(event, field)
            if value:
                ET.SubElement(direction, doc.namespace + field).text = value
        measure.insert(list(measure).index(event), direction)
    elif role in ('work_title', 'movement_title'):
        parent = put(doc, doc.root, 'work', order=ROOT_ORDER) if role == 'work_title' else doc.root
        tag = 'work-title' if role == 'work_title' else 'movement-title'
        if doc.child(parent, tag) is not None:
            raise ReviewError('This title already exists. Edit it instead.')
        node = put(doc, parent, tag, order=['work-number', 'work-title', 'opus'] if role == 'work_title' else ROOT_ORDER)
    elif role in ('composer', 'lyricist'):
        parent = put(doc, doc.root, 'identification', order=ROOT_ORDER)
        node = ET.Element(doc.namespace + 'creator', {'type': role})
        parent.insert(next((i for i, c in enumerate(parent) if local(c.tag) != 'creator'), len(parent)), node)
    else:
        parent = ET.Element(doc.namespace + 'credit', {'page': '1'})
        node = ET.SubElement(parent, doc.namespace + 'credit-words')
        index = next((i for i, c in enumerate(doc.root) if local(c.tag) in ('part-list', 'part')), len(doc.root))
        doc.root.insert(index, parent)
    node.text = request.text
    doc.refs[identifier] = node
    doc.changed = True


def move_text_to_header(doc, identifier, text, role):
    from types import SimpleNamespace
    selected = next((entry for entry in project_texts(doc) if entry['id'] == identifier), None)
    if not selected or selected['role'] != 'direction':
        raise ReviewError('Select a measure text to move to the page header.')
    if role not in ('composer', 'lyricist'):
        raise ReviewError('Unsupported header role.')
    if any(entry['role'] == role for entry in project_texts(doc)):
        raise ReviewError('This header already exists. Edit it instead of creating a duplicate.')
    if not text.strip():
        raise ReviewError('Header text cannot be empty.')
    delete_text(doc, identifier)
    add_text(doc, identifier, SimpleNamespace(role=role, text=text, event_id=None))

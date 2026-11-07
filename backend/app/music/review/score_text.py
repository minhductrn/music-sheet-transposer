"""Independent preserved score text. No lyric classification or ownership inference."""
from xml.etree import ElementTree as ET
import json
import math

from .document import ReviewError, local


def page_size(doc):
    def value(tag, fallback):
        node = next(doc.root.iter(doc.namespace + tag), None)
        try:
            result = float(node.text) if node is not None else fallback
            return result if math.isfinite(result) and result > 0 else fallback
        except (TypeError, ValueError):
            return fallback
    return value('page-width',1190), value('page-height',1684)


def header_position(doc, node, role):
    try:
        if role == 'output_heading':
            field = next((n for n in doc.root.iter(doc.namespace+'miscellaneous-field') if n.get('name')=='mst-output-heading-position'),None)
            result = json.loads(field.text) if field is not None else None
        elif role == 'printed_mst-header' and node.get('default-x') is not None and node.get('default-y') is not None:
            width,height=page_size(doc)
            result={'x':float(node.get('default-x'))/width,'y':(height-float(node.get('default-y')))/(height*0.2)}
        else:
            return None
        if isinstance(result,dict) and all(isinstance(result.get(k),(int,float)) and math.isfinite(result[k]) and 0<=result[k]<=1 for k in ('x','y')):
            return result
    except (ValueError, TypeError, json.JSONDecodeError):
        pass
    return None


def move_header_text(doc, identifier, position):
    node=text_node(doc,identifier)
    entry=next(t for t in project_texts(doc) if t['id']==identifier)
    if entry['role']=='output_heading':
        parent=doc.parent(node)
        field=next((n for n in parent if n.get('name')=='mst-output-heading-position'),None)
        if field is None:
            field=ET.SubElement(parent,doc.namespace+'miscellaneous-field',{'name':'mst-output-heading-position'})
        field.text=json.dumps({'x':position.x,'y':position.y},separators=(',',':'))
    elif entry['role']=='printed_mst-header':
        width,height=page_size(doc)
        node.set('default-x',str(position.x*width))
        node.set('default-y',str(height-position.y*height*0.2))
    else:
        if entry['role'] not in ('direction', 'credit', 'composer', 'lyricist', 'printed_composer', 'printed_lyricist'):
            raise ReviewError('Select an independent text annotation to move to the header.')
        from types import SimpleNamespace
        text = node.text or ''
        delete_text(doc, identifier)
        add_text(doc, identifier, SimpleNamespace(role='header', text=text, event_id=None))
        move_header_text(doc, identifier, position)
    doc.changed=True


def project_texts(doc):
    # Expose the app-owned output label as a stable text object. XML remains metadata.
    heading = next((n for n in doc.root.iter(doc.namespace + 'miscellaneous-field') if n.get('name') == 'mst-output-heading'), None)
    if heading is not None:
        doc.refs['output-heading'] = heading
    else:
        doc.refs.pop('output-heading', None)
    ids = {node: key for key, node in doc.refs.items()}
    parents = {child: parent for parent in doc.root.iter() for child in parent}
    result = []
    for key, node in doc.refs.items():
        tag, parent = local(node.tag), parents.get(node)
        if parent is None:
            continue
        role = None
        if tag == 'miscellaneous-field' and node.get('name') == 'mst-output-heading':
            role = 'output_heading'
        elif tag == 'work-title' and local(parent.tag) == 'work':
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
                       'header_position': header_position(doc,node,role), 'part_id': ids.get(part), 'staff': doc.text(direction, 'staff', '1') if direction is not None else None})
    return result


def text_node(doc, identifier):
    if identifier not in {entry['id'] for entry in project_texts(doc)}:
        raise ReviewError('This score text is no longer available.', 404)
    return doc.refs[identifier]


def paired_header_ids(doc, identifier):
    text_node(doc, identifier)
    entries = project_texts(doc)
    selected = next(entry for entry in entries if entry['id'] == identifier)
    for role in ('composer', 'lyricist'):
        pair = [entry for entry in entries if entry['text'] == selected['text']
                and entry['role'] in (role, 'printed_' + role)]
        if selected['role'] in (role, 'printed_' + role) and len(pair) == 2 and {entry['role'] for entry in pair} == {role, 'printed_' + role}:
            return [entry['id'] for entry in pair]
    return [identifier]


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
    partners = paired_header_ids(doc, identifier)
    if len(partners) == 2:
        for partner_id in partners:
            partner = doc.refs[partner_id]
            if not len(partner):
                partner.text = text
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
    partners = paired_header_ids(doc, identifier)
    if len(partners) == 2:
        # Remove the printed representation first so metadata cannot recreate it.
        printed = next(key for key in partners if local(doc.parent(doc.refs[key]).tag) == 'credit')
        metadata = next(key for key in partners if key != printed)
        _delete_text(doc, printed)
        _delete_text(doc, metadata)
        return
    _delete_text(doc, identifier)


def _delete_text(doc, identifier):
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
        if role == 'header':
            ET.SubElement(parent, doc.namespace + 'credit-type').text = 'mst-header'
        node = ET.SubElement(parent, doc.namespace + 'credit-words')
        index = next((i for i, c in enumerate(doc.root) if local(c.tag) in ('part-list', 'part')), len(doc.root))
        doc.root.insert(index, parent)
    node.text = request.text
    doc.refs[identifier] = node
    if getattr(request, 'header_position', None) is not None:
        move_header_text(doc,identifier,request.header_position)
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

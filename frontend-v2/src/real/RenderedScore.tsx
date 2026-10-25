import { useEffect, useRef, useState } from 'react';
import { OpenSheetMusicDisplay, Pitch, type VexFlowGraphicalNote } from 'opensheetmusicdisplay';
import { events, rational, type Review, type Event } from './api';
export type Curve = {
    kind: 'tie' | 'slur';
    from: string;
    to: string;
    direction: 'up' | 'down';
};
type Props = {
    review: Review;
    readOnly?: boolean;
    fitVersion?:number;
    zoom: number;
    selected?: string | null;
    onHead?: (id: string, dy: number) => void;
    onLyric?: (event: string, verse: string, box: DOMRect) => void;
    onText?: (id: string, box: DOMRect) => void;
    onGap?: (measure: string, onset: string, voice: string, staff: number) => void;
    onAmbiguous?: (ids: string[], dy: number, box: DOMRect) => void;
    onCurve?: (curve: Curve, dy: number) => void;
    onAnchor?: (measure: string, onset: string, staff: number, pitch: {
        step: string;
        alter: string;
        octave: number;
    }, box: DOMRect) => void;
    onReady?: (count: number) => void;
};
// A head is interactive only when renderer semantics resolve exactly one XML event.
export function RenderedScore({ review, readOnly, fitVersion=0, zoom, selected, onHead, onLyric, onText, onGap, onReady, onAmbiguous, onCurve, onAnchor }: Props) {
    const host = useRef<HTMLDivElement>(null), live = useRef({ selected, onHead, onLyric, onText, onGap, onReady, onAmbiguous, onCurve, onAnchor });
    live.current = { selected, onHead, onLyric, onText, onGap, onReady, onAmbiguous, onCurve, onAnchor };
    const fitted=useRef(0);
    const [error, setError] = useState(''), [width, setWidth] = useState(0);
    useEffect(() => { const el = host.current?.parentElement; if (!el)
        return; const observer = new ResizeObserver(() => setWidth(el.clientWidth)); observer.observe(el); return () => observer.disconnect(); }, []);
    useEffect(() => {
        let disposed = false;
        const element = host.current;
        if (!element)
            return;
        const parent=element.parentElement;if(parent){const css=getComputedStyle(parent);element.style.width=Math.max(1,parent.clientWidth-parseFloat(css.paddingLeft)-parseFloat(css.paddingRight))+'px';}
        const osmd = new OpenSheetMusicDisplay(element, { backend: 'svg', autoResize: false, drawTitle: true, drawComposer: true, drawPartNames: false, drawingParameters: 'default' });

        (async () => {
            try {
                await osmd.load(review.xml);
                if (disposed)
                    return;
                // load() clears the OSMD zoom; apply the requested scale afterwards,
                // before both native notation and canonical curve geometry are rendered.
                osmd.Zoom = zoom;
                osmd.render();
                // Separate lyric rows by voice in the derived view; never merge or rewrite XML syllables.
            const lyricVoices = [...new Set(events(review).filter(e => e.lyric_ids.length).map(e => e.voice))].sort();
            const verseRows = Math.max(1, new Set(review.score.lyrics.map(l => l.number)).size);
            for (const row of osmd.GraphicSheet.MeasureList) for (const measure of row) if (measure) for (const entry of measure.staffEntries) for (const lyric of entry.LyricsEntries) {
                const node = lyric.GraphicalLabel.SVGNode as SVGGraphicsElement | null;
                const voice = String(lyric.LyricsEntry.Parent.ParentVoice.VoiceId);
                const index = lyricVoices.indexOf(voice);
                if (node && index > 0) {
                    const matrix = node.getScreenCTM();
                    const scale = matrix ? Math.hypot(matrix.c, matrix.d) : 1;
                    const offset = index * verseRows * (node.getBoundingClientRect().height + 5) / scale;
                    node.setAttribute('transform', (node.getAttribute('transform') ?? '') + ` translate(0,${offset})`);
                }
            }
            let count = 0;
                const all = events(review);
                const nativeCurves = new Map<string, SVGGraphicsElement[]>();
                const bindings = new Map<Element, {
                    event: Event;
                    spacing: number;
                    line: object; left:number;right:number;
                }>();
                for (const row of osmd.GraphicSheet.MeasureList)
                    for (const measure of row) {
                        if (!measure)
                            continue;
                        for (const entry of measure.staffEntries)
                            for (const voice of entry.graphicalVoiceEntries)
                                for (const graphical of voice.notes) {
                                    const note = graphical.sourceNote, staff = note?.ParentStaff;
                                    if (!staff?.ParentInstrument || !note.ParentVoiceEntry || measure.parentSourceMeasure !== note.SourceMeasure)
                                        continue;
                                    const part = osmd.Sheet.Instruments.indexOf(staff.ParentInstrument), mi = osmd.Sheet.SourceMeasures.indexOf(note.SourceMeasure), staffNumber = staff.ParentInstrument.Staves.indexOf(staff) + 1, pitch = note.Pitch;
                                    const canonical = review.score.parts[part]?.measures.find(m => m.index === mi);
                                    const matches = all.filter(e => canonical?.voices.some(v => v.events.includes(e)) && e.staff === staffNumber && e.voice === String(note.ParentVoiceEntry.ParentVoice.VoiceId) && Math.abs(rational(e.onset) - note.ParentVoiceEntry.Timestamp.RealValue * 4) < 1e-7 && Math.abs(rational(e.duration) - note.Length.RealValue * 4) < 1e-7 && e.grace === !!note.IsGraceNote && e.kind === (note.isRest() ? 'rest' : 'note') && (note.isRest() || e.pitch?.step === Pitch.getNoteEnumString(pitch.FundamentalNote) && e.pitch.octave === pitch.Octave + Pitch.OctaveXmlDifference && Number(e.pitch.alter) === pitch.AccidentalHalfTones));
                                    const vf = graphical as VexFlowGraphicalNote;
                                    const heads = vf.getNoteheadSVGs?.() ?? [], head = heads[vf.vfnote?.[1] ?? vf.vfnoteIndex] ?? (note.isRest() ? vf.getSVGGElement?.() : null);
                                    if (!head || matches.length !== 1)
                                        continue;
                                    const lines = measure.ParentStaffLine?.StaffLines;
                                    if(!lines||lines.length!==5)continue;
                                    const spacing = lines?.length === 5 ? (lines[4].Start.y - lines[0].Start.y) * 10 * zoom / 4 : 10 * zoom;
                                    for (const kind of ['tie', 'slur'])
                                        nativeCurves.set(matches[0].id + kind, (kind === 'tie' ? vf.getTieSVGs?.() : vf.getSlurSVGs?.()) as unknown as SVGGraphicsElement[] ?? []);
                                    head.setAttribute('data-score-event', matches[0].id);
                                    const prior = bindings.get(head);
                                    if (prior && prior.event.id !== matches[0].id) {
                                        bindings.delete(head);
                                        head.setAttribute('data-ambiguous', 'true');
                                    }
                                    else if (!head.hasAttribute('data-ambiguous'))
                                        bindings.set(head, { event: matches[0], spacing, line:measure.ParentStaffLine,left:(measure.ParentStaffLine.PositionAndShape.AbsolutePosition.x+lines[0].Start.x)*10,right:(measure.ParentStaffLine.PositionAndShape.AbsolutePosition.x+lines[0].End.x)*10 });
                                }
                    }
                    const relations: Curve[] = [...all.filter(e => e.tie_target_id).map(e => ({ kind: 'tie' as const, from: e.id, to: e.tie_target_id!, direction: e.tie_direction ?? (()=>{const cluster=all.filter(n=>n.tie_target_id&&n.measure_id===e.measure_id&&n.staff===e.staff&&n.onset===e.onset&&n.pitch);const pitch=(n:Event)=>n.pitch!.octave*12+'C D EF G A B'.indexOf(n.pitch!.step)+Number(n.pitch!.alter);const pitches=cluster.map(pitch);return pitches.length>1&&Math.min(...pitches)!==Math.max(...pitches)?pitch(e)==Math.min(...pitches)?'down':'up':e.voice==='2'?'down':'up';})() })), ...(review.slurs ?? []).map(c => ({ kind: 'slur' as const, from: c.source_event_id, to: c.target_event_id, direction: c.direction }))];
                    const byId = new Map([...bindings].map(([node, value]) => [value.event.id, { node: node as SVGGraphicsElement, ...value }]));
                    const svgNS = 'http://www.w3.org/2000/svg';
                    // Native system-break fragments may have no owner ID or a stale layout.
                    // Replace all native ties only when every XML tie is fully mapped here.
                    const xml=new DOMParser().parseFromString(review.xml,'application/xml');
                    let starts=0,stops=0,unambiguous=!xml.querySelector('parsererror');
                    for(const note of xml.getElementsByTagNameNS('*','note')){
                        const sounding=[...note.children].filter(n=>n.localName==='tie');
                        const written=[...note.children].filter(n=>n.localName==='notations').flatMap(n=>[...n.children].filter(c=>c.localName==='tied'));
                        const flags=(nodes:Element[])=>({start:nodes.filter(n=>['start','continue'].includes(n.getAttribute('type')??'')).length,stop:nodes.filter(n=>['stop','continue'].includes(n.getAttribute('type')??'')).length});
                        // Repeated written tags do not add sounding relationships; keep raw XML intact.
                        const a=flags(sounding),b=flags(written),types=sounding.length?a:b;
                        if([...sounding,...written].some(n=>!['start','stop','continue'].includes(n.getAttribute('type')??''))||a.start>1||a.stop>1||(!sounding.length&&(b.start>1||b.stop>1))||(sounding.length&&written.length&&(Boolean(a.start)!==Boolean(b.start)||Boolean(a.stop)!==Boolean(b.stop))))unambiguous=false;
                        starts+=types.start;stops+=types.stop;
                    }
                    const ties=relations.filter(c=>c.kind==='tie'),svgs=element.querySelectorAll('svg');
                    const complete=unambiguous&&svgs.length===1&&starts===stops&&starts===ties.length&&ties.every(c=>{const a=byId.get(c.from),b=byId.get(c.to);return a&&b&&a.node.ownerSVGElement===svgs[0]&&b.node.ownerSVGElement===svgs[0];});
                    if(complete)for(const native of element.querySelectorAll<SVGElement>('g.vf-stavetie')){native.style.opacity='0';native.dataset.canonicalReplacement='complete-xml-ties';}
                    for(const c of relations){const a=byId.get(c.from),b=byId.get(c.to);if(a&&b&&a.node.ownerSVGElement===b.node.ownerSVGElement)for(const id of [c.from,c.to])for(const native of nativeCurves.get(id+c.kind)??[])native.style.opacity='0';}
                    for (const c of relations) {
                        const a = byId.get(c.from), b = byId.get(c.to);
                        if (!a || !b)
                            continue;
                        const svg = a.node.ownerSVGElement;
                        if (!svg || svg !== b.node.ownerSVGElement)
                            continue;
                        const matrix = svg.getScreenCTM();
                        if (!matrix)
                            continue;
                        const inverse = matrix.inverse(), ap = a.node.getBoundingClientRect(), bp = b.node.getBoundingClientRect();
                        const from = new DOMPoint(ap.left + ap.width / 2, c.direction === 'up' ? ap.top : ap.bottom).matrixTransform(inverse), to = new DOMPoint(bp.left + bp.width / 2, c.direction === 'up' ? bp.top : bp.bottom).matrixTransform(inverse), sign = c.direction === 'up' ? -1 : 1;const gap=c.kind==='tie'?1.5:5;const bend=c.kind==='tie'?Math.min(18,Math.max(8,Math.abs(from.x-to.x)*.15)):32;
                        const cross = a.line!==b.line;
                        // Native SVG viewBox already applies Zoom; staff edges are unscaled SVG units.
                        const edge = a.right;const incoming=Math.max(b.left+3,to.x-12);const outgoingBend=c.kind==='tie'?Math.min(bend,Math.max(6,(edge-3-from.x)*.15)):bend;const incomingBend=c.kind==='tie'?Math.min(bend,Math.max(6,(to.x-incoming)*.15)):bend;
                        const d = cross ? `M${from.x} ${from.y + sign * gap}Q${(from.x + edge - 3) / 2} ${from.y + sign * outgoingBend} ${edge - 3} ${from.y + sign * gap} M${incoming} ${to.y + sign * gap}Q${(incoming + to.x) / 2} ${to.y + sign * incomingBend} ${to.x} ${to.y + sign * gap}` : `M${from.x} ${from.y + sign * gap}Q${(from.x + to.x) / 2} ${(from.y + to.y) / 2 + sign * bend} ${to.x} ${to.y + sign * gap}`;
                        const g = document.createElementNS(svgNS, 'g');
                        g.setAttribute('data-testid', `real-curve-${c.kind}-${c.from}-${c.to}`);
                        g.setAttribute('data-direction', c.direction);
                        if(!readOnly)g.setAttribute('role', 'button');
                        g.setAttribute('aria-label', `${c.kind} from ${c.from} to ${c.to}`);
                        if(!readOnly)g.setAttribute('tabindex', '0');
                        g.style.cursor = readOnly?'default':'ns-resize';
                        for (const [color, width] of [['transparent', '14'], ['#263b50', '2']]) {
                            const path = document.createElementNS(svgNS, 'path');
                            path.setAttribute('d', d);
                            path.setAttribute('fill', 'none');
                            path.setAttribute('stroke', color);
                            path.setAttribute('stroke-width', width);
                            path.style.pointerEvents = readOnly?'none':'stroke';
                            g.append(path);
                        }
                        let sy: number | null = null;
                        if(!readOnly)g.onpointerdown = e => { e.stopPropagation(); sy = e.clientY; g.setPointerCapture(e.pointerId); };
                        if(!readOnly)g.onpointerup = e => { e.stopPropagation(); if (sy !== null) {
                            live.current.onCurve?.(c, (e.clientY - sy) / zoom);
                            sy = null;
                        } };
                        if(!readOnly)g.onkeydown = e => { if (e.key === 'Enter')
                            live.current.onCurve?.(c, 0); };
                        svg.append(g);
                    }
                if (!readOnly) {
                    for (const [node, { event }] of bindings) {
                        const head = node as SVGGraphicsElement;
                        count++;
                        head.dataset.eventId = event.id;
                        head.dataset.pitch = event.pitch ? `${event.pitch.step}${event.pitch.alter}/${event.pitch.octave}` : 'rest';
                        head.dataset.duration = event.duration ?? '';
                        head.dataset.voice = event.voice;
                        head.setAttribute('data-testid', 'real-head-' + event.id);
                        head.setAttribute('role', 'button');
                        head.setAttribute('aria-label', `${event.kind === 'rest' ? 'Rest' : 'Note'} ${event.id}, voice ${event.voice}`);
                        head.setAttribute('tabindex', '0');
                        head.style.cursor = 'pointer';
                        head.classList.toggle('real-selected', live.current.selected === event.id);
                        head.onkeydown = e => { if (e.key === 'Enter' || e.key === ' ') {
                            e.preventDefault();
                            live.current.onHead?.(event.id, 0);
                        } };
                    }
                    // Resolve physical shared heads with an explicit voice chooser instead of assuming DOM paint order.
                    for (const svg of element.querySelectorAll('svg')) {
                        let down: {
                            x: number;
                            y: number;
                            hits: {
                                event: Event;
                                spacing: number;
                    line: object; left:number;right:number;
                                box: DOMRect;
                            }[];
                        } | null = null;
                        svg.addEventListener('pointerdown', e => { const hits = [...bindings].filter(([n]) => n.closest('svg') === svg).map(([node, value]) => ({ ...value, box: node.getBoundingClientRect() })).filter(v => e.clientX >= v.box.left - 3 && e.clientX <= v.box.right + 3 && e.clientY >= v.box.top - 3 && e.clientY <= v.box.bottom + 3); svg.dataset.noteGesture = hits.length ? 'true' : 'false'; if (!hits.length)
                            return; e.stopPropagation(); e.preventDefault(); down = { x: e.clientX, y: e.clientY, hits }; svg.setPointerCapture(e.pointerId); }, true);
                        svg.addEventListener('pointerup', e => { if (!down)
                            return; e.stopPropagation(); const dy = (e.clientY - down.y) / (down.hits[0].spacing / 2); if (down.hits.length === 1)
                            live.current.onHead?.(down.hits[0].event.id, dy);
                        else
                            live.current.onAmbiguous?.(down.hits.map(h => h.event.id), dy, down.hits[0].box); down = null; }, true);
                    }
                    for (const row of osmd.GraphicSheet.MeasureList)
                        for (const measure of row)
                            if (measure)
                                for (const entry of measure.staffEntries)
                                    for (const lyric of entry.LyricsEntries) {
                                        const source = lyric.LyricsEntry, voice = source.Parent;
                                        const ownerCandidates = all.filter(e => bindings.size > 0 && e.voice === String(voice.ParentVoice.VoiceId) && review.score.parts.some(p => p.measures.some(m => m.index === osmd.Sheet.SourceMeasures.indexOf(measure.parentSourceMeasure) && m.voices.some(v => v.events.includes(e)))) && Math.abs(rational(e.onset) - voice.Timestamp.RealValue * 4) < 1e-7 && review.score.lyrics.some(l => l.event_id === e.id && l.number === source.VerseNumber && l.text === source.Text));
                                        const node = lyric.GraphicalLabel.SVGNode as SVGGraphicsElement | null;
                                        if (node && ownerCandidates.length === 1) {
                                            node.style.cursor = 'text';
                                            node.setAttribute('data-testid', 'real-lyric-' + ownerCandidates[0].id + '-' + source.VerseNumber);
                                            node.onclick = e => { e.stopPropagation(); live.current.onLyric?.(ownerCandidates[0].id, source.VerseNumber, node.getBoundingClientRect()); };
                                        }
                                    }
                    // Staff anchors use actual rendered timestamps and staff lines; XML onset remains explicit.
                    for (const row of osmd.GraphicSheet.MeasureList)
                        for (const measure of row) {
                            if (!measure?.ParentStaffLine)
                                continue;
                            const staff = measure.ParentStaff, partIndex = osmd.Sheet.Instruments.indexOf(staff.ParentInstrument), mi = osmd.Sheet.SourceMeasures.indexOf(measure.parentSourceMeasure), canonical = review.score.parts[partIndex]?.measures.find(m => m.index === mi);
                            if (!canonical)
                                continue;
                            const sample = [...bindings].find(([, v]) => canonical.voices.some(voice => voice.events.includes(v.event)));
                            if (!sample && element.querySelectorAll('svg').length !== 1) continue;
                            const svg = sample ? (sample[0] as SVGGraphicsElement).ownerSVGElement : element.querySelector('svg'), matrix = svg?.getScreenCTM();
                            if (!svg || !matrix)
                                continue;
                            const inverse = matrix.inverse(), lines = measure.ParentStaffLine.StaffLines;
                            if (lines.length !== 5)
                                continue;
                            const staffNumber = staff.ParentInstrument.Staves.indexOf(staff) + 1, position = measure.PositionAndShape.AbsolutePosition, left = (position.x + measure.PositionAndShape.BorderLeft) * 10, right = (position.x + measure.PositionAndShape.BorderRight) * 10, top = (measure.ParentStaffLine.PositionAndShape.AbsolutePosition.y + lines[0].Start.y) * 10, spacing = (lines[4].Start.y - lines[0].Start.y) * 10 / 4;
                            const points = [...bindings].filter(([, v]) => v.event.staff === staffNumber && canonical.voices.some(voice => voice.events.includes(v.event))).map(([node, v]) => { const b = node.getBoundingClientRect(); return { beat: rational(v.event.onset), x: new DOMPoint(b.left + b.width / 2, b.top).matrixTransform(inverse).x }; }).sort((a, b) => a.beat - b.beat);
                            if (!points.length) points.push({beat:0,x:left+Math.min(35,(right-left)/3)});
                            if (!(right > left))
                                continue;
                            const modelEvents = canonical.voices.flatMap(v => v.events);
                            const end = rational(canonical.expected_duration) || Math.max(...modelEvents.map(e => rational(e.onset) + rational(e.duration)));
                            const anchors = [...points, { beat: end, x: right - 6 }];
                            const positionAt = (beat: number) => { const before = [...anchors].reverse().find(p => p.beat <= beat) ?? anchors[0], after = anchors.find(p => p.beat >= beat) ?? anchors[anchors.length - 1]; return after.beat === before.beat ? before.x : before.x + (after.x - before.x) * (beat - before.beat) / (after.beat - before.beat); };
                            const positionTokens = new Map(modelEvents.filter(e => e.onset !== null).map(e => [rational(e.onset), e.onset!]));
                            for (const gap of canonical.insertion_gaps ?? [])
                                positionTokens.set(rational(gap.onset), gap.onset);
                            const candidates = new Set(points.map(p => p.beat));
                            for (let beat = 0; beat < end; beat += .25)
                                candidates.add(beat);
                            for (const gap of canonical.insertion_gaps ?? [])
                                if (gap.staff === staffNumber)
                                    candidates.add(rational(gap.onset));
                            for (const gap of canonical.insertion_gaps ?? []) {
                                if (gap.staff !== staffNumber)
                                    continue;
                                const x = positionAt(rational(gap.onset)), y = top + spacing * 2;
                                const g = document.createElementNS(svgNS, 'g');
                                g.setAttribute('data-gap-anchor', 'true');
                                g.setAttribute('data-testid', `real-gap-${canonical.id}-${gap.voice}-${gap.onset}`);
                                g.setAttribute('role', 'button');
                                g.setAttribute('aria-label', `Gap in measure ${canonical.number}, voice ${gap.voice}`);
                                g.setAttribute('tabindex', '0');
                                const rect = document.createElementNS(svgNS, 'rect');
                                rect.setAttribute('x', String(x - 9));
                                rect.setAttribute('y', String(y - 10));
                                rect.setAttribute('width', '18');
                                rect.setAttribute('height', '20');
                                rect.setAttribute('fill', '#f3f8fc');
                                rect.setAttribute('stroke', '#6489a7');
                                rect.setAttribute('stroke-dasharray', '3 2');
                                g.append(rect);
                                g.style.cursor = 'pointer';
                                g.onclick = e => { e.stopPropagation(); live.current.onGap?.(canonical.id, gap.onset, gap.voice, gap.staff); };
                                g.onkeydown = e => { if (e.key === 'Enter')
                                    live.current.onGap?.(canonical.id, gap.onset, gap.voice, gap.staff); };
                                svg.append(g);
                            }
                            svg.addEventListener('click', e => {
                                if (svg.dataset.noteGesture === 'true') {
                                    svg.dataset.noteGesture = 'false';
                                    return;
                                }
                                if ((e.target as Element).closest('[data-event-id],[data-testid^="real-curve"],[data-gap-anchor],text'))
                                    return;
                                const pt = new DOMPoint(e.clientX, e.clientY).matrixTransform(inverse);
                                if (pt.x < left || pt.x > right || pt.y < top - spacing * 3 || pt.y > top + spacing * 7)
                                    return;
                                const clef = modelEvents.find(e => e.staff === staffNumber)?.clef;
                                const bottoms: Record<string, number> = { 'G2': 30, 'F4': 18, 'C3': 24, 'C4': 22 };
                                const sign = clef?.fields?.find(f => f.name === 'sign')?.text ?? clef?.sign, line = clef?.fields?.find(f => f.name === 'line')?.text ?? clef?.line, octave = Number(clef?.fields?.find(f => f.name === 'clef-octave-change')?.text ?? clef?.octave_change ?? 0);
                                const bottom = bottoms[(sign ?? 'G') + (line ?? '2')] + 7 * octave;
                                if (bottom === undefined)
                                    return;
                                const nearest = [...candidates].map(beat => ({ beat, x: positionAt(beat) })).reduce((best, p) => Math.abs(p.x - pt.x) < Math.abs(best.x - pt.x) ? p : best);
                                const diatonic = bottom - Math.round((pt.y - (top + spacing * 4)) / (spacing / 2)), step = 'CDEFGAB'[((diatonic % 7) + 7) % 7], fifths = Number(canonical.key_signature[0]?.fifths ?? 0), alter = (fifths >= 0 ? 'FCGDAEB' : 'BEADGCF').slice(0, Math.abs(fifths)).includes(step) ? String(fifths >= 0 ? 1 : -1) : '0';
                                live.current.onAnchor?.(canonical.id, positionTokens.get(nearest.beat) ?? String(nearest.beat), staffNumber, { step, alter, octave: Math.floor(diatonic / 7) }, new DOMRect(e.clientX, e.clientY, 0, 0));
                            });
                        }
                    for (const text of review.score.texts ?? []) {
                        const nodes = [...element.querySelectorAll('svg text')].filter(n => n.textContent === text.text);
                        if (nodes.length === 1) {
                            const node = nodes[0] as SVGGraphicsElement;
                            node.style.cursor = 'text';
                            node.setAttribute('data-testid', 'real-text-' + text.id);
                            node.onclick = e => { e.stopPropagation(); live.current.onText?.(text.id, node.getBoundingClientRect()); };
                        }
                    }
                }
                if(fitVersion!==fitted.current){fitted.current=fitVersion;const viewport=element.parentElement;if(viewport){viewport.scrollLeft=0;viewport.scrollTop=0;}}
                const systems=new Map<object,{top:number,bottom:number}>();
                for(const row of osmd.GraphicSheet.MeasureList)for(const measure of row)if(measure?.ParentStaffLine){const system=measure.ParentStaffLine.ParentMusicSystem;const box=system.PositionAndShape;systems.set(system,{top:(box.AbsolutePosition.y+box.BorderTop)*10*zoom,bottom:(box.AbsolutePosition.y+box.BorderBottom)*10*zoom});}
                const ordered=[...systems.values()].sort((a,b)=>a.top-b.top);
                if(element.querySelectorAll('svg').length===1)element.querySelector('svg')!.setAttribute('data-pdf-breaks',JSON.stringify(ordered.slice(1).map((s,i)=>(ordered[i].bottom+s.top)/2)));
                live.current.onReady?.(count);
                setError('');
            }
            catch (e) {
                if (!disposed)
                    setError(e instanceof Error ? e.message : 'Cannot render this MusicXML.');
            }
        })();
        return () => { disposed = true; element.replaceChildren(); };
    }, [review, readOnly, zoom, width,fitVersion]);
    useEffect(() => { host.current?.querySelectorAll('[data-event-id]').forEach(n => { const active = n.getAttribute('data-event-id') === selected; n.classList.toggle('real-selected', active); n.setAttribute('aria-pressed', String(active)); }); }, [selected, review, zoom]);
    return <><div ref={host} className="real-score"/>{error && <p role="alert">{error}</p>}</>;
}

import { renderPedalIdentities } from './pedalRendering';
import { renderXML } from './renderXML';
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
    printCompact?: boolean;
    review: Review;
    readOnly?: boolean;
    fitVersion?:number;
    zoom: number;
    selected?: string | null;
    selection?: string[];
    boxSelect?: boolean;
    onSelection?: (ids:string[])=>void;
    selectedText?: string|null;
    selectedMark?: string|null;
    onStaffContext?:(measure:string,box:DOMRect)=>void;
    onHarmony?:(id:string,box:DOMRect)=>void;
    onHarmonyCandidates?:(ids:string[],box:DOMRect)=>void;
    onMark?:(id:string)=>void;
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
export function RenderedScore({ printCompact=false, review, readOnly, fitVersion=0, zoom, selected, selection=[], boxSelect=false, onSelection, onHarmony, onHarmonyCandidates, onStaffContext, selectedText, selectedMark, onMark, onHead, onLyric, onText, onGap, onReady, onAmbiguous, onCurve, onAnchor }: Props) {
    const host = useRef<HTMLDivElement>(null), live = useRef({ boxSelect, onSelection, onHarmony, onHarmonyCandidates, onStaffContext, selected, onMark, onHead, onLyric, onText, onGap, onReady, onAmbiguous, onCurve, onAnchor });
    live.current = { boxSelect, onSelection, onHarmony, onHarmonyCandidates, onStaffContext, selected, onMark, onHead, onLyric, onText, onGap, onReady, onAmbiguous, onCurve, onAnchor };
    const fitted=useRef(0);
    const scrollPosition=useRef({top:0,left:0});
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

        if(printCompact){const rules=osmd.EngravingRules;rules.MinimumDistanceBetweenSystems=4;rules.VerticalBetweenLyricsDistance=0.25;rules.HorizontalBetweenLyricsDistance=0.15;rules.MinNoteDistance=1.5;}

        (async () => {
            try {
                await osmd.load(renderXML(review.xml));
                if (disposed)
                    return;
                // load() clears the OSMD zoom; apply the requested scale afterwards,
                // before both native notation and canonical curve geometry are rendered.
                osmd.Zoom = zoom;
                if(readOnly)osmd.render();else renderPedalIdentities(osmd);
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
                                    const matches = all.filter(e => canonical?.voices.some(v => v.events.includes(e)) && e.staff === staffNumber && e.voice === String(note.ParentVoiceEntry.ParentVoice.VoiceId) && Math.abs(rational(e.onset) - note.ParentVoiceEntry.Timestamp.RealValue * 4) < 1e-7 && (e.grace || Math.abs(rational(e.duration) - note.Length.RealValue * 4) < 1e-7) && e.grace === !!note.IsGraceNote && e.kind === (note.isRest() ? 'rest' : 'note') && (note.isRest() || e.pitch?.step === Pitch.getNoteEnumString(pitch.FundamentalNote) && e.pitch.octave === pitch.Octave + Pitch.OctaveXmlDifference && Number(e.pitch.alter) === pitch.AccidentalHalfTones));
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
                        if(!readOnly)g.onpointerdown = e => { if(e.button!==0)return;e.stopPropagation(); sy = e.clientY; g.setPointerCapture(e.pointerId); };
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
                        let boxStart:{x:number;y:number}|null=null;
                        let boxRect:SVGRectElement|null=null;
                        const clearBox=()=>{boxRect?.remove();boxRect=null;boxStart=null;};
                        svg.addEventListener('pointerdown',e=>{
                            if(e.button!==0||(!live.current.boxSelect&&!e.shiftKey))return;
                            e.preventDefault();e.stopImmediatePropagation();svg.dataset.noteGesture='true';
                            boxStart={x:e.clientX,y:e.clientY};svg.setPointerCapture(e.pointerId);
                            boxRect=document.createElementNS('http://www.w3.org/2000/svg','rect');
                            boxRect.setAttribute('fill','#1769b522');boxRect.setAttribute('stroke','#1769b5');boxRect.style.pointerEvents='none';svg.append(boxRect);
                        },true);
                        svg.addEventListener('pointermove',e=>{
                            if(!boxStart||!boxRect)return;
                            e.stopImmediatePropagation();const inverse=svg.getScreenCTM()?.inverse();if(!inverse)return;
                            const a=new DOMPoint(boxStart.x,boxStart.y).matrixTransform(inverse),b=new DOMPoint(e.clientX,e.clientY).matrixTransform(inverse);
                            boxRect.setAttribute('x',String(Math.min(a.x,b.x)));boxRect.setAttribute('y',String(Math.min(a.y,b.y)));boxRect.setAttribute('width',String(Math.abs(a.x-b.x)));boxRect.setAttribute('height',String(Math.abs(a.y-b.y)));
                        },true);
                        svg.addEventListener('pointerup',e=>{
                            if(!boxStart)return;e.preventDefault();e.stopImmediatePropagation();
                            const left=Math.min(boxStart.x,e.clientX),right=Math.max(boxStart.x,e.clientX),top=Math.min(boxStart.y,e.clientY),bottom=Math.max(boxStart.y,e.clientY);
                            const ids=[...bindings].filter(([node])=>node.closest('svg')===svg).filter(([node])=>{const b=node.getBoundingClientRect();return b.right>=left&&b.left<=right&&b.bottom>=top&&b.top<=bottom;}).map(([,v])=>v.event.id);
                            clearBox();live.current.onSelection?.([...new Set(ids)]);
                        },true);
                        svg.addEventListener('pointercancel',clearBox);
                        svg.addEventListener('pointerdown', e => { if(e.button!==0)return; if((e.target as Element).closest('[data-testid^="real-curve-"], [data-text-id], [data-mark-id], [data-harmony-id]')){svg.dataset.noteGesture='true';return;} const hits = [...bindings].filter(([n]) => n.closest('svg') === svg).map(([node, value]) => ({ ...value, box: node.getBoundingClientRect() })).filter(v => e.clientX >= v.box.left - 3 && e.clientX <= v.box.right + 3 && e.clientY >= v.box.top - 3 && e.clientY <= v.box.bottom + 3); svg.dataset.noteGesture = hits.length ? 'true' : 'false'; if (!hits.length)
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
                                        const staff=measure.ParentStaff;
                                        const partIndex=osmd.Sheet.Instruments.indexOf(staff.ParentInstrument);
                                        const staffNumber=staff.ParentInstrument.Staves.indexOf(staff)+1;
                                        const canonical=review.score.parts[partIndex]?.measures.find(m=>m.index===osmd.Sheet.SourceMeasures.indexOf(measure.parentSourceMeasure));
                                        const ownerCandidates = all.filter(e => e.staff===staffNumber && canonical?.voices.some(v=>v.events.includes(e)) && bindings.size > 0 && e.voice === String(voice.ParentVoice.VoiceId) && review.score.parts.some(p => p.measures.some(m => m.index === osmd.Sheet.SourceMeasures.indexOf(measure.parentSourceMeasure) && m.voices.some(v => v.events.includes(e)))) && Math.abs(rational(e.onset) - voice.Timestamp.RealValue * 4) < 1e-7 && review.score.lyrics.some(l => l.event_id === e.id && l.number === source.VerseNumber && l.text === source.Text));
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
                            svg.addEventListener('contextmenu',e=>{const point=new DOMPoint(e.clientX,e.clientY).matrixTransform(inverse);if(point.x>=left&&point.x<=right&&point.y>=top-spacing*2&&point.y<=top+spacing*6){e.preventDefault();e.stopPropagation();live.current.onStaffContext?.(canonical.id,new DOMRect(e.clientX,e.clientY,0,0));}});
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
                    const visitedPedals=new Set<object>();
                    for(const row of osmd.GraphicSheet.MeasureList)for(const measure of row){
                        if(!measure?.ParentStaffLine)continue;
                        for(const graphic of measure.ParentStaffLine.Pedals??[]){
                            if(visitedPedals.has(graphic))continue;visitedPedals.add(graphic);
                            const pedal=graphic.getPedal,start=pedal.ParentStartMultiExpression;if(!start)continue;
                            const staff=measure.ParentStaff,part=osmd.Sheet.Instruments.indexOf(staff.ParentInstrument),mi=osmd.Sheet.SourceMeasures.indexOf(start.SourceMeasureParent),canonical=review.score.parts[part]?.measures.find(m=>m.index===mi);
                            const candidates=review.score.omr_marks?.filter(m=>m.kind==='pedal'&&m.type==='start'&&m.measure_id===canonical?.id&&m.staff===staff.ParentInstrument.Staves.indexOf(staff)+1&&Math.abs(rational(m.onset)-start.Timestamp.RealValue*4)<1e-7)??[];
                            if(candidates.length!==1)continue;
                            const binding=[...byId.values()].find(v=>v.event.measure_id===canonical?.id&&v.event.staff===staff.ParentInstrument.Staves.indexOf(staff)+1),svg=binding?.node.ownerSVGElement;if(!svg)continue;
                            const box=graphic.PositionAndShape,x=(box.AbsolutePosition.x+box.BorderLeft)*10*zoom,y=(box.AbsolutePosition.y+box.BorderTop)*10*zoom,w=(box.BorderRight-box.BorderLeft)*10*zoom,h=(box.BorderBottom-box.BorderTop)*10*zoom;
                            if(!(w>0&&h>0)){
                                const id=(graphic as unknown as {editablePedalSVGId?:string}).editablePedalSVGId;
                                const target=(id?svg.querySelector<SVGGraphicsElement>('#'+CSS.escape('vf-'+id))??svg.querySelector<SVGGraphicsElement>('#'+CSS.escape(id)):null);
                                if(target){const b=target.getBBox();if(b.width>0&&b.height>0){const hit=document.createElementNS(svgNS,'rect');hit.setAttribute('x',String(b.x-3));hit.setAttribute('y',String(b.y-3));hit.setAttribute('width',String(b.width+6));hit.setAttribute('height',String(b.height+6));hit.setAttribute('fill','transparent');hit.style.pointerEvents='all';target.append(hit);}target.setAttribute('tabindex','0');target.setAttribute('role','button');target.setAttribute('aria-label','Pedal mark in measure '+canonical?.number);target.setAttribute('data-mark-id',candidates[0].id);target.onclick=e=>{e.stopPropagation();live.current.onMark?.(candidates[0].id);};target.onpointerdown=e=>e.stopPropagation();target.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();live.current.onMark?.(candidates[0].id);}};}

                                continue;
                            }
                            const rect=window.document.createElementNS(svgNS,'rect');rect.setAttribute('x',String(x-3));rect.setAttribute('y',String(y-3));rect.setAttribute('width',String(w+6));rect.setAttribute('height',String(h+6));rect.setAttribute('fill','transparent');rect.setAttribute('stroke','transparent');rect.setAttribute('tabindex','0');rect.setAttribute('role','button');rect.setAttribute('aria-label','Pedal mark in measure '+canonical?.number);rect.setAttribute('data-mark-id',candidates[0].id);rect.onclick=e=>{e.stopPropagation();live.current.onMark?.(candidates[0].id);};rect.onpointerdown=e=>e.stopPropagation();rect.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();live.current.onMark?.(candidates[0].id);}};svg.append(rect);
                        }
                    }
                    for(const row of osmd.GraphicSheet.MeasureList)for(const measure of row){
                        if(!measure)continue;
                        const part=osmd.Sheet.Instruments.indexOf(measure.ParentStaff.ParentInstrument),mi=osmd.Sheet.SourceMeasures.indexOf(measure.parentSourceMeasure),canonical=review.score.parts[part]?.measures.find(m=>m.index===mi);
                        for(const entry of measure.staffEntries)for(const chord of entry.graphicalChordContainers??[]){
                            const measureHarmonies=review.score.harmonies?.filter(h=>h.measure_id===canonical?.id)??[];
                            const renderedTimes=measure.staffEntries.filter(e=>e.graphicalChordContainers?.length).map(e=>e.relInMeasureTimestamp.RealValue*4);
                            // Some OSMD versions ignore harmony offsets. In that case expose
                            // the exact measure's candidates instead of assigning a wrong ID.
                            const unresolvedOffset=measureHarmonies.some(h=>!renderedTimes.some(time=>Math.abs(rational(h.onset)-time)<1e-7));
                            const candidates=unresolvedOffset?measureHarmonies:measureHarmonies.filter(h=>Math.abs(rational(h.onset)-entry.relInMeasureTimestamp.RealValue*4)<1e-7);
                            const label=chord.GraphicalLabel.SVGNode as SVGGraphicsElement|null;if(!candidates.length||!label)continue;
                            const svg=label.ownerSVGElement,inverse=svg?.getScreenCTM()?.inverse();if(!svg||!inverse)continue;
                            const b=label.getBoundingClientRect(),a=new DOMPoint(b.left,b.top).matrixTransform(inverse),z=new DOMPoint(b.right,b.bottom).matrixTransform(inverse);if(!(z.x>a.x&&z.y>a.y))continue;
                            const hit=document.createElementNS(svgNS,'rect');hit.setAttribute('x',String(a.x-4));hit.setAttribute('y',String(a.y-4));hit.setAttribute('width',String(z.x-a.x+8));hit.setAttribute('height',String(z.y-a.y+8));hit.setAttribute('fill','transparent');hit.setAttribute('data-harmony-id',candidates[0].id);hit.setAttribute('role','button');hit.setAttribute('tabindex','0');hit.setAttribute('aria-label',candidates.length===1?'Chord '+candidates[0].root_step+' in measure '+canonical?.number:'Choose chord in measure '+canonical?.number);hit.onpointerdown=e=>e.stopPropagation();hit.onclick=e=>{e.stopPropagation();if(candidates.length===1)live.current.onHarmony?.(candidates[0].id,hit.getBoundingClientRect());else live.current.onHarmonyCandidates?.(candidates.map(h=>h.id),hit.getBoundingClientRect());};hit.onkeydown=e=>{if(e.key==='Enter'){e.preventDefault();if(candidates.length===1)live.current.onHarmony?.(candidates[0].id,hit.getBoundingClientRect());else live.current.onHarmonyCandidates?.(candidates.map(h=>h.id),hit.getBoundingClientRect());}};svg.append(hit);
                        }
                    }
                    const visitedDynamics=new Set<object>();
                    for(const row of osmd.GraphicSheet.MeasureList)for(const measure of row){
                        const line=measure?.ParentStaffLine;if(!line)continue;
                        for(const graphic of line.AbstractExpressions??[]){
                            if(visitedDynamics.has(graphic))continue;visitedDynamics.add(graphic);
                            const source=graphic.SourceExpression as unknown as {InMeasureTimestamp?:{RealValue:number};StaffNumber?:number};
                            if(!source.InMeasureTimestamp)continue;
                            const part=osmd.Sheet.Instruments.indexOf(line.ParentStaff.ParentInstrument),mi=osmd.Sheet.SourceMeasures.indexOf(graphic.parentMeasure),canonical=review.score.parts[part]?.measures.find(m=>m.index===mi);
                            const marks=review.score.omr_marks?.filter(m=>m.kind==='dynamics'&&m.measure_id===canonical?.id&&m.staff===source.StaffNumber&&Math.abs(rational(m.onset)-source.InMeasureTimestamp!.RealValue*4)<1e-7)??[];
                            if(marks.length!==1)continue;
                            const binding=[...byId.values()].find(v=>v.event.measure_id===canonical?.id),svg=binding?.node.ownerSVGElement;if(!svg)continue;
                            const label=graphic.Label?.SVGNode as SVGGraphicsElement|undefined;
                            const inverse=svg.getScreenCTM()?.inverse();
                            if(!label||!inverse)continue;
                            const bounds=label.getBoundingClientRect(),from=new DOMPoint(bounds.left,bounds.top).matrixTransform(inverse),to=new DOMPoint(bounds.right,bounds.bottom).matrixTransform(inverse);
                            const x=from.x,y=from.y,w=to.x-from.x,h=to.y-from.y;
                            if(!(w>0&&h>0))continue;
                            const hit=document.createElementNS(svgNS,'rect');hit.setAttribute('x',String(x-4));hit.setAttribute('y',String(y-4));hit.setAttribute('width',String(w+8));hit.setAttribute('height',String(h+8));hit.setAttribute('fill','transparent');hit.setAttribute('data-mark-id',marks[0].id);hit.setAttribute('role','button');hit.setAttribute('tabindex','0');hit.setAttribute('aria-label','Dynamics '+marks[0].type+' in measure '+canonical?.number);hit.onpointerdown=e=>e.stopPropagation();hit.onclick=e=>{e.stopPropagation();live.current.onMark?.(marks[0].id);};hit.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();live.current.onMark?.(marks[0].id);}};svg.append(hit);
                        }
                    }
                    for (const text of review.score.texts ?? []) {
                        const normalize=(value:string)=>value.normalize('NFC').replace(/\s+/gu,' ').trim();
                        const matches=(review.score.texts??[]).filter(t=>normalize(t.text)===normalize(text.text));
                        if(new Set(matches.map(t=>t.id)).size!==1){
                            // One composer may appear in both metadata and the printed credit.
                            // Bind that explicit pair once, without guessing among unrelated text.
                            const composer=matches.length===2&&matches.some(t=>t.role==='composer')&&matches.some(t=>t.role==='printed_composer')&&text.role==='printed_composer';
                            const title=matches.length>=2&&matches.length<=3&&new Set(matches.map(t=>t.role)).size===matches.length&&matches.every(t=>['movement_title','work_title','printed_title','credit'].includes(t.role))&&matches.some(t=>['movement_title','work_title'].includes(t.role))&&matches.filter(t=>['printed_title','credit'].includes(t.role)).length===1&&['printed_title','credit'].includes(text.role);
                            if(!composer&&!title)continue;
                        }
                        const nodes=[...element.querySelectorAll<SVGTextElement>('svg text')].filter(n=>{
                            const whole=normalize(n.textContent??''),part=normalize(text.text);
                            if(whole===part)return true;
                            // OSMD can merge adjacent direction words into one SVG text node.
                            // Bind only a unique literal fragment; never guess from OCR similarity.
                            return text.role==='direction'&&part.length>0&&whole.indexOf(part)>=0&&whole.indexOf(part)===whole.lastIndexOf(part);
                        });
                        const distinct=new Map<string,SVGTextElement>();
                        for(const node of nodes){const box=node.getBoundingClientRect();distinct.set([box.x,box.y,box.width,box.height].map(n=>Math.round(n*10)).join(':'),node);}
                        for(const [copy,node] of [...distinct.values()].entries()){
                            const svg=node.ownerSVGElement,inverse=svg?.getScreenCTM()?.inverse();if(!svg||!inverse)continue;
                            let bounds=node.getBoundingClientRect();
                            const raw=node.textContent??'',fragment=text.text,start=raw.indexOf(fragment);
                            if(normalize(raw)!==normalize(fragment)){
                                // Substring geometry must refer to the exact raw characters.
                                if(start<0||start!==raw.lastIndexOf(fragment))continue;
                                const first=node.getStartPositionOfChar(start),last=node.getEndPositionOfChar(start+fragment.length-1),ctm=node.getScreenCTM();if(!ctm)continue;
                                const a=new DOMPoint(first.x,first.y).matrixTransform(ctm),z=new DOMPoint(last.x,last.y).matrixTransform(ctm);
                                bounds=new DOMRect(Math.min(a.x,z.x),bounds.top,Math.abs(z.x-a.x),bounds.height);
                            }
                            const from=new DOMPoint(bounds.left,bounds.top).matrixTransform(inverse),to=new DOMPoint(bounds.right,bounds.bottom).matrixTransform(inverse);
                            if(!(to.x>from.x&&to.y>from.y))continue;
                            const hit=window.document.createElementNS(svgNS,'g'),rect=window.document.createElementNS(svgNS,'rect');
                            rect.setAttribute('x',String(from.x-2));rect.setAttribute('y',String(from.y-2));rect.setAttribute('width',String(to.x-from.x+4));rect.setAttribute('height',String(to.y-from.y+4));rect.setAttribute('fill','transparent');rect.setAttribute('stroke','transparent');hit.append(rect);
                            hit.style.cursor='text';hit.setAttribute('data-testid','real-text-'+text.id+(copy?'-copy-'+copy:''));hit.setAttribute('data-text-id',text.id);hit.setAttribute('tabindex','0');hit.setAttribute('role','button');hit.setAttribute('aria-label','Score text '+text.text);
                            hit.onpointerdown=e=>e.stopPropagation();hit.onclick=e=>{e.stopPropagation();live.current.onText?.(text.id,bounds);};hit.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();live.current.onText?.(text.id,bounds);}};
                            svg.append(hit);
                        }
                    }
                }
                if(fitVersion!==fitted.current){fitted.current=fitVersion;scrollPosition.current={top:0,left:0};const viewport=element.parentElement;if(viewport){viewport.scrollLeft=0;viewport.scrollTop=0;}}else{const viewport=element.parentElement;if(viewport){viewport.scrollLeft=scrollPosition.current.left;viewport.scrollTop=scrollPosition.current.top;}}
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
        return () => { disposed = true; const viewport=element.parentElement;if(viewport)scrollPosition.current={top:viewport.scrollTop,left:viewport.scrollLeft};element.replaceChildren(); };
    }, [review, readOnly, zoom, width,fitVersion,printCompact]);
    useEffect(() => { host.current?.querySelectorAll('[data-event-id]').forEach(n => { const active = n.getAttribute('data-event-id') === selected || selection.includes(n.getAttribute('data-event-id')??''); n.classList.toggle('real-selected', active); n.setAttribute('aria-pressed', String(active)); }); }, [selected, selection, review, zoom]);
    useEffect(()=>{host.current?.querySelectorAll('[data-text-id]').forEach(n=>{n.classList.toggle('real-object-selected',n.getAttribute('data-text-id')===selectedText);});},[selectedText,review,zoom]);
    useEffect(()=>{host.current?.querySelectorAll('[data-mark-id]').forEach(n=>{n.setAttribute('stroke',n.getAttribute('data-mark-id')===selectedMark?'#1769b5':'transparent');});},[selectedMark,review,zoom]);
    return <><div ref={host} className="real-score"/>{error && <p role="alert">{error}</p>}</>;
}

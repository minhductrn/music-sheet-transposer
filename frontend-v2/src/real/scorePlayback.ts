import type { Review } from './api';

type Note = { start: number; end: number; pitch: number };
type NoteSegment = Note & { id: string; chain: Note };

function children(element: Element, name: string) {
    return Array.from(element.children).filter(child => child.localName === name);
}

export function playbackNotes(xml: string, parts?: Review['score']['parts']) {
    const score = new DOMParser().parseFromString(xml, 'application/xml');
    const tempos = new Map([[0, 120]]);
    const notes: Note[] = [];
    const measureTimes: number[] = [];
    const highlights: NoteSegment[] = [];
    const stepOffsets: Record<string, number> = { C: 0, D: 2, E: 4, F: 5, G: 7, A: 9, B: 11 };
    for (const [partIndex, part] of children(score.documentElement, 'part').entries()) {
        let beat = 0, divisions = 1;
        const transpositions = new Map<number, number>();
        const ties = new Map<string, Note>();
        for (const [measureIndex, measure] of children(part, 'measure').entries()) {
            if (partIndex === 0) measureTimes.push(beat);
            const projected = parts?.[partIndex]?.measures[measureIndex];
            const voices = new Map(projected?.voices.map(voice => [voice.id, voice.events]));
            const offsets = new Map<string, number>();
            let cursor = beat, end = beat, previousOnset = beat;
            for (const item of measure.children) {
                const field = (...path: string[]) => {
                    let element: Element | undefined = item;
                    for (const name of path) element = element && children(element, name)[0];
                    return element?.textContent ?? '';
                };
                if (item.localName === 'attributes') {
                    divisions = Number(field('divisions')) || divisions;
                    for (const transpose of children(item, 'transpose')) {
                        const value = (tag: string) => Number(children(transpose, tag)[0]?.textContent ?? 0);
                        transpositions.set(Number(transpose.getAttribute('number')),
                            value('chromatic') + 12 * value('octave-change'));
                    }
                }
                const duration = Number(field('duration')) / divisions;
                if (item.localName === 'backup' || item.localName === 'forward') {
                    cursor += item.localName === 'backup' ? -duration : duration;
                    end = Math.max(cursor, end);
                }
                const bpm = Number(children(item, 'sound')[0]?.getAttribute('tempo')
                    ?? item.getAttribute('tempo'));
                if (Number.isFinite(bpm) && bpm > 0) tempos.set(Math.max(0, cursor + Number(field('offset')) / divisions), bpm);
                if (item.localName !== 'note') continue;
                const voice = field('voice') || '1';
                const offset = offsets.get(voice) ?? 0;
                offsets.set(voice, offset + 1);
                const event = voices.get(voice)?.[offset];
                if (children(item, 'grace')[0]) continue;
                const chord = children(item, 'chord')[0];
                const start = chord ? previousOnset : cursor;
                if (!chord) {
                    previousOnset = start;
                    cursor += duration;
                }
                end = Math.max(end, cursor, start + duration);
                const staff = Number(field('staff')) || 1;
                const pitch = (Number(field('pitch', 'octave')) + 1) * 12
                    + stepOffsets[field('pitch', 'step')] + Number(field('pitch', 'alter'))
                    + (transpositions.get(staff) ?? transpositions.get(0) ?? 0);
                if (!Number.isFinite(pitch) || duration <= 0) continue;
                const key = [staff, voice, pitch].join(':');
                const tieTypes = [...children(item, 'tie'),
                    ...children(item, 'notations').flatMap(node => children(node, 'tied'))]
                    .map(tie => tie.getAttribute('type'));
                const stop = tieTypes.includes('stop');
                const existing = stop ? ties.get(key) : undefined;
                const note = existing ?? { start, end: start + duration, pitch };
                if (!existing) notes.push(note);
                if (event?.pitch) highlights.push({ id: event.id, start, end: start + duration, pitch, chain: note });
                note.end = start + duration;
                if (tieTypes.includes('start')) ties.set(key, note);
                else ties.delete(key);
            }
            beat = end;
        }
    }
    let seconds = 0, previousBeat = 0, bpm = 120;
    const timeline = [...tempos].sort(([a], [b]) => a - b).map(([beat, nextBpm]) => {
        seconds += (beat - previousBeat) * 60 / bpm;
        previousBeat = beat;
        bpm = nextBpm;
        return { beat, seconds, bpm };
    });
    const reversedTimeline = [...timeline].reverse();
    const toSeconds = (beat: number) => {
        const tempo = reversedTimeline.find(entry => entry.beat <= beat) ?? timeline[0];
        return tempo.seconds + (beat - tempo.beat) * 60 / tempo.bpm;
    };
    const inSeconds = <T extends { start: number; end: number }>(note: T) =>
        ({ ...note, start: toSeconds(note.start), end: toSeconds(note.end) });
    return {
        initialTempo: timeline[0].bpm,
        measureTimes: measureTimes.map(toSeconds),
        notes: notes.map(inSeconds).sort((a, b) => a.start - b.start),
        highlights: highlights.map(inSeconds).sort((a, b) => a.start - b.start),
    };
}

export function selectedPlaybackNotes(segments: NoteSegment[]): Note[] {
    const notes: Note[] = [];
    const latest = new Map<Note, Note>();
    for (const { chain, pitch, start, end } of segments) {
        const previous = latest.get(chain);
        if (previous && Math.abs(previous.end - start) < 1e-7) {
            previous.end = end;
        } else {
            const note = { pitch, start, end };
            latest.set(chain, note);
            notes.push(note);
        }
    }
    return notes;
}

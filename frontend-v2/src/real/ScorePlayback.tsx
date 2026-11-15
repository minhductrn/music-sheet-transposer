import { useEffect, useMemo, useRef, useState, type RefObject } from 'react';
import type { Review } from './api';
import { playbackNotes, selectedPlaybackNotes } from './scorePlayback';

export function ScorePlayback({ xml, active, label = 'Working Score', parts, viewport, sound, onSoundChange, selectedMeasure, selection, tempoOffset, setTempoOffset }: {
    xml: string;
    sound: string;
    onSoundChange: (sound: string) => void;
    active: boolean;
    label?: string;
    selectedMeasure?: number;
    selection?: readonly string[];
    tempoOffset: number;
    setTempoOffset: (offset: number) => void;
    parts?: Review['score']['parts'];
    viewport?: RefObject<HTMLDivElement | null>;
}) {
    const stopRef = useRef<(() => void) | null>(null);
    const [playing, setPlaying] = useState(false);
    const [status, setStatus] = useState('');

    const [follow, setFollow] = useState(true);
    const [loop, setLoop] = useState(false);
    const [from, setFrom] = useState(0);
    const [through, setThrough] = useState<number | null>(null);
    const { notes, initialTempo, highlights, measureTimes } = useMemo(() => playbackNotes(xml, parts), [xml, parts]);
    const tempo = Math.max(20, Math.round(initialTempo + tempoOffset));

    useEffect(() => () => stopRef.current?.(), [xml, active, parts, sound]);

    const speed = useRef(initialTempo / tempo);
    const following = useRef(follow);
    useEffect(() => { speed.current = initialTempo / tempo; }, [initialTempo, tempo]);
    useEffect(() => { following.current = follow; }, [follow]);
    const last = Math.max(0, measureTimes.length - 1);
    const loopFrom = Math.min(from, last);
    const loopTo = Math.max(loopFrom, Math.min(through ?? last, last));

    const hasSelection = Boolean(selection?.length);

    async function play(fromBeginning = false) {
        if (stopRef.current || !active) return;
        const playSelection = hasSelection && !fromBeginning;
        const selectedIds = new Set(selection);
        const currentHighlights = playSelection ? highlights.filter(note => selectedIds.has(note.id)) : highlights;
        const currentNotes = playSelection ? selectedPlaybackNotes(currentHighlights) : notes;
        const repeat = loop && !fromBeginning;
        if (!currentNotes.length) {
            setStatus('No playable notes.');
            return;
        }
        let context: AudioContext;
        try {
            context = new AudioContext();
        } catch {
            setStatus('Audio playback is unavailable.');
            return;
        }
        let timer: number | undefined;
        let frame = 0;
        let highlighted: Element[] = [];
        const clearHighlights = () => {
            highlighted.forEach(head => head.classList.remove('real-playing'));
            highlighted = [];
        };
        const stop = () => {
            window.cancelAnimationFrame(frame);
            clearHighlights();
            window.clearInterval(timer);
            stopRef.current = null;
            void context.close();
            setPlaying(false);
        };
        stopRef.current = stop;
        setPlaying(true);
        setStatus('');
        try {
            await context.resume();
            if (stopRef.current !== stop) return;
            const pianoWave = context.createPeriodicWave(
                new Float32Array(6), Float32Array.of(0, 1, 0.55, 0.22, 0.12, 0.06));
            const scoreEnd = currentNotes.reduce((end, note) => Math.max(end, note.end), 0);
            const startAt = playSelection ? currentNotes[0].start
                : (measureTimes[repeat ? loopFrom : fromBeginning ? 0 : selectedMeasure ?? 0] ?? 0);
            const finish = repeat && !playSelection ? (measureTimes[loopTo + 1] ?? scoreEnd) : scoreEnd;
            if (finish <= startAt) {
                stop();
                setStatus('No playable notes in this range.');
                return;
            }
            const tones = new Set<OscillatorNode>();
            let timeScale = speed.current;
            let origin = context.currentTime + 0.05;
            let position = startAt;
            const scoreTime = (now: number) => position + Math.max(0, now - origin) / timeScale;
            if (viewport) {
                let next = 0;
                let previousTime = -1;
                let sounding: typeof highlights = [];
                const updateHighlights = () => {
                    const time = scoreTime(context.currentTime);
                    if (time < previousTime) {
                        next = 0;
                        sounding = [];
                    }
                    previousTime = time;
                    while (next < currentHighlights.length && currentHighlights[next].start <= time) {
                        sounding.push(currentHighlights[next++]);
                    }
                    sounding = sounding.filter(note => note.end > time);
                    const heads = sounding.flatMap(note => Array.from(
                        viewport.current?.querySelectorAll(`[data-event-id="${CSS.escape(note.id)}"]`) ?? []));
                    for (const head of highlighted) {
                        if (!heads.includes(head)) head.classList.remove('real-playing');
                    }
                    for (const head of heads) head.classList.add('real-playing');
                    const pane = viewport.current;
                    const head = heads[heads.length - 1];
                    if (following.current && pane && head && !highlighted.includes(head)) {
                        const view = pane.getBoundingClientRect();
                        const note = head.getBoundingClientRect();
                        if (note.top < view.top || note.bottom > view.bottom) {
                            pane.scrollTop += note.top - view.top - pane.clientHeight / 3;
                        }
                        if (note.left < view.left || note.right > view.right) {
                            pane.scrollLeft += note.left - view.left - pane.clientWidth / 3;
                        }
                    }
                    highlighted = heads;
                    frame = window.requestAnimationFrame(updateHighlights);
                };
                frame = window.requestAnimationFrame(updateHighlights);
            }
            let index = 0;
            const schedule = () => {
                const now = context.currentTime;
                const time = scoreTime(now);
                if (time >= finish && !repeat) {
                    stop();
                    return;
                }
                if (time >= finish || timeScale !== speed.current) {
                    for (const tone of tones) tone.stop();
                    tones.clear();
                    position = time >= finish ? startAt : time;
                    origin = now;
                    timeScale = speed.current;
                    index = 0;
                }
                while (index < currentNotes.length) {
                    const note = currentNotes[index];
                    const onset = origin + (note.start - position) * timeScale;
                    if (note.start >= finish || onset >= now + 0.12) break;
                    index++;
                    const start = Math.max(now, onset);
                    const end = origin + (Math.min(note.end, finish) - position) * timeScale;
                    if (end <= start) continue;
                    const tone = context.createOscillator();
                    const envelope = context.createGain();
                    const ramp = Math.min(0.02, (end - start) / 3);
                    tone.type = 'triangle';
                    if (sound === 'piano') {
                        tone.setPeriodicWave(pianoWave);
                    }
                    tone.frequency.value = 440 * 2 ** ((note.pitch - 69) / 12);
                    envelope.gain.setValueAtTime(0, start);
                    envelope.gain.linearRampToValueAtTime(0.07, start + ramp);
                    if (sound === 'piano') {
                        envelope.gain.exponentialRampToValueAtTime(0.008, end - ramp);
                    } else {
                        envelope.gain.setValueAtTime(0.07, end - ramp);
                    }
                    envelope.gain.linearRampToValueAtTime(0, end);
                    tone.connect(envelope).connect(context.destination);
                    tones.add(tone);
                    tone.start(start);
                    tone.stop(end);
                    tone.onended = () => { tones.delete(tone); tone.disconnect(); envelope.disconnect(); };
                }
            };
            timer = window.setInterval(schedule, 40);
            schedule();
        } catch {
            if (stopRef.current === stop) {
                stop();
                setStatus('Audio playback could not start.');
            }
        }
    }

    return <div className="score-playback">
        <button type="button" disabled={!active} aria-label={`${playing ? 'Stop' : 'Play'} ${label}`}
            onClick={() => playing ? stopRef.current?.() : void play()}>{playing ? 'Stop' : hasSelection ? 'Play selection' : 'Play'}</button>
        <label>Sound <select value={sound} disabled={!active || playing} onChange={event => onSoundChange(event.target.value)}>
            <option value="piano">Piano</option><option value="tone">Simple tone</option>
        </select></label>
        <div role="group" aria-label="Playback tempo">
            <button type="button" aria-label="Decrease tempo" disabled={!active || tempo <= 20}
                onClick={() => setTempoOffset(Math.max(20, tempo - 5) - initialTempo)}>−</button>
            <output>{tempo} BPM</output>
            <button type="button" aria-label="Increase tempo" disabled={!active}
                onClick={() => setTempoOffset(tempo + 5 - initialTempo)}>+</button>
        </div>
        {viewport && <>
            <button type="button" disabled={playing || !active} onClick={() => void play(true)}>Play from beginning</button>
            <label><input type="checkbox" checked={follow} onChange={event => setFollow(event.target.checked)} /> Follow</label>
            <label><input type="checkbox" checked={loop} disabled={playing || !measureTimes.length}
                onChange={event => setLoop(event.target.checked)} /> Loop</label>
            {loop && !hasSelection && <div role="group" aria-label="Loop measures">
                <label>From <select disabled={playing} value={loopFrom} onChange={event => setFrom(Number(event.target.value))}>
                    {measureTimes.map((_, index) => <option key={index} value={index}>{parts?.[0]?.measures[index]?.number ?? index + 1}</option>)}
                </select></label>
                <label>To <select disabled={playing} value={loopTo} onChange={event => setThrough(Number(event.target.value))}>
                    {measureTimes.map((_, index) => <option key={index} value={index} disabled={index < loopFrom}>{parts?.[0]?.measures[index]?.number ?? index + 1}</option>)}
                </select></label>
            </div>}
        </>}
        {status && <span role="status">{status}</span>}
    </div>;
}

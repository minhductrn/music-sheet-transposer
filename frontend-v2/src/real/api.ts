// MusicXML stays authoritative; score objects are read-only server projections.
export type Pitch = {
    step: string;
    alter: string;
    octave: number;
};
export type Event = {
    accidental?: { text?: string };
    key_signature?: {fifths:string;mode?:string|null}[];
    id: string;
    kind: string;
    pitch: Pitch | null;
    onset: string | null;
    duration: string | null;
    voice: string;
    staff: number;
    measure_id: string;
    chord_id: string | null;
    grace: boolean;
    display_size: string;
    notated_duration?: {
        type: string | null;
        dots: number;
    };
    lyric_ids: string[];
    tie_target_id?: string | null;
    tie_direction?: 'up' | 'down' | null;
    palette_duration_options: Record<string, string>;
    clef?: {
        sign?: string;
        line?: string;
        octave_change?: string;
        fields?: {
            name: string;
            text: string;
        }[];
    };
};
export type Measure = {
    id: string;
    number: string;
    index: number;
    expected_duration: string | null;
    voices: {
        id: string;
        events: Event[];
    }[];
    insertion_gaps: {
        onset: string;
        duration: string;
        voice: string;
        staff: number;
    }[];
    key_signature: {
        fifths: string;
        mode: string | null;
    }[];
    time_signature: {
        pairs: {
            beats: string;
            beat_type: string;
        }[];
    }[];
};
export type Lyric = {
    id: string;
    event_id: string;
    number: string;
    text: string;
    segments: string[];
};
export type Slur = {
    source_event_id: string;
    target_event_id: string;
    direction: 'up' | 'down';
    number: string;
};
export type Review = {
    id: string;
    revision: number;
    musicxml_base64: string;
    xml: string;
    bytes: Uint8Array;
    score: {
        metadata: {
            title: string;
        };
        parts: {
            id: string;
            name: string;
            measures: Measure[];
        }[];
        lyrics: Lyric[];
        texts: {
            id: string;
            role: string;
            text: string;
            event_id?: string;
        }[];
    };
    slurs: Slur[];
    validation: {
        can_verify: boolean;
        diagnostics: {
            message: string;
            blocking: boolean;
        }[];
    };
};
export type Key = {
    fifths: number;
    mode: 'major' | 'minor';
};
export const rational = (s: string | null) => { if (s === null)
    return NaN; const [a, b = '1'] = s.split('/'); return Number(a) / Number(b); };
export const events = (r: Review) => r.score.parts.flatMap(p => p.measures.flatMap(m => m.voices.flatMap(v => v.events)));
export function decode(base64: string) { const bytes = Uint8Array.from(atob(base64), c => c.charCodeAt(0)); const prefix = new TextDecoder('latin1').decode(bytes.slice(0, 250)); const encoding = bytes[0] === 255 && bytes[1] === 254 || bytes[0] === 60 && bytes[1] === 0 ? 'utf-16le' : bytes[0] === 254 && bytes[1] === 255 || bytes[0] === 0 && bytes[1] === 60 ? 'utf-16be' : /encoding\s*=\s*["']([^"']+)["']/i.exec(prefix)?.[1] ?? 'utf-8'; if (!/^utf-?8$|^utf-?16(?:le|be)?$/i.test(encoding))
    throw Error('This XML encoding is not supported by the pilot. Open a UTF-8 or UTF-16 MusicXML copy; the original is unchanged.'); const text = new TextDecoder(encoding, { fatal: true }).decode(bytes); return text.replace(/(<\?xml[^>]*encoding\s*=\s*)["'][^"']+["']/i, '$1"utf-8"'); }
async function checked(response: Response) { if (!response.ok) {
    const data = await response.json().catch(() => null);
    throw Error(typeof data?.detail === 'string' ? data.detail : `Request failed (${response.status}). No score change applied.`);
} return response; }
async function projection(response: Response): Promise<Review> { const p = await (await checked(response)).json(); try {
    return { ...p, bytes: Uint8Array.from(atob(p.musicxml_base64), c => c.charCodeAt(0)), xml: decode(p.musicxml_base64) };
}
catch (error) {
    await closeReview(p.id).catch(() => { });
    throw error;
} }
export const xmlBlob = (xml: string) => new Blob([xml], { type: 'application/vnd.recordare.musicxml+xml' });
export async function openXML(file: Blob) { const form = new FormData(); form.append('musicxml', file, 'concert.musicxml'); return projection(await fetch('/api/v1/reviews', { method: 'POST', body: form })); }
export async function closeReview(id: string) { await fetch(`/api/v1/reviews/${encodeURIComponent(id)}`, { method: 'DELETE', keepalive: true }); }
export async function edit(r: Review, path: string, body?: unknown, method = 'POST') { return projection(await fetch(`/api/v1/reviews/${encodeURIComponent(r.id)}/${path}`, { method, headers: { 'Content-Type': 'application/json', 'If-Match': String(r.revision) }, body: body === undefined ? undefined : JSON.stringify(body) })); }
async function fileOperation(path: string, xml: string, fields: Record<string, string>) { const form = new FormData(); form.append('file', xmlBlob(xml), 'concert.musicxml'); for (const [k, v] of Object.entries(fields))
    form.append(k, v); return checked(await fetch('/api/v1/' + path, { method: 'POST', body: form })); }
export async function keyInfo(xml: string): Promise<{
    fifths: number;
    mode: 'major' | 'minor' | null;
    candidates: Key[];
}> { return (await fileOperation('concert-key', xml, {})).json(); }
export async function concertXML(xml: string, source: Key, target: number, direction: 'up' | 'down') { return (await fileOperation('transpose/concert-key', xml, { source_fifths: String(source.fifths), source_mode: source.mode, source_confirmed: 'true', target_fifths: String(target), direction })).text(); }
export async function saxXML(xml: string, instrument: string, direction: "up"|"down" = "up") { return (await fileOperation('transpose/instrument', xml, { instrument, direction })).text(); }
export async function previewTriplet(r: Review, event_ids: string[]): Promise<{
    valid: boolean;
    reason?: string;
    message?: string;
    command?: unknown;
}> { return (await checked(await fetch(`/api/v1/reviews/${encodeURIComponent(r.id)}/triplets/preview`, { method: 'POST', headers: { 'Content-Type': 'application/json', 'If-Match': String(r.revision) }, body: JSON.stringify({ event_ids }) }))).json(); }
export function dottedWritten(base: string, dot: boolean) { const [n, d = 1] = base.split('/').map(Number); let a = n * (dot ? 3 : 1), b = d * (dot ? 2 : 1); const gcd = (x: number, y: number): number => y ? gcd(y, x % y) : x; const g = gcd(a, b); a /= g; b /= g; return b === 1 ? String(a) : `${a}/${b}`; }
